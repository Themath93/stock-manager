"""Trading engine facade that orchestrates all trading components.

This module provides the main TradingEngine class that coordinates:
- Order execution and position management
- Risk management and rate limiting
- Price monitoring and position reconciliation
- State persistence and recovery
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Optional
import logging
import threading
import time
from uuid import uuid4

from stock_manager.trading import (
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    TradingConfig,
    OrderExecutor,
    OrderResult,
    PositionManager,
    RiskManager,
    RiskLimits,
    RateLimiter,
)
from stock_manager.types import BrokerTruthSnapshot
from stock_manager.trading.guardrails import (
    EngineOperabilityDecision,
    OperationalState,
    RuntimeFaultDecision,
    build_execution_dedupe_key,
    evaluate_execution_integrity,
    evaluate_engine_operability,
    evaluate_order_permission,
    evaluate_pending_order_recovery,
    evaluate_realtime_startup,
    evaluate_runtime_fault,
    evaluate_session_handoff,
    evaluate_submission_recovery,
    evaluate_runtime_guard,
    evaluate_startup_guard,
    evaluate_websocket_guard,
    infer_buy_fill_from_balance,
    resolve_auto_exit_order,
    resolve_operational_state,
)
from stock_manager.monitoring import PriceMonitor, PositionReconciler
from stock_manager.persistence import TradingState, save_state_atomic, load_state
from stock_manager.persistence.recovery import (
    startup_reconciliation,
    RecoveryReport,
    RecoveryResult,
)
from stock_manager.notifications import (
    NotifierProtocol,
    NoOpNotifier,
    NotificationEvent,
    NotificationLevel,
)
from stock_manager.trading.logging import PipelineJsonLogger

logger = logging.getLogger(__name__)

_ACTIVE_PENDING_ORDER_STATUSES = {
    OrderStatus.CREATED,
    OrderStatus.SUBMITTED,
    OrderStatus.PENDING_BROKER,
    OrderStatus.PARTIAL_FILL,
}
_UNRESOLVED_ORDER_WARNING_AGE_SEC = 30.0


StrategyDiscoverySource = Literal["manual", "mock_fallback", "volume_rank", "fallback", "none"]


@dataclass(frozen=True)
class StrategyDiscoveryResult:
    """Resolved symbol candidates and their source metadata."""

    symbols: tuple[str, ...]
    source: StrategyDiscoverySource
    reason: str | None = None


@dataclass
class EngineStatus:
    """Trading engine status snapshot."""

    running: bool
    position_count: int
    price_monitor_running: bool
    reconciler_running: bool
    rate_limiter_available: int
    state_path: str
    is_paper_trading: bool
    operational_state: str
    buying_enabled: bool
    buy_blocked_reason: str | None
    trading_enabled: bool
    recovery_result: str
    degraded_reason: str | None
    operator_action_required: bool
    last_broker_snapshot_at: str | None
    open_order_count: int
    snapshot_stale: bool
    handoff_reason: str | None
    strategy_discovery_source: str | None
    strategy_discovery_symbols: tuple[str, ...]
    strategy_discovery_reason: str | None
    strategy_discovery_updated_at: str | None


@dataclass
class TradingEngine:
    """Main trading engine that orchestrates all trading components.

    The TradingEngine provides a unified interface for:
    - Placing and managing orders
    - Monitoring positions and prices
    - Enforcing risk limits
    - Persisting state and recovering from failures

    Example:
        >>> from stock_manager.engine import TradingEngine
        >>> from stock_manager.trading import TradingConfig, RiskLimits
        >>>
        >>> config = TradingConfig(
        ...     risk_limits=RiskLimits(max_position_size=100, max_total_exposure=1000000)
        ... )
        >>>
        >>> with TradingEngine(client, config, "12345678") as engine:
        ...     result = engine.buy("005930", 10, 70000, stop_loss=65000)
        ...     if result.success:
        ...         print(f"Order placed: {result.order_id}")
    """

    client: Any  # KISRestClient
    config: TradingConfig
    account_number: str
    account_product_code: str = "01"
    state_path: Path = field(default_factory=lambda: Path.home() / ".stock_manager" / "state.json")
    is_paper_trading: bool = False
    notifier: NotifierProtocol = field(default_factory=NoOpNotifier)
    broker_adapter: Any | None = None

    # Internal components (initialized in __post_init__)
    _executor: OrderExecutor = field(init=False)
    _position_manager: PositionManager = field(init=False)
    _risk_manager: RiskManager = field(init=False)
    _rate_limiter: RateLimiter = field(init=False)
    _price_monitor: PriceMonitor = field(init=False)
    _reconciler: PositionReconciler = field(init=False)
    _state: TradingState = field(init=False)
    _running: bool = field(default=False, init=False)
    _buying_enabled: bool = field(default=False, init=False)
    _buy_blocked_reason: str | None = field(default=None, init=False)
    _trading_enabled: bool = field(default=False, init=False)
    _degraded_reason: str | None = field(default=None, init=False)
    _operational_state: OperationalState = field(default="blocked", init=False)
    _last_market_data_success_at: datetime | None = field(default=None, init=False, repr=False)
    _last_reconciliation_success_at: datetime | None = field(default=None, init=False, repr=False)
    _last_balance_refresh_success_at: datetime | None = field(default=None, init=False, repr=False)
    _last_broker_snapshot_at: datetime | None = field(default=None, init=False, repr=False)
    _last_recovery_result: RecoveryResult = field(default=RecoveryResult.CLEAN, init=False)
    _daily_kill_switch_active: bool = field(default=False, init=False)
    _daily_kill_switch_triggered_at: datetime | None = field(default=None, init=False)
    _daily_pnl_date: str | None = field(default=None, init=False)
    _daily_baseline_equity: Decimal | None = field(default=None, init=False)
    _daily_realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"), init=False)
    _daily_unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"), init=False)
    _strategy_thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _strategy_stop_event: threading.Event = field(
        default_factory=threading.Event, init=False, repr=False
    )
    _strategy_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _auto_exit_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _state_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _auto_exit_last_trigger: dict[tuple[str, str], float] = field(
        default_factory=dict, init=False, repr=False
    )
    _broker_adapter: Any | None = field(default=None, init=False, repr=False)
    _processed_execution_keys: list[str] = field(default_factory=list, init=False, repr=False)
    _processed_execution_key_set: set[str] = field(default_factory=set, init=False, repr=False)
    _strategy_discovery_source: StrategyDiscoverySource | None = field(default=None, init=False)
    _strategy_discovery_symbols: tuple[str, ...] = field(default_factory=tuple, init=False)
    _strategy_discovery_reason: str | None = field(default=None, init=False)
    _strategy_discovery_updated_at: str | None = field(default=None, init=False)
    _strategy_discovery_last_fingerprint: str | None = field(default=None, init=False, repr=False)
    _runtime_logger: PipelineJsonLogger = field(init=False, repr=False)
    _guardrail_notifications_sent: set[str] = field(default_factory=set, init=False, repr=False)
    _operator_action_required: bool = field(default=False, init=False)
    _open_order_count: int = field(default=0, init=False)
    _snapshot_stale: bool = field(default=False, init=False)
    _handoff_reason: str | None = field(default=None, init=False)
    _last_broker_snapshot: BrokerTruthSnapshot | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Initialize all trading components with proper dependencies."""
        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            max_requests=self.config.rate_limit_per_sec, window_seconds=1.0
        )

        # Initialize position manager
        self._position_manager = PositionManager()

        self._risk_manager = RiskManager(
            limits=RiskLimits(
                max_position_size_pct=self.config.max_position_size_pct,
                max_positions=self.config.max_positions,
                default_stop_loss_pct=self.config.default_stop_loss_pct,
                default_take_profit_pct=self.config.default_take_profit_pct,
            ),
            portfolio_value=self.config.portfolio_value,
        )

        self._position_manager.set_callbacks(
            on_stop_loss=self._handle_stop_loss,
            on_take_profit=self._handle_take_profit,
        )

        # Initialize order executor
        self._executor = OrderExecutor(
            client=self.client,
            account_number=self.account_number,
            account_product_code=self.account_product_code,
            is_paper_trading=self.is_paper_trading,
        )

        # Initialize price monitor
        self._price_monitor = PriceMonitor(
            client=self.client,
            interval=self.config.polling_interval_sec,
            rate_limiter=self._rate_limiter,
        )

        # Initialize position reconciler
        self._reconciler = PositionReconciler(
            position_manager=self._position_manager,
            inquire_balance_func=self._inquire_balance,
            interval=60.0,  # Check every minute
            on_discrepancy=None,
            on_cycle_complete=self._on_reconciliation_cycle,
            apply_state=False,
        )

        self._broker_adapter = self._resolve_broker_adapter()
        self._register_websocket_lifecycle_callback()
        self._runtime_logger = PipelineJsonLogger(
            log_dir=self.state_path.parent / "runtime",
            prefix="engine-runtime",
        )

        # Initialize empty state
        self._state = TradingState(positions={}, last_updated=datetime.now(timezone.utc))

        logger.info(
            "TradingEngine initialized",
            extra={
                "account": self.account_number,
                "paper_trading": self.is_paper_trading,
                "state_path": str(self.state_path),
            },
        )

    def start(self) -> RecoveryReport:
        """Start the trading engine.

        This method:
        1. Loads persisted state from disk
        2. Runs startup reconciliation to detect discrepancies
        3. Starts background monitoring threads

        Returns:
            RecoveryReport: Summary of startup reconciliation results

        Raises:
            RuntimeError: If engine is already running
        """
        if self._running:
            raise RuntimeError("Engine is already running")

        logger.info("Starting TradingEngine")
        self._guardrail_notifications_sent.clear()
        self._clear_buy_guard()
        self._last_market_data_success_at = None
        self._last_reconciliation_success_at = None
        self._last_balance_refresh_success_at = None
        self._last_broker_snapshot_at = None
        self._operator_action_required = False
        self._open_order_count = 0
        self._snapshot_stale = False
        self._handoff_reason = None
        self._last_broker_snapshot = None

        # Load persisted state
        try:
            loaded_state = load_state(self.state_path)
            if loaded_state:
                self._state = loaded_state
                # Restore positions to position manager
                for position in loaded_state.positions.values():
                    self._position_manager.open_position(position)
                logger.info(
                    f"Loaded {len(loaded_state.positions)} positions from state",
                    extra={"state_path": str(self.state_path)},
                )
        except Exception as e:
            logger.warning(f"Failed to load state: {e}. Starting with empty state.")

        self._restore_risk_controls()
        self._restore_runtime_metadata()
        self._seed_executor_idempotency_keys()

        # Run preflight checks
        preflight_errors = self._run_preflight_checks()
        if preflight_errors:
            raise RuntimeError(f"Preflight checks failed: {'; '.join(preflight_errors)}")

        # Run startup reconciliation
        recovery_report = startup_reconciliation(
            local_state=self._state,
            client=self.client,
            inquire_balance_func=self._inquire_balance,
            inquire_daily_orders_func=self._inquire_daily_orders,
            fetch_account_truth_func=self._fetch_account_truth,
            save_state_func=save_state_atomic,
            state_path=self.state_path,
        )
        self._sync_position_manager_from_state()
        recovery_result = self._coerce_recovery_result(recovery_report.result)
        self._last_recovery_result = recovery_result
        self._degraded_reason = None
        raw_pending_orders = getattr(recovery_report, "pending_orders", [])
        unresolved_order_count = (
            len(raw_pending_orders)
            if isinstance(raw_pending_orders, (list, tuple, set, dict))
            else 0
        )
        startup_guard = evaluate_startup_guard(
            is_paper_trading=self.is_paper_trading,
            allow_unsafe_trading=self.config.allow_unsafe_trading,
            recovery_mode=self.config.recovery_mode,
            recovery_result=recovery_result.value,
            unresolved_order_count=unresolved_order_count,
        )

        # Log recovery results
        logger.info(
            "Startup reconciliation complete",
            extra={
                "result": recovery_report.result,
                "errors": len(recovery_report.errors),
                "orphan_positions": len(recovery_report.orphan_positions),
                "missing_positions": len(recovery_report.missing_positions),
            },
        )

        self._note_reconciliation_success()
        self._set_operational_state(
            operational_state=startup_guard.operational_state,
            degraded_reason=startup_guard.degraded_reason,
        )

        if self._daily_kill_switch_active:
            self._latch_trading_guard(degraded_reason="daily_loss_killswitch")

        # Update state after reconciliation
        self._update_state()
        self._persist_state()

        self._running = True
        self._start_monotonic = time.monotonic()

        # Start background monitoring threads
        symbols = list(self._position_manager.get_all_positions().keys())
        realtime_startup = self._start_realtime_streams(symbols)
        if symbols and not realtime_startup.quote_stream_active:
            self._ensure_polling_fallback(symbols)
        if realtime_startup.should_block_trading:
            self._latch_trading_guard(degraded_reason=realtime_startup.degraded_reason)
            self._notify_guardrail_once(
                key="execution_stream_unavailable",
                event_type="error.execution_stream_unavailable",
                level=NotificationLevel.CRITICAL,
                title="Execution Stream Unavailable",
                error_type="ExecutionStreamUnavailable",
                error_category="broker_stream",
                operation="websocket_execution_stream_startup",
                recoverable=bool(self.is_paper_trading or self.config.allow_unsafe_trading),
                error_message="WebSocket execution stream unavailable during startup.",
                is_paper_trading=self.is_paper_trading,
            )
        self._reconciler.start()

        self._start_strategy_orchestration()
        logger.info("TradingEngine started successfully")

        # Notify engine started
        self._notify(
            "engine.started",
            NotificationLevel.INFO,
            "Engine Started",
            position_count=len(self._position_manager.get_all_positions()),
            recovery_result=recovery_result.value,
            is_paper_trading=self.is_paper_trading,
            operational_state=self._operational_state,
            buying_enabled=self._buying_enabled,
            buy_blocked_reason=self._buy_blocked_reason,
            trading_enabled=self._trading_enabled,
            degraded_reason=self._degraded_reason,
        )

        # Notify recovery events
        if recovery_result == RecoveryResult.RECONCILED:
            self._notify(
                "recovery.reconciled",
                NotificationLevel.WARNING,
                "Recovery: Position Reconciled",
                orphan_positions=recovery_report.orphan_positions,
                missing_positions=recovery_report.missing_positions,
                quantity_mismatches=recovery_report.quantity_mismatches,
            )
        elif recovery_result == RecoveryResult.FAILED:
            self._notify(
                "recovery.failed",
                NotificationLevel.CRITICAL,
                "Recovery Failed",
                errors=recovery_report.errors,
            )

        return recovery_report

    def stop(self, timeout: float = 10.0):
        """Stop the trading engine gracefully.

        Args:
            timeout: Maximum time to wait for threads to stop (seconds)

        Raises:
            RuntimeError: If engine is not running
        """
        if not self._running:
            raise RuntimeError("Engine is not running")

        logger.info("Stopping TradingEngine")
        handoff = evaluate_session_handoff(
            has_positions=bool(self._position_manager.get_all_positions()),
            operator_action_required=self._operator_action_required,
        )
        if handoff.require_operator_handoff:
            self._handoff_reason = handoff.summary
            snapshot = self._capture_account_truth(reason=handoff.summary or "operator_handoff")
            self._log_runtime_event(
                "operator.handoff_required",
                summary=handoff.summary,
                position_count=len(self._position_manager.get_all_positions()),
                snapshot=self._snapshot_payload(snapshot) if snapshot is not None else None,
            )
            self._notify(
                "operator.handoff_required",
                NotificationLevel.WARNING,
                "Operator Handoff Required",
                summary=handoff.summary,
                position_count=len(self._position_manager.get_all_positions()),
                operator_action_required=self._operator_action_required,
                open_order_count=self._open_order_count,
            )

        self._stop_strategy_orchestration(timeout=timeout / 2)

        # Stop monitoring threads (they handle joining internally)
        self._price_monitor.stop(timeout=timeout / 2)
        self._stop_realtime_streams()
        self._reconciler.stop(timeout=timeout / 2)

        # Final state save
        self._update_state()
        self._persist_state()

        self._running = False
        self._set_operational_state(
            operational_state="blocked",
            degraded_reason=self._degraded_reason,
        )
        logger.info("TradingEngine stopped")

        # Notify engine stopped
        self._notify(
            "engine.stopped",
            NotificationLevel.INFO,
            "Engine Stopped",
            position_count=len(self._position_manager.get_all_positions()),
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: int,
        stop_loss: Optional[int] = None,
        take_profit: Optional[int] = None,
        origin: str = "manual",
    ) -> OrderResult:
        """Place a buy order with risk validation.

        Args:
            symbol: Stock symbol code (e.g., "005930" for Samsung)
            quantity: Number of shares to buy
            price: Limit price per share (KRW)
            stop_loss: Optional stop-loss price (KRW)
            take_profit: Optional take-profit price (KRW)

        Returns:
            OrderResult: Result of the order placement

        Raises:
            RuntimeError: If engine is not running
        """
        symbol = symbol.strip().upper()
        self._ensure_running()

        rejection = self._maybe_reject_buy(
            symbol=symbol,
            quantity=quantity,
            price=price,
        )
        if rejection is not None:
            return rejection

        # Market hours check - block buys outside trading hours
        if self._should_enforce_market_hours() and not self._is_market_open():
            reason = "Market is closed (trading hours: 09:00-15:20 KST, weekdays)"
            self._notify(
                "order.rejected",
                NotificationLevel.WARNING,
                "Market Closed",
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
                reason=reason,
            )
            return OrderResult(success=False, order_id="", message=reason)

        logger.info(
            f"Buy order requested: {symbol} qty={quantity} price={price}",
            extra={
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            },
        )

        if not self._ensure_fresh_runtime_guardrails_for_buy(
            symbol=symbol,
            quantity=quantity,
            price=price,
        ):
            return self._build_buy_guard_rejection(symbol=symbol, quantity=quantity, price=price)

        if not self._refresh_risk_state(order_price=price, order_quantity=quantity, for_buy=True):
            return self._build_buy_guard_rejection(symbol=symbol, quantity=quantity, price=price)

        rejection = self._maybe_reject_buy(
            symbol=symbol,
            quantity=quantity,
            price=price,
        )
        if rejection is not None:
            return rejection

        risk_result = self._risk_manager.validate_order(
            symbol=symbol,
            quantity=quantity,
            price=Decimal(str(price)),
            side="buy",
        )
        if not risk_result.approved:
            if self.config.risk_enforcement_mode == "enforce":
                self._notify(
                    "order.rejected",
                    NotificationLevel.WARNING,
                    "Order Rejected",
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=price,
                    reason=risk_result.reason,
                )
                return OrderResult(success=False, order_id="", message=risk_result.reason)
            elif self.config.risk_enforcement_mode == "warn":
                logger.warning(f"Risk check failed (warn mode): {risk_result.reason}")
                self._notify(
                    "risk.warning",
                    NotificationLevel.WARNING,
                    "Risk Warning",
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=price,
                    reason=risk_result.reason,
                )
                # Continue with order despite risk warning

        order_quantity = (
            risk_result.adjusted_quantity
            if risk_result.adjusted_quantity is not None
            else quantity
        )

        current_position = self._position_manager.get_position(symbol)
        with self._state_lock:
            order = self._create_order_intent(
                symbol=symbol,
                side="buy",
                quantity=order_quantity,
                price=price,
                origin=origin,
                requested_stop_loss=stop_loss,
                requested_take_profit=take_profit,
                position_quantity_at_submit=current_position.quantity if current_position else 0,
            )
            self._state.pending_orders[order.order_id] = order
            self._update_state_unlocked()
        self._persist_state()

        result = self._submit_order_intent(order)

        if result.success:
            self._log_runtime_event(
                "order_state_transition",
                order_id=order.order_id,
                symbol=symbol,
                side="buy",
                status=order.status.value,
                resolution_source=None,
            )
            self._notify(
                "order.submitted",
                NotificationLevel.INFO,
                "Order Submitted",
                symbol=symbol,
                side="BUY",
                quantity=order_quantity,
                price=price,
                broker_order_id=result.broker_order_id,
                order_id=order.order_id,
            )
        elif getattr(result, "submission_unknown", False) is True:
            self._notify(
                "order.unresolved",
                NotificationLevel.WARNING,
                "Order Unresolved",
                symbol=symbol,
                side="BUY",
                quantity=order_quantity,
                price=price,
                broker_order_id=order.broker_order_id,
                order_id=order.order_id,
                reason="submission_result_unknown",
            )
        else:
            self._notify(
                "order.rejected",
                NotificationLevel.WARNING,
                "Order Rejected",
                symbol=symbol,
                side="BUY",
                quantity=order_quantity,
                price=price,
                reason=result.message,
            )

        return result

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: int | None = None,
        *,
        origin: str = "manual",
        exit_reason: str | None = None,
    ) -> OrderResult:
        """Place a sell order to exit a position.

        Args:
            symbol: Stock symbol code
            quantity: Number of shares to sell
            price: Limit price per share (KRW), or None for market order

        Returns:
            OrderResult: Result of the order placement

        Raises:
            RuntimeError: If engine is not running
        """
        symbol = symbol.strip().upper()
        self._ensure_running()

        position = self._position_manager.get_position(symbol)
        rejection = self._maybe_reject_sell(
            symbol=symbol,
            quantity=quantity,
            price=price,
            position_quantity=position.quantity if position is not None else 0,
        )
        if rejection is not None:
            return rejection
        assert position is not None

        logger.info(
            f"Sell order requested: {symbol} qty={quantity} price={price}",
            extra={"symbol": symbol, "quantity": quantity, "price": price},
        )

        with self._state_lock:
            order = self._create_order_intent(
                symbol=symbol,
                side="sell",
                quantity=quantity,
                price=price,
                origin=origin,
                exit_reason=exit_reason,
                position_quantity_at_submit=position.quantity,
            )
            self._state.pending_orders[order.order_id] = order
            self._update_state_unlocked()
        self._persist_state()

        result = self._submit_order_intent(order)

        if result.success:
            self._log_runtime_event(
                "order_state_transition",
                order_id=order.order_id,
                symbol=symbol,
                side="sell",
                status=order.status.value,
                resolution_source=None,
                exit_reason=exit_reason,
            )
            self._notify(
                "order.submitted",
                NotificationLevel.INFO,
                "Order Submitted",
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
                broker_order_id=result.broker_order_id,
                order_id=order.order_id,
                exit_reason=exit_reason,
            )
        elif getattr(result, "submission_unknown", False) is True:
            self._notify(
                "order.unresolved",
                NotificationLevel.WARNING,
                "Order Unresolved",
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
                broker_order_id=order.broker_order_id,
                order_id=order.order_id,
                reason="submission_result_unknown",
                exit_reason=exit_reason,
            )
        else:
            self._notify(
                "order.rejected",
                NotificationLevel.WARNING,
                "Order Rejected",
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
                reason=result.message,
            )

        return result

    def get_positions(self) -> dict[str, Position]:
        """Get all current positions.

        Returns:
            Dictionary mapping symbol to Position
        """
        return self._position_manager.get_all_positions()

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position by symbol.

        Args:
            symbol: Stock symbol code

        Returns:
            Position if exists, None otherwise
        """
        return self._position_manager.get_position(symbol)

    def get_balance(self) -> dict:
        """Get account balance via broker API.

        Returns:
            Balance response dict with output1 (holdings) and output2 (summary)

        Raises:
            RuntimeError: If engine is not running
        """
        self._ensure_running()
        snapshot = self._fetch_account_truth()
        return {
            "output1": list(snapshot.positions),
            "output2": [dict(snapshot.cash)],
            "_snapshot_metadata": {
                "fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_ok": snapshot.snapshot_ok,
                "open_order_count": len(snapshot.open_orders),
                "operator_action_required": self._operator_action_required,
                "snapshot_stale": self._snapshot_stale,
                "handoff_reason": self._handoff_reason,
            },
        }

    def get_daily_orders(self) -> dict:
        """Get today's order/execution history via broker API.

        Returns:
            Daily order conclusion response dict with output1 (orders)

        Raises:
            RuntimeError: If engine is not running
        """
        self._ensure_running()
        response = self._inquire_daily_orders()
        try:
            snapshot = self._fetch_account_truth()
            response["_snapshot_metadata"] = {
                "fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_ok": snapshot.snapshot_ok,
                "open_order_count": len(snapshot.open_orders),
                "operator_action_required": self._operator_action_required,
                "snapshot_stale": self._snapshot_stale,
                "handoff_reason": self._handoff_reason,
            }
        except Exception:
            response["_snapshot_metadata"] = {
                "fetched_at": (
                    self._last_broker_snapshot_at.isoformat()
                    if self._last_broker_snapshot_at is not None
                    else None
                ),
                "snapshot_ok": False,
                "open_order_count": self._open_order_count,
                "operator_action_required": self._operator_action_required,
                "snapshot_stale": True,
                "handoff_reason": self._handoff_reason,
            }
        return response

    def get_open_orders(self) -> dict:
        """Get the current broker open orders via the account-truth snapshot."""
        self._ensure_running()
        snapshot = self._fetch_account_truth()
        return {
            "output1": list(snapshot.open_orders),
            "_view": "open_orders",
            "_snapshot_metadata": {
                "fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_ok": snapshot.snapshot_ok,
                "open_order_count": len(snapshot.open_orders),
                "operator_action_required": self._operator_action_required,
                "snapshot_stale": self._snapshot_stale,
                "handoff_reason": self._handoff_reason,
            },
        }

    def liquidate_all(self) -> list[dict]:
        """Market-sell all open positions.

        Iterates all OPEN/OPEN_RECONCILED positions and places market sell orders.
        Continues even if individual orders fail.

        Returns:
            List of result dicts per position:
            {symbol, quantity, entry_price, success, message, broker_order_id}

        Raises:
            RuntimeError: If engine is not running
        """
        self._ensure_running()
        from stock_manager.trading.models import PositionStatus

        positions = self._position_manager.get_all_positions()
        results: list[dict] = []

        for symbol, pos in positions.items():
            if pos.status not in (PositionStatus.OPEN, PositionStatus.OPEN_RECONCILED):
                continue

            result_entry: dict = {
                "symbol": symbol,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "success": False,
                "message": "",
                "broker_order_id": None,
            }

            try:
                order_result = self.sell(
                    symbol=symbol,
                    quantity=pos.quantity,
                    price=None,
                    origin="liquidate_all",
                    exit_reason="LIQUIDATE_ALL",
                )
                result_entry["success"] = order_result.success
                result_entry["message"] = order_result.message or ""
                result_entry["broker_order_id"] = order_result.broker_order_id
            except Exception as exc:
                result_entry["message"] = str(exc)

            results.append(result_entry)

        return results

    def get_status(self) -> EngineStatus:
        """Get current engine status.

        Returns:
            EngineStatus: Snapshot of engine health and metrics
        """
        # Check reconciler status via thread
        reconciler_running = (
            (self._reconciler._thread is not None and self._reconciler._thread.is_alive())
            if self._running
            else False
        )
        rate_limiter_available = self._rate_limiter.available
        client_rate_available = getattr(self.client, "request_rate_limiter_available", None)
        if isinstance(client_rate_available, int):
            rate_limiter_available = client_rate_available

        operability = self.get_operability()
        return EngineStatus(
            running=self._running,
            position_count=len(self._position_manager.get_all_positions()),
            price_monitor_running=self._price_monitor.is_running,
            reconciler_running=reconciler_running,
            rate_limiter_available=rate_limiter_available,
            state_path=str(self.state_path),
            is_paper_trading=self.is_paper_trading,
            operational_state=operability.operational_state,
            buying_enabled=self._buying_enabled,
            buy_blocked_reason=self._buy_blocked_reason,
            trading_enabled=self._trading_enabled,
            recovery_result=self._last_recovery_result.value,
            degraded_reason=self._degraded_reason,
            operator_action_required=self._operator_action_required,
            last_broker_snapshot_at=(
                self._last_broker_snapshot_at.isoformat()
                if self._last_broker_snapshot_at is not None
                else None
            ),
            open_order_count=self._open_order_count,
            snapshot_stale=self._snapshot_stale,
            handoff_reason=self._handoff_reason,
            strategy_discovery_source=self._strategy_discovery_source,
            strategy_discovery_symbols=self._strategy_discovery_symbols,
            strategy_discovery_reason=self._strategy_discovery_reason,
            strategy_discovery_updated_at=self._strategy_discovery_updated_at,
        )

    def is_healthy(self) -> bool:
        """Quick health check.

        Returns:
            True if engine is running and all components are healthy
        """
        return self.get_operability().is_healthy

    def get_operability(self) -> EngineOperabilityDecision:
        """Return explicit health/readiness/session-liveness signals."""
        rate_limiter_available = self._rate_limiter.available
        client_rate_available = getattr(self.client, "request_rate_limiter_available", None)
        if isinstance(client_rate_available, int):
            rate_limiter_available = client_rate_available

        adapter = self._broker_adapter
        return evaluate_engine_operability(
            running=self._running,
            rate_limiter_available=rate_limiter_available,
            reconciliation_fresh=not self._is_timestamp_stale(
                self._last_reconciliation_success_at,
                self._effective_reconciliation_staleness_sec(),
            ),
            has_positions=bool(self._position_manager.get_all_positions()),
            price_monitor_running=self._price_monitor.is_running,
            market_data_fresh=not self._is_timestamp_stale(
                self._last_market_data_success_at,
                self._effective_quote_staleness_sec(),
            ),
            websocket_monitoring_enabled=bool(
                getattr(self.config, "websocket_monitoring_enabled", False)
            ),
            websocket_connected=bool(getattr(adapter, "websocket_connected", False))
            if adapter is not None
            else False,
            operational_state=self._operational_state,
        )

    # Internal helper methods

    def _on_price_update(self, symbol: str, price: Decimal) -> None:
        """Callback for price updates from monitor.

        Args:
            symbol: Stock symbol code
            price: Current price
        """
        self._note_market_data_success()
        self._position_manager.update_price(symbol, price)

    def _resolve_broker_adapter(self) -> Any | None:
        if self.broker_adapter is not None:
            return self.broker_adapter

        try:
            from stock_manager.adapters.broker.kis.broker_adapter import KISBrokerAdapter
            from stock_manager.adapters.broker.kis.client import KISRestClient
        except Exception:
            return None

        if not isinstance(self.client, KISRestClient):
            return None

        try:
            return KISBrokerAdapter(
                config=self.client.config,
                account_number=self.account_number,
                account_product_code=self.account_product_code,
                rest_client=self.client,
            )
        except Exception:
            logger.warning("Failed to initialize KIS broker adapter", exc_info=True)
            return None

    def _register_websocket_lifecycle_callback(self) -> None:
        adapter = self._broker_adapter
        if adapter is None:
            return

        websocket_client = getattr(adapter, "websocket_client", None)
        register_callback = getattr(websocket_client, "register_lifecycle_callback", None)
        if not callable(register_callback):
            return

        try:
            register_callback(self._on_websocket_lifecycle)
        except Exception:
            logger.debug("Failed to register websocket lifecycle callback", exc_info=True)

    def _ensure_polling_fallback(self, symbols: list[str]) -> None:
        normalized = [symbol.strip().upper() for symbol in symbols if str(symbol).strip()]
        if not normalized:
            return

        self._note_market_data_success()
        if not self._price_monitor.is_running:
            self._price_monitor.start(normalized, self._on_price_update)
            return

        for symbol in normalized:
            self._price_monitor.add_symbol(symbol)

    def _notify_guardrail_once(
        self,
        *,
        key: str,
        event_type: str,
        level: NotificationLevel,
        title: str,
        **details: Any,
    ) -> None:
        if key in self._guardrail_notifications_sent:
            return
        self._guardrail_notifications_sent.add(key)
        self._notify(event_type, level, title, **details)

    def _set_operational_state(
        self,
        *,
        operational_state: OperationalState,
        degraded_reason: str | None,
    ) -> None:
        self._operational_state = operational_state
        self._buying_enabled = operational_state == "normal"
        self._buy_blocked_reason = None if self._buying_enabled else degraded_reason
        self._trading_enabled = self._buying_enabled
        self._degraded_reason = None if operational_state == "normal" else degraded_reason

    def _clear_buy_guard(self) -> None:
        self._set_operational_state(operational_state="normal", degraded_reason=None)

    def _seed_executor_idempotency_keys(self) -> None:
        keys = {
            order.idempotency_key
            for order in self._state.pending_orders.values()
            if isinstance(order, Order)
            and order.status in {
                OrderStatus.SUBMITTED,
                OrderStatus.PENDING_BROKER,
                OrderStatus.PARTIAL_FILL,
            }
            and order.idempotency_key
        }
        self._executor._submitted_keys.update(keys)

    def _note_market_data_success(self) -> None:
        self._last_market_data_success_at = datetime.now(timezone.utc)

    def _note_reconciliation_success(self) -> None:
        self._last_reconciliation_success_at = datetime.now(timezone.utc)

    def _note_balance_refresh_success(self) -> None:
        self._last_balance_refresh_success_at = datetime.now(timezone.utc)

    def _effective_quote_staleness_sec(self) -> float:
        configured = getattr(self.config, "quote_staleness_sec", None)
        if configured is not None:
            return float(configured)
        polling_interval = float(getattr(self.config, "polling_interval_sec", 2.0) or 2.0)
        return max(3 * polling_interval, 15.0)

    def _effective_reconciliation_staleness_sec(self) -> float:
        return float(getattr(self.config, "reconciliation_staleness_sec", 180.0))

    @staticmethod
    def _is_timestamp_stale(timestamp: datetime | None, threshold_sec: float) -> bool:
        if threshold_sec <= 0:
            return False
        if timestamp is None:
            return True
        return (datetime.now(timezone.utc) - timestamp).total_seconds() > threshold_sec

    def _is_monitoring_path_active(self) -> bool:
        if self._price_monitor.is_running:
            return True

        adapter = self._broker_adapter
        if adapter is not None and bool(getattr(self.config, "websocket_monitoring_enabled", False)):
            return bool(getattr(adapter, "websocket_connected", False))

        return False

    def _should_bypass_runtime_buy_guard(self) -> bool:
        return self.is_paper_trading or self.config.allow_unsafe_trading

    def _current_buy_block_reason(self) -> str | None:
        if self._daily_kill_switch_active:
            return "daily_loss_killswitch"
        return self._buy_blocked_reason or self._degraded_reason

    @staticmethod
    def _order_rejection_reason(
        *,
        symbol: str,
        side: Literal["buy", "sell"],
        decision: Any,
        degraded_reason: str | None,
    ) -> str:
        reject_code = getattr(decision, "reject_code", None)
        if reject_code == "pending_same_side":
            return f"Pending {side.upper()} order already exists for {symbol}"
        if reject_code == "no_open_position":
            return f"No open position for {symbol}"
        if reject_code == "exceeds_position":
            return "sell_quantity_exceeds_position"
        if reject_code == "invalid_quantity":
            return "invalid_order_quantity"
        if reject_code == "trading_disabled":
            return degraded_reason or "trading_disabled"
        return degraded_reason or "trading_disabled"

    def _reject_order(
        self,
        *,
        symbol: str,
        side: Literal["buy", "sell"],
        quantity: int,
        price: int | None,
        reason: str,
    ) -> OrderResult:
        self._notify(
            "order.rejected",
            NotificationLevel.WARNING,
            "Order Rejected",
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            price=price,
            reason=reason,
        )
        return OrderResult(success=False, order_id="", message=reason)

    def _build_buy_guard_rejection(self, *, symbol: str, quantity: int, price: int) -> OrderResult:
        reason = self._current_buy_block_reason() or "trading_disabled"
        return self._reject_order(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            reason=reason,
        )

    def _maybe_reject_buy(self, *, symbol: str, quantity: int, price: int) -> OrderResult | None:
        decision = evaluate_order_permission(
            operational_state=self._operational_state,
            side="buy",
            position_quantity=0,
            requested_quantity=quantity,
            has_pending_same_side=self._has_pending_order(symbol, side="buy"),
        )
        if decision.allowed and not self._daily_kill_switch_active:
            return None
        reason = self._order_rejection_reason(
            symbol=symbol,
            side="buy",
            decision=decision,
            degraded_reason=self._current_buy_block_reason(),
        )
        return self._reject_order(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            reason=reason,
        )

    def _maybe_reject_sell(
        self,
        *,
        symbol: str,
        quantity: int,
        price: int | None,
        position_quantity: int,
    ) -> OrderResult | None:
        decision = evaluate_order_permission(
            operational_state=self._operational_state,
            side="sell",
            position_quantity=position_quantity,
            requested_quantity=quantity,
            has_pending_same_side=self._has_pending_order(symbol, side="sell"),
        )
        if decision.allowed:
            return None
        reason = self._order_rejection_reason(
            symbol=symbol,
            side="sell",
            decision=decision,
            degraded_reason=self._degraded_reason,
        )
        return self._reject_order(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price,
            reason=reason,
        )

    def _ensure_fresh_runtime_guardrails_for_buy(
        self,
        *,
        symbol: str,
        quantity: int,
        price: int,
    ) -> bool:
        if self._should_bypass_runtime_buy_guard():
            return True

        if self._is_timestamp_stale(
            self._last_reconciliation_success_at,
            self._effective_reconciliation_staleness_sec(),
        ):
            self._latch_trading_guard(degraded_reason="reconciliation_stale")
            self._notify_guardrail_once(
                key="reconciliation_stale",
                event_type="error.reconciliation_stale",
                level=NotificationLevel.CRITICAL,
                title="Reconciliation Stale",
                error_type="ReconciliationStale",
                error_category="broker_state",
                operation="runtime_reconciliation",
                recoverable=False,
                error_message="Runtime reconciliation freshness exceeded threshold.",
                threshold_sec=self._effective_reconciliation_staleness_sec(),
                is_paper_trading=self.is_paper_trading,
            )
            return False

        if not self._position_manager.get_all_positions():
            return True

        if self._is_timestamp_stale(
            self._last_market_data_success_at,
            self._effective_quote_staleness_sec(),
        ):
            self._latch_trading_guard(degraded_reason="market_data_stale")
            self._notify_guardrail_once(
                key="market_data_stale",
                event_type="error.market_data_stale",
                level=NotificationLevel.CRITICAL,
                title="Market Data Stale",
                error_type="MarketDataStale",
                error_category="market_data",
                operation="price_monitoring",
                recoverable=False,
                error_message="Market data freshness exceeded threshold.",
                threshold_sec=self._effective_quote_staleness_sec(),
                symbol=symbol,
                quantity=quantity,
                price=price,
                is_paper_trading=self.is_paper_trading,
            )
            return False

        return True

    def _latch_trading_guard(self, *, degraded_reason: str | None) -> None:
        candidate_state = resolve_operational_state(degraded_reason=degraded_reason)
        state_rank = {"normal": 0, "degraded_reduce_only": 1, "blocked": 2}
        current_rank = state_rank[self._operational_state]
        candidate_rank = state_rank[candidate_state]
        if candidate_rank < current_rank:
            return

        next_reason = self._degraded_reason
        if candidate_rank > current_rank:
            next_reason = degraded_reason
        elif degraded_reason and self._degraded_reason in (None, "daily_loss_killswitch"):
            next_reason = degraded_reason

        self._set_operational_state(
            operational_state=candidate_state,
            degraded_reason=next_reason,
        )

    def _apply_runtime_fault(self, *, fault: str, handoff_reason: str | None = None) -> RuntimeFaultDecision:
        decision = evaluate_runtime_fault(fault=fault)
        if decision.action != "log_only":
            degraded_reason = decision.degraded_reason or self._degraded_reason
            self._latch_trading_guard(degraded_reason=degraded_reason)
        if decision.operator_action_required:
            self._operator_action_required = True
            if handoff_reason:
                self._handoff_reason = handoff_reason
        return decision

    @staticmethod
    def _normalize_open_order_side(value: Any) -> str | None:
        normalized = str(value or "").strip().lower()
        if normalized in {"buy", "b", "2", "02"}:
            return "buy"
        if normalized in {"sell", "s", "1", "01"}:
            return "sell"
        return None

    def _find_matching_open_order(
        self,
        *,
        order: Order,
        open_orders: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for item in open_orders:
            if not isinstance(item, dict):
                continue
            broker_order_id = item.get("broker_order_id")
            if order.broker_order_id and broker_order_id not in (None, ""):
                if str(broker_order_id) == order.broker_order_id:
                    return item

        candidates: list[dict[str, Any]] = []
        for item in open_orders:
            if not isinstance(item, dict):
                continue
            if str(item.get("symbol") or "").strip().upper() != order.symbol:
                continue
            if self._normalize_open_order_side(item.get("side")) != order.side:
                continue
            candidates.append(item)

        if len(candidates) == 1:
            return candidates[0]
        return None

    def _start_realtime_streams(self, symbols: list[str]) -> Any:
        adapter = self._broker_adapter
        websocket_monitoring_enabled = bool(getattr(self.config, "websocket_monitoring_enabled", False))
        websocket_execution_notice_enabled = bool(
            getattr(self.config, "websocket_execution_notice_enabled", False)
        )
        quote_stream_active = False
        execution_stream_active = not websocket_execution_notice_enabled
        if adapter is None:
            return evaluate_realtime_startup(
                is_paper_trading=self.is_paper_trading,
                allow_unsafe_trading=self.config.allow_unsafe_trading,
                websocket_monitoring_enabled=websocket_monitoring_enabled,
                websocket_execution_notice_enabled=websocket_execution_notice_enabled,
                quote_subscription_succeeded=False,
                execution_subscription_succeeded=execution_stream_active,
            )

        if websocket_monitoring_enabled and symbols:
            try:
                adapter.subscribe_quotes(symbols=symbols, callback=self._on_websocket_quote)
                quote_stream_active = True
                self._note_market_data_success()
            except Exception:
                logger.warning(
                    "WebSocket quote stream unavailable; falling back to polling",
                    exc_info=True,
                )

        if websocket_execution_notice_enabled:
            try:
                adapter.subscribe_executions(callback=self._on_websocket_execution)
                execution_stream_active = True
            except Exception:
                logger.warning("WebSocket execution stream unavailable", exc_info=True)

        return evaluate_realtime_startup(
            is_paper_trading=self.is_paper_trading,
            allow_unsafe_trading=self.config.allow_unsafe_trading,
            websocket_monitoring_enabled=websocket_monitoring_enabled,
            websocket_execution_notice_enabled=websocket_execution_notice_enabled,
            quote_subscription_succeeded=quote_stream_active,
            execution_subscription_succeeded=execution_stream_active,
        )

    def _stop_realtime_streams(self) -> None:
        adapter = self._broker_adapter
        if adapter is None:
            return
        try:
            adapter.disconnect_websocket()
        except Exception:
            logger.debug("Failed to stop websocket streams cleanly", exc_info=True)

    def _ensure_symbol_monitoring(self, symbol: str) -> None:
        normalized = symbol.strip().upper()
        if not normalized:
            return

        adapter = self._broker_adapter
        if adapter is not None and bool(
            getattr(self.config, "websocket_monitoring_enabled", False)
        ):
            try:
                adapter.subscribe_quotes(symbols=[normalized], callback=self._on_websocket_quote)
                self._note_market_data_success()
                return
            except Exception:
                logger.warning(
                    "WebSocket quote subscription failed; using polling monitor",
                    exc_info=True,
                )

        if not self._price_monitor.is_running:
            self._note_market_data_success()
            self._price_monitor.start([], self._on_price_update)
        self._price_monitor.add_symbol(normalized)

    def _on_websocket_quote(self, event: Any) -> None:
        symbol = str(getattr(event, "symbol", "")).strip().upper()
        if not symbol:
            return

        ask_price = getattr(event, "ask_price", None)
        bid_price = getattr(event, "bid_price", None)
        price = ask_price if ask_price is not None else bid_price
        if price is None:
            return

        self._on_price_update(symbol, price)

    def _on_websocket_execution(self, event: Any) -> None:
        symbol = str(getattr(event, "symbol", "")).strip().upper()
        order_id = getattr(event, "broker_order_id", None) or getattr(event, "order_id", None)
        side = getattr(event, "side", None)
        price = getattr(event, "executed_price", None) or getattr(event, "price", None)
        quantity = getattr(event, "executed_quantity", None) or getattr(event, "quantity", None)

        self._notify(
            "order.execution_notice",
            NotificationLevel.INFO,
            "Execution Notice",
            symbol=symbol or None,
            order_id=str(order_id) if order_id not in (None, "") else None,
            side=str(side) if side not in (None, "") else None,
            price=str(price) if price not in (None, "") else None,
            quantity=str(quantity) if quantity not in (None, "") else None,
        )

        try:
            self._apply_execution_event(event)
            self._reconciler.reconcile_now()
        except Exception:
            logger.debug("Execution reconciliation failed", exc_info=True)
            self._apply_runtime_fault(
                fault="execution_apply_failed",
                handoff_reason="execution_apply_failed",
            )
            self._capture_account_truth(reason="execution_apply_failed")

    def _on_websocket_lifecycle(self, event: Any) -> None:
        if not self._running:
            return

        status = str(getattr(event, "status", "")).strip().lower()
        decision = evaluate_websocket_guard(
            lifecycle_status=status,  # type: ignore[arg-type]
            is_paper_trading=self.is_paper_trading,
            allow_unsafe_trading=self.config.allow_unsafe_trading,
            websocket_monitoring_enabled=bool(
                getattr(self.config, "websocket_monitoring_enabled", False)
            ),
            websocket_execution_notice_enabled=bool(
                getattr(self.config, "websocket_execution_notice_enabled", False)
            ),
        )
        if status != "reconnect_exhausted":
            return

        if decision.start_polling_fallback and "quote_stream_fallback_enabled" not in self._guardrail_notifications_sent:
            self._guardrail_notifications_sent.add("quote_stream_fallback_enabled")
            fallback_symbols = list(self._position_manager.get_all_positions().keys())
            self._ensure_polling_fallback(fallback_symbols)
            logger.warning(
                "WebSocket quote stream exhausted; polling fallback enabled",
                extra={"symbol_count": len(fallback_symbols)},
            )

        execution_enabled = bool(
            getattr(self.config, "websocket_execution_notice_enabled", False)
        )
        if execution_enabled:
            level = (
                NotificationLevel.CRITICAL
                if decision.should_block_trading
                else NotificationLevel.WARNING
            )
            self._notify_guardrail_once(
                key="execution_stream_unavailable",
                event_type="error.execution_stream_unavailable",
                level=level,
                title="Execution Stream Unavailable",
                error_type="ExecutionStreamUnavailable",
                error_category="broker_stream",
                operation="websocket_execution_stream",
                recoverable=bool(self.is_paper_trading or self.config.allow_unsafe_trading),
                error_message="WebSocket execution stream reconnect exhausted.",
                reconnect_attempts=getattr(event, "reconnect_attempts", None),
                is_paper_trading=self.is_paper_trading,
            )

        if decision.should_block_trading:
            self._latch_trading_guard(degraded_reason=decision.degraded_reason)

    def _discover_strategy_symbols(self) -> StrategyDiscoveryResult:
        limit = int(getattr(self.config, "strategy_discovery_limit", 0) or 0)
        if limit <= 0:
            return StrategyDiscoveryResult(
                symbols=(),
                source="none",
                reason="discovery_limit_non_positive",
            )

        fallback = self._normalize_symbol_entries(
            getattr(self.config, "strategy_discovery_fallback_symbols", ())
        )
        fallback_symbols = tuple(fallback[:limit])

        if self.is_paper_trading:
            reason = "paper_trading_mode" if fallback_symbols else "paper_trading_mode_no_fallback"
            return StrategyDiscoveryResult(
                symbols=fallback_symbols,
                source="mock_fallback",
                reason=reason,
            )

        try:
            from stock_manager.adapters.broker.kis.apis.domestic_stock.ranking import (
                get_volume_rank,
            )

            response = get_volume_rank(
                self.client,
                is_paper_trading=False,
                FID_COND_MRKT_DIV_CODE="J",
                FID_COND_SCR_DIV_CODE="20171",
                FID_INPUT_ISCD="0001",
                FID_DIV_CLS_CODE="0",
                FID_BLNG_CLS_CODE="0",
                FID_TRGT_CLS_CODE="111111111",
                FID_TRGT_EXLS_CLS_CODE="000000",
                FID_INPUT_PRICE_1="",
                FID_INPUT_PRICE_2="",
                FID_VOL_CNT="",
                FID_INPUT_DATE_1="",
            )
        except Exception:
            logger.warning("Strategy symbol discovery failed", exc_info=True)
            return StrategyDiscoveryResult(
                symbols=fallback_symbols,
                source="fallback",
                reason="volume_rank_request_failed",
            )

        rt_cd = str(response.get("rt_cd", "1"))
        if rt_cd != "0":
            return StrategyDiscoveryResult(
                symbols=fallback_symbols,
                source="fallback",
                reason=f"volume_rank_rt_cd_{rt_cd}",
            )

        output = response.get("output", [])
        if not isinstance(output, list):
            return StrategyDiscoveryResult(
                symbols=fallback_symbols,
                source="fallback",
                reason="volume_rank_output_invalid",
            )

        discovered: list[str] = []
        seen: set[str] = set()
        for item in output:
            if not isinstance(item, dict):
                continue
            symbol = self._extract_discovery_symbol(item)
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            discovered.append(symbol)
            if len(discovered) >= limit:
                break

        if discovered:
            return StrategyDiscoveryResult(
                symbols=tuple(discovered),
                source="volume_rank",
                reason=None,
            )
        return StrategyDiscoveryResult(
            symbols=fallback_symbols,
            source="fallback",
            reason="volume_rank_empty_output",
        )

    @staticmethod
    def _extract_discovery_symbol(payload: dict[str, Any]) -> str:
        for key in (
            "mksc_shrn_iscd",
            "stck_shrn_iscd",
            "pdno",
            "iscd",
            "ISCD",
            "fid_input_iscd",
            "symbol",
            "SYMBOL",
        ):
            value = payload.get(key)
            if value in (None, ""):
                continue

            symbol = str(value).strip().upper()
            if symbol.startswith("A") and len(symbol) == 7 and symbol[1:].isdigit():
                symbol = symbol[1:]
            if symbol:
                return symbol
        return ""

    @staticmethod
    def _normalize_symbol_entries(values: Any) -> list[str]:
        if not isinstance(values, (list, tuple, set)):
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            symbol = str(value).strip().upper()
            if not symbol:
                continue
            if symbol.startswith("A") and len(symbol) == 7 and symbol[1:].isdigit():
                symbol = symbol[1:]
            if symbol in seen:
                continue
            seen.add(symbol)
            normalized.append(symbol)

        return normalized

    def _update_strategy_discovery_state(
        self,
        *,
        source: StrategyDiscoverySource,
        symbols: tuple[str, ...],
        reason: str | None,
        notify_discovery: bool,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        fingerprint = f"{source}|{','.join(symbols)}|{reason or ''}"
        changed = fingerprint != self._strategy_discovery_last_fingerprint

        self._strategy_discovery_source = source
        self._strategy_discovery_symbols = symbols
        self._strategy_discovery_reason = reason
        self._strategy_discovery_updated_at = now_iso
        self._strategy_discovery_last_fingerprint = fingerprint

        log_payload: dict[str, Any] = {
            "source": source,
            "symbols": list(symbols),
            "reason": reason,
            "changed": changed,
            "notify_discovery": notify_discovery,
        }
        if changed:
            logger.info("Strategy symbol resolution updated", extra=log_payload)
            if notify_discovery:
                notify_payload: dict[str, Any] = {
                    "discovery_source": source,
                    "symbols": list(symbols),
                    "symbol_count": len(symbols),
                }
                if reason:
                    notify_payload["discovery_reason"] = reason
                self._notify(
                    "pipeline.screening_complete",
                    NotificationLevel.INFO,
                    "종목 탐색 완료",
                    **notify_payload,
                )
        else:
            logger.debug("Strategy symbol resolution unchanged", extra=log_payload)

    def _persist_state(self):
        """Save current state to disk atomically."""
        try:
            with self._state_lock:
                snapshot = TradingState.from_dict(self._state.to_dict())
            save_state_atomic(snapshot, self.state_path)
            logger.debug(f"State persisted to {self.state_path}")
        except Exception as e:
            logger.error(f"Failed to persist state: {e}", exc_info=True)
            self._notify(
                "error.state_persistence_failed",
                NotificationLevel.WARNING,
                "상태 저장 실패",
                **self._build_error_context(e, operation="state_persistence"),
            )

    def _update_state(self):
        """Sync positions from position manager to state."""
        with self._state_lock:
            self._update_state_unlocked()

    def _update_state_unlocked(self) -> None:
        self._state.positions = self._position_manager.get_all_positions()
        self._state.risk_controls = self._export_risk_controls()
        self._state.runtime_metadata = self._export_runtime_metadata()
        self._state.last_updated = datetime.now(timezone.utc)

    def _export_runtime_metadata(self) -> dict[str, Any]:
        snapshot = self._last_broker_snapshot
        serialized_snapshot: dict[str, Any] | None = None
        if snapshot is not None:
            serialized_snapshot = {
                "cash": dict(snapshot.cash),
                "positions": list(snapshot.positions),
                "open_orders": list(snapshot.open_orders),
                "fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_ok": snapshot.snapshot_ok,
            }

        return {
            "operator_action_required": self._operator_action_required,
            "last_broker_snapshot_at": (
                self._last_broker_snapshot_at.isoformat()
                if self._last_broker_snapshot_at is not None
                else None
            ),
            "open_order_count": self._open_order_count,
            "snapshot_stale": self._snapshot_stale,
            "handoff_reason": self._handoff_reason,
            "last_broker_snapshot": serialized_snapshot,
        }

    def _restore_runtime_metadata(self) -> None:
        metadata = (
            self._state.runtime_metadata
            if isinstance(getattr(self._state, "runtime_metadata", None), dict)
            else {}
        )
        self._operator_action_required = bool(metadata.get("operator_action_required", False))
        self._open_order_count = int(metadata.get("open_order_count", 0) or 0)
        self._snapshot_stale = bool(metadata.get("snapshot_stale", False))
        handoff_reason = metadata.get("handoff_reason")
        self._handoff_reason = str(handoff_reason) if handoff_reason not in (None, "") else None

        last_snapshot_at = metadata.get("last_broker_snapshot_at")
        self._last_broker_snapshot_at = None
        if last_snapshot_at not in (None, ""):
            try:
                self._last_broker_snapshot_at = datetime.fromisoformat(str(last_snapshot_at))
            except Exception:
                self._last_broker_snapshot_at = None

        self._last_broker_snapshot = None
        raw_snapshot = metadata.get("last_broker_snapshot")
        if not isinstance(raw_snapshot, dict):
            return

        fetched_at_raw = raw_snapshot.get("fetched_at")
        fetched_at = datetime.now(timezone.utc)
        if fetched_at_raw not in (None, ""):
            try:
                fetched_at = datetime.fromisoformat(str(fetched_at_raw))
            except Exception:
                fetched_at = datetime.now(timezone.utc)

        raw_positions = raw_snapshot.get("positions", [])
        raw_open_orders = raw_snapshot.get("open_orders", [])
        self._last_broker_snapshot = BrokerTruthSnapshot(
            cash=raw_snapshot.get("cash", {}) if isinstance(raw_snapshot.get("cash"), dict) else {},
            positions=tuple(item for item in raw_positions if isinstance(item, dict)),
            open_orders=tuple(item for item in raw_open_orders if isinstance(item, dict)),
            fetched_at=fetched_at,
            snapshot_ok=bool(raw_snapshot.get("snapshot_ok", False)),
        )

    def _set_broker_snapshot(self, snapshot: BrokerTruthSnapshot) -> None:
        self._last_broker_snapshot = snapshot
        self._last_broker_snapshot_at = snapshot.fetched_at
        self._open_order_count = len(snapshot.open_orders)
        self._snapshot_stale = False
        self._note_balance_refresh_success()

    def _fetch_account_truth(self) -> BrokerTruthSnapshot:
        adapter = self._broker_adapter
        if adapter is not None and hasattr(adapter, "fetch_account_truth"):
            snapshot = adapter.fetch_account_truth()
        else:
            balance_response = self._inquire_balance()
            output2 = balance_response.get("output2", [])
            cash_summary = output2[0] if isinstance(output2, list) and output2 else {}
            positions = balance_response.get("output1", [])
            if not isinstance(positions, list):
                positions = []
            snapshot = BrokerTruthSnapshot(
                cash=cash_summary if isinstance(cash_summary, dict) else {},
                positions=tuple(item for item in positions if isinstance(item, dict)),
                open_orders=(),
                fetched_at=datetime.now(timezone.utc),
                snapshot_ok=True,
            )
        self._set_broker_snapshot(snapshot)
        return snapshot

    def _mark_snapshot_unavailable(self, *, reason: str) -> None:
        self._snapshot_stale = True
        self._handoff_reason = self._handoff_reason or reason

    @staticmethod
    def _snapshot_payload(snapshot: BrokerTruthSnapshot) -> dict[str, Any]:
        return {
            "cash": dict(snapshot.cash),
            "positions": list(snapshot.positions),
            "open_orders": list(snapshot.open_orders),
            "fetched_at": snapshot.fetched_at.isoformat(),
            "snapshot_ok": snapshot.snapshot_ok,
        }

    def _capture_account_truth(self, *, reason: str) -> BrokerTruthSnapshot | None:
        try:
            snapshot = self._fetch_account_truth()
            self._log_runtime_event(
                "account.snapshot",
                reason=reason,
                snapshot=self._snapshot_payload(snapshot),
            )
            with self._state_lock:
                self._update_state_unlocked()
            self._persist_state()
            return snapshot
        except Exception as exc:
            self._mark_snapshot_unavailable(reason=reason)
            self._log_runtime_event(
                "account.snapshot_failed",
                reason=reason,
                error=str(exc),
            )
            with self._state_lock:
                self._update_state_unlocked()
            self._persist_state()
            return None

    def _queue_notification(
        self,
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]],
        event_type: str,
        level: NotificationLevel,
        title: str,
        **details: Any,
    ) -> None:
        notifications.append((event_type, level, title, details))

    def _emit_notifications(
        self, notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]]
    ) -> None:
        for event_type, level, title, details in notifications:
            self._notify(event_type, level, title, **details)

    def _log_runtime_event(self, event: str, **payload: Any) -> None:
        try:
            self._runtime_logger.log_runtime_event(event, **payload)
        except Exception:
            logger.debug("Runtime logger write failed", exc_info=True)

    def _sync_position_manager_from_state(self) -> None:
        desired_positions = self._state.positions if isinstance(self._state.positions, dict) else {}
        current_positions = self._position_manager.get_all_positions()

        for symbol in set(current_positions) - set(desired_positions):
            self._position_manager.close_position(symbol)

        for symbol, raw in desired_positions.items():
            desired = raw if isinstance(raw, Position) else None
            if desired is None:
                continue

            current = self._position_manager.get_position(symbol)
            if current is None:
                self._position_manager.open_position(desired)
                continue

            current.quantity = desired.quantity
            current.entry_price = desired.entry_price
            current.current_price = desired.current_price
            current.stop_loss = desired.stop_loss
            current.take_profit = desired.take_profit
            current.unrealized_pnl = desired.unrealized_pnl
            current.status = desired.status

    def _inquire_daily_orders(self, client=None) -> dict:
        from datetime import date
        from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
            inquire_daily_ccld,
        )

        request_config = inquire_daily_ccld(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            ord_dt=date.today().strftime("%Y%m%d"),
            is_paper_trading=self.is_paper_trading,
        )

        request_client = client or self.client
        return request_client.make_request(
            method="GET",
            path=request_config["url_path"],
            params=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )

    def _has_pending_order(self, symbol: str, *, side: str | None = None) -> bool:
        with self._state_lock:
            return self._has_pending_order_unlocked(symbol, side=side)

    def _has_pending_order_unlocked(self, symbol: str, *, side: str | None = None) -> bool:
        for order in self._state.pending_orders.values():
            if not isinstance(order, Order):
                continue
            if order.status not in _ACTIVE_PENDING_ORDER_STATUSES:
                continue
            if order.symbol != symbol:
                continue
            if side is not None and order.side != side:
                continue
            return True
        return False

    def _active_pending_orders_unlocked(self) -> list[Order]:
        return [
            order
            for order in self._state.pending_orders.values()
            if isinstance(order, Order) and order.status in _ACTIVE_PENDING_ORDER_STATUSES
        ]

    def _unresolved_orders_summary(self) -> tuple[int, str | None, list[str]]:
        with self._state_lock:
            unresolved = [
                order
                for order in self._active_pending_orders_unlocked()
                if order.unresolved_reason not in (None, "")
            ]
            reasons = [str(order.unresolved_reason) for order in unresolved if order.unresolved_reason]
            return len(unresolved), (reasons[0] if reasons else None), reasons[:3]

    def _create_order_intent(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        price: int | None,
        origin: str,
        requested_stop_loss: int | None = None,
        requested_take_profit: int | None = None,
        exit_reason: str | None = None,
        position_quantity_at_submit: int | None = None,
    ) -> Order:
        order_id = str(uuid4())
        return Order(
            order_id=order_id,
            idempotency_key=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type="market" if price is None else "limit",
            status=OrderStatus.CREATED,
            origin=origin,
            requested_stop_loss=requested_stop_loss,
            requested_take_profit=requested_take_profit,
            exit_reason=exit_reason,
            position_quantity_at_submit=position_quantity_at_submit,
            last_event_at=datetime.now(timezone.utc),
        )

    def _submit_order_intent(self, order: Order) -> OrderResult:
        if order.side == "buy":
            result = self._executor.buy(
                symbol=order.symbol,
                quantity=order.quantity,
                price=order.price,
                idempotency_key=order.idempotency_key,
            )
        else:
            result = self._executor.sell(
                symbol=order.symbol,
                quantity=order.quantity,
                price=order.price,
                idempotency_key=order.idempotency_key,
            )

        now = datetime.now(timezone.utc)
        with self._state_lock:
            persisted_order = self._state.pending_orders.get(order.order_id)
            if not isinstance(persisted_order, Order):
                persisted_order = order
                self._state.pending_orders[order.order_id] = persisted_order

            persisted_order.submission_attempts += 1
            persisted_order.last_event_at = now

            if result.success:
                persisted_order.status = OrderStatus.SUBMITTED
                persisted_order.broker_order_id = self._coerce_optional_text(result.broker_order_id)
                persisted_order.submitted_at = now
                persisted_order.unresolved_reason = None
            elif getattr(result, "submission_unknown", False) is True:
                persisted_order.status = OrderStatus.PENDING_BROKER
                persisted_order.submitted_at = persisted_order.submitted_at or now
                persisted_order.unresolved_reason = "submission_result_unknown"
                if not self._should_bypass_runtime_buy_guard():
                    self._latch_trading_guard(degraded_reason="submission_result_unknown")
                    self._notify_guardrail_once(
                        key="submission_result_unknown",
                        event_type="error.submission_result_unknown",
                        level=NotificationLevel.CRITICAL,
                        title="Order Submission Unknown",
                        error_type="OrderSubmissionUnknown",
                        error_category="broker_order",
                        operation="order_submission",
                        recoverable=False,
                        error_message="Broker submission result is unknown after transport failure.",
                        symbol=order.symbol,
                        side=order.side.upper(),
                        quantity=order.quantity,
                        price=order.price,
                        is_paper_trading=self.is_paper_trading,
                    )
            else:
                persisted_order.status = OrderStatus.REJECTED
                persisted_order.unresolved_reason = None
                self._state.pending_orders.pop(order.order_id, None)

            self._update_state_unlocked()

        self._persist_state()
        if getattr(result, "submission_unknown", False) is True:
            recovered_broker_order_id = self._recover_submission_unknown_order(order.order_id)
            if recovered_broker_order_id not in (None, ""):
                result.broker_order_id = recovered_broker_order_id
        result.order_id = order.order_id
        return result

    def _recover_submission_unknown_order(self, order_id: str) -> str | None:
        matched_broker_order_id: str | None = None
        for attempt in range(1, 4):
            try:
                snapshot = self._fetch_account_truth()
            except Exception:
                self._mark_snapshot_unavailable(reason="open_order_truth_unavailable")
                snapshot = None

            with self._state_lock:
                order = self._state.pending_orders.get(order_id)
                if not isinstance(order, Order):
                    return matched_broker_order_id

                open_order = (
                    self._find_matching_open_order(order=order, open_orders=snapshot.open_orders)
                    if snapshot is not None
                    else None
                )
                decision = evaluate_submission_recovery(
                    matched_broker_order_id=(
                        str(open_order.get("broker_order_id"))
                        if isinstance(open_order, dict)
                        and open_order.get("broker_order_id") not in (None, "")
                        else None
                    ),
                    final_attempt=attempt == 3,
                )
                if decision.bind_broker_order and decision.matched_broker_order_id is not None:
                    matched_broker_order_id = decision.matched_broker_order_id
                    order.broker_order_id = decision.matched_broker_order_id
                    order.last_reconciled_at = datetime.now(timezone.utc)
                    order.unresolved_reason = (
                        str(open_order.get("status"))
                        if isinstance(open_order, dict) and open_order.get("status") not in (None, "")
                        else "submission_result_unknown"
                    )
                    self._update_state_unlocked()
                    self._persist_state()
                    return matched_broker_order_id

                if decision.operator_action_required:
                    order.unresolved_reason = "submission_result_unknown"
                    order.last_reconciled_at = datetime.now(timezone.utc)
                    self._apply_runtime_fault(
                        fault="submission_result_unknown",
                        handoff_reason="submission_result_unknown",
                    )
                    self._update_state_unlocked()
                    self._persist_state()
                    return None

            if attempt < 3:
                time.sleep(5.0)

        return matched_broker_order_id

    def _build_execution_key(self, event: Any) -> str:
        return (
            build_execution_dedupe_key(
                broker_order_id=(
                    getattr(event, "broker_order_id", None) or getattr(event, "order_id", None)
                ),
                side=getattr(event, "side", None),
                cumulative_quantity=getattr(event, "cumulative_quantity", None),
                remaining_quantity=getattr(event, "remaining_quantity", None),
                event_status=getattr(event, "event_status", None),
                executed_quantity=(
                    getattr(event, "executed_quantity", None) or getattr(event, "quantity", None)
                ),
                executed_price=(
                    getattr(event, "executed_price", None) or getattr(event, "price", None)
                ),
            )
            or ""
        )

    def _remember_execution_key(self, key: str) -> bool:
        if not key:
            return False
        if key in self._processed_execution_key_set:
            return True
        self._processed_execution_key_set.add(key)
        self._processed_execution_keys.append(key)
        if len(self._processed_execution_keys) > 256:
            oldest = self._processed_execution_keys.pop(0)
            self._processed_execution_key_set.discard(oldest)
        return False

    def _find_matching_pending_order(
        self, event: Any
    ) -> tuple[str | None, Order | None, str | None]:
        broker_order_id = getattr(event, "broker_order_id", None) or getattr(event, "order_id", None)
        symbol = str(getattr(event, "symbol", "")).strip().upper()
        side = getattr(event, "side", None)
        expected_delta = self._event_reported_quantity(event)

        if broker_order_id:
            for order_key, order in self._state.pending_orders.items():
                if not isinstance(order, Order) or order.status not in _ACTIVE_PENDING_ORDER_STATUSES:
                    continue
                if order.broker_order_id == str(broker_order_id):
                    return order_key, order, None

        candidates: list[tuple[str, Order]] = []
        for order_key, order in self._state.pending_orders.items():
            if not isinstance(order, Order) or order.status not in _ACTIVE_PENDING_ORDER_STATUSES:
                continue
            if symbol and order.symbol != symbol:
                continue
            if side is not None and order.side != side:
                continue
            candidates.append((order_key, order))

        if not candidates:
            return None, None, "no_matching_pending_order"

        if len(candidates) == 1:
            return candidates[0][0], candidates[0][1], None

        if expected_delta is not None:
            qty_candidates = [
                (order_key, order)
                for order_key, order in candidates
                if max(order.quantity - order.filled_quantity, 0) >= expected_delta
            ]
            if len(qty_candidates) == 1:
                return qty_candidates[0][0], qty_candidates[0][1], None
            candidates = qty_candidates or candidates

        candidates.sort(
            key=lambda item: item[1].submitted_at or datetime.min.replace(tzinfo=timezone.utc)
        )
        latest_time = candidates[-1][1].submitted_at
        latest_candidates = [
            (order_key, order)
            for order_key, order in candidates
            if order.submitted_at == latest_time
        ]
        if len(latest_candidates) == 1:
            return latest_candidates[0][0], latest_candidates[0][1], None
        return None, None, "ambiguous_execution_match"

    def _event_reported_quantity(self, event: Any) -> int | None:
        reported = getattr(event, "executed_quantity", None) or getattr(event, "quantity", None)
        if reported in (None, ""):
            return None
        try:
            return max(0, int(Decimal(str(reported))))
        except Exception:
            return None

    def _resolve_fill_delta(self, order: Order, event: Any) -> int:
        cumulative = getattr(event, "cumulative_quantity", None)
        if cumulative is not None:
            target_filled = min(order.quantity, int(Decimal(str(cumulative))))
            return max(0, target_filled - order.filled_quantity)

        reported = getattr(event, "executed_quantity", None) or getattr(event, "quantity", None)
        if reported in (None, ""):
            return 0
        reported_qty = max(0, int(Decimal(str(reported))))
        return max(0, min(order.quantity - order.filled_quantity, reported_qty))

    def _apply_execution_event(self, event: Any) -> None:
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]] = []
        persisted = False
        key = self._build_execution_key(event)
        raw_payload = getattr(event, "raw_payload", None)
        integrity_failure_reason: str | None = None

        with self._state_lock:
            if key and self._remember_execution_key(key):
                logger.debug("Ignoring duplicated execution notice", extra={"key": key})
                self._log_runtime_event("execution_deduped", key=key)
                return

            order_key, order, unresolved_reason = self._find_matching_pending_order(event)
            integrity_decision = evaluate_execution_integrity(
                dedupe_key=key or None,
                matched_pending_order=order is not None and order_key is not None,
            )
            if not integrity_decision.apply_event:
                reason = integrity_decision.reason or unresolved_reason or "unmatched_execution_notice"
                integrity_failure_reason = reason
                logger.warning(
                    "Execution notice did not match a pending order",
                    extra={"key": key, "reason": reason},
                )
                self._log_runtime_event(
                    "unmatched_execution",
                    key=key,
                    reason=reason,
                    payload=raw_payload,
                )
                self._queue_notification(
                    notifications,
                    "order.unresolved",
                    NotificationLevel.CRITICAL,
                    "Order Unresolved",
                    symbol=str(getattr(event, "symbol", "")).strip().upper() or None,
                    side=getattr(event, "side", None),
                    reason=reason,
                    resolution_source="execution",
                    raw_payload=raw_payload,
                )
            else:
                assert order_key is not None
                assert order is not None
                order.unresolved_reason = None
                fill_delta = self._resolve_fill_delta(order, event)
                if fill_delta > 0:
                    fill_price = getattr(event, "executed_price", None) or getattr(event, "price", None)
                    if order.side == "buy":
                        self._apply_buy_fill(
                            order_key=order_key,
                            order=order,
                            filled_quantity=fill_delta,
                            fill_price=fill_price,
                            source="execution",
                            notifications=notifications,
                        )
                    else:
                        self._apply_sell_fill(
                            order_key=order_key,
                            order=order,
                            filled_quantity=fill_delta,
                            fill_price=fill_price,
                            source="execution",
                            position_snapshot=None,
                            notifications=notifications,
                        )
                    self._update_state_unlocked()
                    persisted = True

        if integrity_failure_reason is not None:
            self._apply_runtime_fault(
                fault=integrity_failure_reason,
                handoff_reason=integrity_failure_reason,
            )
            self._capture_account_truth(reason=integrity_failure_reason)
        elif persisted:
            self._persist_state()
        self._emit_notifications(notifications)

    def _apply_buy_fill(
        self,
        *,
        order_key: str,
        order: Order,
        filled_quantity: int,
        fill_price: Any,
        source: str,
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]],
    ) -> None:
        fill_price_decimal = self._to_decimal(fill_price) or self._to_decimal(order.price) or Decimal("0")
        now = datetime.now(timezone.utc)
        previous_quantity = order.filled_quantity
        new_total = previous_quantity + filled_quantity
        total_cost = (order.filled_avg_price or Decimal("0")) * Decimal(previous_quantity)
        total_cost += fill_price_decimal * Decimal(filled_quantity)
        order.filled_quantity = new_total
        if new_total > 0:
            order.filled_avg_price = total_cost / Decimal(new_total)
        order.last_event_at = now
        order.resolution_source = source
        order.last_reconciled_at = now if source != "execution" else order.last_reconciled_at
        order.status = OrderStatus.FILLED if order.filled_quantity >= order.quantity else OrderStatus.PARTIAL_FILL
        if order.status == OrderStatus.FILLED:
            order.filled_at = now
        order.broker_last_seen_status = "filled" if order.status == OrderStatus.FILLED else "partial_fill"

        position = self._position_manager.get_position(order.symbol)
        if position is None:
            self._position_manager.open_position(
                Position(
                    symbol=order.symbol,
                    quantity=filled_quantity,
                    entry_price=fill_price_decimal,
                    current_price=fill_price_decimal,
                    status=PositionStatus.OPEN if source == "execution" else PositionStatus.OPEN_RECONCILED,
                )
            )
            position = self._position_manager.get_position(order.symbol)
            if position is not None:
                self._queue_notification(
                    notifications,
                    "position.opened",
                    NotificationLevel.INFO,
                    "Position Opened",
                    symbol=order.symbol,
                    quantity=position.quantity,
                    entry_price=str(position.entry_price),
                    source=source,
                )
        elif position is not None:
            total_position_cost = (position.entry_price * Decimal(position.quantity)) + (
                fill_price_decimal * Decimal(filled_quantity)
            )
            position.quantity += filled_quantity
            if position.quantity > 0:
                position.entry_price = total_position_cost / Decimal(position.quantity)
            position.current_price = fill_price_decimal
            position.status = PositionStatus.OPEN if source == "execution" else PositionStatus.OPEN_RECONCILED

        if position is not None:
            self._apply_exit_targets(position, order)
            self._ensure_symbol_monitoring(order.symbol)

        if source != "execution":
            self._queue_notification(
                notifications,
                "order.reconciled",
                NotificationLevel.INFO,
                "Order Reconciled",
                symbol=order.symbol,
                side="BUY",
                quantity=filled_quantity,
                price=str(fill_price_decimal),
                broker_order_id=order.broker_order_id,
                order_id=order.order_id,
                resolution_source=source,
            )
        event_type = "order.filled" if order.status == OrderStatus.FILLED else "order.partially_filled"
        event_title = "Order Filled" if order.status == OrderStatus.FILLED else "Order Partially Filled"
        self._queue_notification(
            notifications,
            event_type,
            NotificationLevel.INFO,
            event_title,
            symbol=order.symbol,
            side="BUY",
            quantity=filled_quantity,
            price=str(fill_price_decimal),
            broker_order_id=order.broker_order_id,
            order_id=order.order_id,
            executed_quantity=str(filled_quantity),
            executed_price=str(fill_price_decimal),
        )
        if order.status == OrderStatus.FILLED:
            self._state.pending_orders.pop(order_key, None)
        self._log_runtime_event(
            "order_state_transition",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            status=order.status.value,
            resolution_source=source,
            filled_quantity=order.filled_quantity,
        )

    def _apply_sell_fill(
        self,
        *,
        order_key: str,
        order: Order,
        filled_quantity: int,
        fill_price: Any,
        source: str,
        position_snapshot: Any | None = None,
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]],
    ) -> None:
        fill_price_decimal = self._to_decimal(fill_price) or self._to_decimal(order.price) or Decimal("0")
        now = datetime.now(timezone.utc)
        previous_quantity = order.filled_quantity
        new_total = previous_quantity + filled_quantity
        total_cost = (order.filled_avg_price or Decimal("0")) * Decimal(previous_quantity)
        total_cost += fill_price_decimal * Decimal(filled_quantity)
        order.filled_quantity = new_total
        if new_total > 0:
            order.filled_avg_price = total_cost / Decimal(new_total)
        order.last_event_at = now
        order.resolution_source = source
        order.last_reconciled_at = now if source != "execution" else order.last_reconciled_at
        order.status = OrderStatus.FILLED if order.filled_quantity >= order.quantity else OrderStatus.PARTIAL_FILL
        if order.status == OrderStatus.FILLED:
            order.filled_at = now
        order.broker_last_seen_status = "filled" if order.status == OrderStatus.FILLED else "partial_fill"

        position = self._position_manager.get_position(order.symbol)
        closed_position = False
        if position is not None:
            effective_qty = min(filled_quantity, max(position.quantity, 0))
            if effective_qty > 0:
                self._record_realized_pnl(
                    position=position,
                    sold_quantity=effective_qty,
                    sold_price=int(fill_price_decimal),
                )
                if effective_qty >= position.quantity:
                    self._position_manager.close_position(order.symbol)
                    self._price_monitor.remove_symbol(order.symbol)
                    closed_position = True
                else:
                    position.quantity -= effective_qty
                    position.current_price = fill_price_decimal
                    position.unrealized_pnl = (
                        fill_price_decimal - position.entry_price
                    ) * Decimal(position.quantity)
                    self._queue_notification(
                        notifications,
                        "position.reduced",
                        NotificationLevel.INFO,
                        "Position Reduced",
                        symbol=order.symbol,
                        quantity=position.quantity,
                        entry_price=str(position.entry_price),
                        source=source,
                    )
        elif position_snapshot is not None and getattr(position_snapshot, "entry_price", None) is not None:
            self._record_realized_pnl_from_values(
                entry_price=position_snapshot.entry_price,
                sold_quantity=filled_quantity,
                sold_price=int(fill_price_decimal),
            )
            closed_position = bool(
                getattr(position_snapshot, "quantity", 0) <= filled_quantity
            )

        if source != "execution":
            self._queue_notification(
                notifications,
                "order.reconciled",
                NotificationLevel.INFO,
                "Order Reconciled",
                symbol=order.symbol,
                side="SELL",
                quantity=filled_quantity,
                price=str(fill_price_decimal),
                broker_order_id=order.broker_order_id,
                order_id=order.order_id,
                resolution_source=source,
                exit_reason=order.exit_reason,
            )
        event_type = "order.filled" if order.status == OrderStatus.FILLED else "order.partially_filled"
        event_title = "Order Filled" if order.status == OrderStatus.FILLED else "Order Partially Filled"
        self._queue_notification(
            notifications,
            event_type,
            NotificationLevel.INFO,
            event_title,
            symbol=order.symbol,
            side="SELL",
            quantity=filled_quantity,
            price=str(fill_price_decimal),
            broker_order_id=order.broker_order_id,
            order_id=order.order_id,
            executed_quantity=str(filled_quantity),
            executed_price=str(fill_price_decimal),
            exit_reason=order.exit_reason,
        )
        if closed_position:
            self._queue_notification(
                notifications,
                "position.closed",
                NotificationLevel.INFO,
                "Position Closed",
                symbol=order.symbol,
                source=source,
                exit_reason=order.exit_reason,
            )
        if order.status == OrderStatus.FILLED:
            self._state.pending_orders.pop(order_key, None)
        self._log_runtime_event(
            "order_state_transition",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            status=order.status.value,
            resolution_source=source,
            filled_quantity=order.filled_quantity,
            exit_reason=order.exit_reason,
        )

    def _apply_exit_targets(self, position: Position, order: Order) -> None:
        if order.requested_stop_loss is not None:
            position.stop_loss = Decimal(str(order.requested_stop_loss))
        elif position.stop_loss is None and position.entry_price > 0:
            position.stop_loss = self._build_default_exit_price(
                entry_price=position.entry_price,
                pct=Decimal(str(self.config.default_stop_loss_pct)),
                direction="down",
            )

        if order.requested_take_profit is not None:
            position.take_profit = Decimal(str(order.requested_take_profit))
        elif position.take_profit is None and position.entry_price > 0:
            position.take_profit = self._build_default_exit_price(
                entry_price=position.entry_price,
                pct=Decimal(str(self.config.default_take_profit_pct)),
                direction="up",
            )

    @staticmethod
    def _coerce_optional_text(value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, (str, int, float, Decimal)):
            return str(value)
        return None

    @staticmethod
    def _build_default_exit_price(
        *, entry_price: Decimal, pct: Decimal, direction: Literal["down", "up"]
    ) -> Decimal:
        multiplier = Decimal("1") - pct if direction == "down" else Decimal("1") + pct
        return Decimal(int((entry_price * multiplier).to_integral_value()))

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value in (None, "", "-"):
            return None
        try:
            return Decimal(str(value).replace(",", ""))
        except Exception:
            return None

    def _record_realized_pnl_from_values(
        self, *, entry_price: Decimal, sold_quantity: int, sold_price: int
    ) -> None:
        now = datetime.now(timezone.utc)
        self._rollover_daily_metrics_if_needed(now=now)
        effective_qty = max(int(sold_quantity), 0)
        if effective_qty <= 0:
            return
        realized = (Decimal(str(sold_price)) - entry_price) * Decimal(effective_qty)
        self._daily_realized_pnl += realized

    def _safe_inquire_daily_orders(self) -> dict[str, Any] | None:
        try:
            return self._inquire_daily_orders()
        except Exception:
            logger.debug("Daily order inquiry failed during broker sync", exc_info=True)
            return None

    def _find_daily_order_match(
        self, order: Order, daily_orders: list[dict[str, Any]]
    ) -> tuple[dict[str, Any] | None, str | None]:
        for item in daily_orders:
            if not isinstance(item, dict):
                continue
            broker_order_id = item.get("odno") or item.get("ODNO")
            if broker_order_id not in (None, "") and order.broker_order_id:
                if str(broker_order_id) == order.broker_order_id:
                    return item, None
        candidates: list[dict[str, Any]] = []
        for item in daily_orders:
            if not isinstance(item, dict):
                continue
            symbol = item.get("pdno") or item.get("PDNO")
            if str(symbol or "") != order.symbol:
                continue
            side_code = item.get("sll_buy_dvsn_cd") or item.get("SLL_BUY_DVSN_CD")
            side = "buy" if str(side_code) == "02" else "sell" if str(side_code) == "01" else None
            if side == order.side:
                candidates.append(item)
        if len(candidates) == 1:
            return candidates[0], None
        if len(candidates) > 1:
            return None, "ambiguous_daily_order_match"
        return None, "no_daily_order_match"

    def _extract_daily_filled_qty(self, item: dict[str, Any]) -> int:
        for key in (
            "tot_ccld_qty",
            "TOT_CCLD_QTY",
            "ccld_qty",
            "CCLD_QTY",
            "tot_ccld_cqty",
            "TOT_CCLD_CQTY",
        ):
            value = item.get(key)
            if value not in (None, ""):
                try:
                    return int(Decimal(str(value)))
                except Exception:
                    continue
        return 0

    def _extract_daily_fill_price(self, item: dict[str, Any]) -> Decimal | None:
        for key in ("avg_prvs", "avg_prc", "ccld_avg_prc", "ord_avg_prc", "avg_price"):
            value = item.get(key)
            if value not in (None, ""):
                return self._to_decimal(value)
        return None

    @staticmethod
    def _daily_order_looks_rejected(item: dict[str, Any]) -> bool:
        payload = " ".join(
            str(item.get(key, ""))
            for key in ("ord_stts", "ord_sttus", "ccld_dvsn", "msg1", "status")
        ).lower()
        return any(token in payload for token in ("reject", "거부", "취소", "cancel"))

    @staticmethod
    def _daily_order_status_text(item: dict[str, Any]) -> str | None:
        payload = " ".join(
            str(item.get(key, ""))
            for key in ("ord_stts", "ord_sttus", "ccld_dvsn", "status", "msg1")
        ).strip()
        return payload or None

    def _mark_order_unresolved(
        self,
        *,
        order: Order,
        reason: str,
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]],
        raw_payload: Any | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        order.unresolved_reason = reason
        order.last_reconciled_at = now
        self._log_runtime_event(
            "pending_order_unresolved",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            reason=reason,
            age_sec=self._pending_order_age_sec(order),
            payload=raw_payload,
        )
        if self._pending_order_age_sec(order) < _UNRESOLVED_ORDER_WARNING_AGE_SEC:
            return
        self._queue_notification(
            notifications,
            "order.unresolved",
            NotificationLevel.WARNING,
            "Order Unresolved",
            symbol=order.symbol,
            side=order.side.upper(),
            quantity=order.quantity,
            price=order.price,
            broker_order_id=order.broker_order_id,
            order_id=order.order_id,
            reason=reason,
            pending_age_sec=round(self._pending_order_age_sec(order), 1),
            raw_payload=raw_payload,
        )

    def _pending_order_age_sec(self, order: Order) -> float:
        base_time = order.submitted_at or order.created_at
        if base_time is None:
            return 0.0
        return max(0.0, (datetime.now(timezone.utc) - base_time).total_seconds())

    def _sync_pending_orders_from_broker(
        self,
        result: Any,
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]],
        account_truth: BrokerTruthSnapshot | None = None,
    ) -> None:
        if not self._state.pending_orders:
            return

        daily_orders_response = self._safe_inquire_daily_orders()
        daily_orders = (
            daily_orders_response.get("output1", [])
            if isinstance(daily_orders_response, dict)
            else []
        )
        if not isinstance(daily_orders, list):
            daily_orders = []
        open_orders = account_truth.open_orders if account_truth is not None else ()

        for order_key, order in list(self._state.pending_orders.items()):
            if not isinstance(order, Order):
                continue
            if order.status not in _ACTIVE_PENDING_ORDER_STATUSES:
                continue

            daily_order, daily_match_reason = self._find_daily_order_match(order, daily_orders)
            open_order = self._find_matching_open_order(order=order, open_orders=open_orders)
            order.last_reconciled_at = datetime.now(timezone.utc)
            order.broker_last_seen_status = (
                self._daily_order_status_text(daily_order) if daily_order is not None else None
            )
            if daily_order is not None and self._daily_order_looks_rejected(daily_order):
                order.status = OrderStatus.REJECTED
                order.last_event_at = datetime.now(timezone.utc)
                order.unresolved_reason = None
                self._queue_notification(
                    notifications,
                    "order.rejected",
                    NotificationLevel.WARNING,
                    "Order Rejected",
                    symbol=order.symbol,
                    side=order.side.upper(),
                    quantity=order.quantity,
                    price=order.price,
                    reason="Broker reported rejected/cancelled order",
                )
                self._state.pending_orders.pop(order_key, None)
                continue

            broker_position = result.broker_positions.get(order.symbol)
            local_snapshot = result.local_positions.get(order.symbol)

            if order.side == "buy" and daily_order is not None:
                daily_filled = self._extract_daily_filled_qty(daily_order)
                recovery_decision = evaluate_pending_order_recovery(
                    order_quantity=order.quantity,
                    filled_quantity=order.filled_quantity,
                    reconciled_filled_quantity=daily_filled,
                )
                if recovery_decision.fill_delta > 0:
                    self._apply_buy_fill(
                        order_key=order_key,
                        order=order,
                        filled_quantity=recovery_decision.fill_delta,
                        fill_price=(
                            self._extract_daily_fill_price(daily_order)
                            or (broker_position.entry_price if broker_position is not None else None)
                            or order.price
                        ),
                        source="daily_order",
                        notifications=notifications,
                    )
                if recovery_decision.status == "filled" and open_order is None:
                    order.unresolved_reason = None
                else:
                    if open_order is not None:
                        order.status = OrderStatus.PARTIAL_FILL
                    self._mark_order_unresolved(
                        order=order,
                        reason=(
                            str(open_order.get("status"))
                            if isinstance(open_order, dict) and open_order.get("status") not in (None, "")
                            else self._daily_order_status_text(daily_order) or "buy_not_filled_yet"
                        ),
                        notifications=notifications,
                        raw_payload=daily_order,
                    )
                continue

            if order.side == "buy" and broker_position is not None and broker_position.quantity > 0:
                fill_decision = infer_buy_fill_from_balance(
                    order_quantity=order.quantity,
                    filled_quantity=order.filled_quantity,
                    position_quantity_at_submit=order.position_quantity_at_submit,
                    broker_position_quantity=broker_position.quantity,
                )
                if fill_decision.filled_delta > 0:
                    self._apply_buy_fill(
                        order_key=order_key,
                        order=order,
                        filled_quantity=fill_decision.filled_delta,
                        fill_price=broker_position.entry_price or order.price,
                        source="balance",
                        notifications=notifications,
                    )
                    if order.status == OrderStatus.FILLED and open_order is None:
                        order.unresolved_reason = None
                    else:
                        if open_order is not None:
                            order.status = OrderStatus.PARTIAL_FILL
                        self._mark_order_unresolved(
                            order=order,
                            reason=(
                                str(open_order.get("status"))
                                if isinstance(open_order, dict) and open_order.get("status") not in (None, "")
                                else "buy_fill_requires_quantity_increase"
                            ),
                            notifications=notifications,
                            raw_payload=result.broker_positions.get(order.symbol),
                        )
                    continue
                self._mark_order_unresolved(
                    order=order,
                    reason=fill_decision.unresolved_reason or "buy_fill_requires_quantity_increase",
                    notifications=notifications,
                    raw_payload=result.broker_positions.get(order.symbol),
                )
                continue

            if order.side == "sell":
                original_qty = order.position_quantity_at_submit or (
                    local_snapshot.quantity if local_snapshot is not None else order.quantity
                )
                if daily_order is not None:
                    daily_filled = self._extract_daily_filled_qty(daily_order)
                    recovery_decision = evaluate_pending_order_recovery(
                        order_quantity=order.quantity,
                        filled_quantity=order.filled_quantity,
                        reconciled_filled_quantity=daily_filled,
                    )
                    if recovery_decision.fill_delta > 0:
                        self._apply_sell_fill(
                            order_key=order_key,
                            order=order,
                            filled_quantity=recovery_decision.fill_delta,
                            fill_price=(
                                self._extract_daily_fill_price(daily_order)
                                or (
                                    broker_position.current_price
                                    if broker_position is not None
                                    else order.price
                                )
                            ),
                            source="daily_order",
                            position_snapshot=local_snapshot,
                            notifications=notifications,
                        )
                    if recovery_decision.status == "filled" and open_order is None:
                        order.unresolved_reason = None
                    else:
                        if open_order is not None:
                            order.status = OrderStatus.PARTIAL_FILL
                        self._mark_order_unresolved(
                            order=order,
                            reason=(
                                str(open_order.get("status"))
                                if isinstance(open_order, dict) and open_order.get("status") not in (None, "")
                                else self._daily_order_status_text(daily_order) or "sell_not_filled_yet"
                            ),
                            notifications=notifications,
                            raw_payload=daily_order,
                        )
                    continue

                if open_order is not None:
                    order.status = (
                        OrderStatus.PARTIAL_FILL if order.filled_quantity > 0 else OrderStatus.SUBMITTED
                    )
                    self._mark_order_unresolved(
                        order=order,
                        reason=(
                            str(open_order.get("status"))
                            if open_order.get("status") not in (None, "")
                            else "open_order_active"
                        ),
                        notifications=notifications,
                        raw_payload=open_order,
                    )
                    continue

                if broker_position is None and daily_order is None:
                    self._mark_order_unresolved(
                        order=order,
                        reason="sell_requires_execution_or_daily_order_confirmation",
                        notifications=notifications,
                        raw_payload=None,
                    )
                    continue

                broker_remaining = broker_position.quantity if broker_position is not None else 0
                if broker_remaining >= original_qty:
                    self._mark_order_unresolved(
                        order=order,
                        reason=daily_match_reason or "sell_not_filled_yet",
                        notifications=notifications,
                        raw_payload=daily_order,
                    )
                    continue

                if daily_match_reason == "ambiguous_daily_order_match":
                    self._mark_order_unresolved(
                        order=order,
                        reason=daily_match_reason,
                        notifications=notifications,
                        raw_payload=daily_orders,
                    )
                    continue

            if order.unresolved_reason is None and daily_match_reason in {
                "ambiguous_daily_order_match",
                "no_daily_order_match",
            }:
                self._mark_order_unresolved(
                    order=order,
                    reason=daily_match_reason,
                    notifications=notifications,
                    raw_payload=daily_orders,
                )

    def _apply_reconciled_positions(self, broker_positions: dict[str, Any]) -> None:
        for symbol, snapshot in broker_positions.items():
            position = self._position_manager.get_position(symbol)
            if position is None:
                self._position_manager.open_position(
                    Position(
                        symbol=symbol,
                        quantity=snapshot.quantity,
                        entry_price=snapshot.entry_price or Decimal("0"),
                        current_price=snapshot.current_price,
                        status=PositionStatus.OPEN_RECONCILED,
                    )
                )
                position = self._position_manager.get_position(symbol)
            elif position is not None:
                position.quantity = snapshot.quantity
                if snapshot.entry_price is not None and (
                    position.entry_price <= 0 or position.status == PositionStatus.OPEN_RECONCILED
                ):
                    position.entry_price = snapshot.entry_price
                if snapshot.current_price is not None:
                    position.current_price = snapshot.current_price
                    position.unrealized_pnl = (
                        snapshot.current_price - position.entry_price
                    ) * Decimal(position.quantity)
                if position.status in {PositionStatus.STALE, PositionStatus.CLOSED}:
                    position.status = PositionStatus.OPEN_RECONCILED

            if position is not None and position.entry_price > 0:
                placeholder_order = Order(symbol=symbol, side="buy")
                self._apply_exit_targets(position, placeholder_order)
                self._ensure_symbol_monitoring(symbol)

    def _on_reconciliation_cycle(self, result: Any) -> None:
        notifications: list[tuple[str, NotificationLevel, str, dict[str, Any]]] = []
        should_persist = False
        account_truth: BrokerTruthSnapshot | None = None
        self._note_reconciliation_success()
        try:
            account_truth = self._fetch_account_truth()
        except Exception:
            logger.debug("Open-order broker truth refresh failed", exc_info=True)
            self._mark_snapshot_unavailable(reason="open_order_truth_unavailable")
            self._apply_runtime_fault(
                fault="open_order_truth_unavailable",
                handoff_reason="open_order_truth_unavailable",
            )
        try:
            with self._state_lock:
                self._sync_pending_orders_from_broker(
                    result,
                    notifications,
                    account_truth=account_truth,
                )
                self._apply_reconciled_positions(result.broker_positions)
                self._update_state_unlocked()
                should_persist = True
        except Exception:
            logger.debug("Reconciliation cycle apply failed", exc_info=True)
            self._apply_runtime_fault(
                fault="runtime_reconciliation_drift",
                handoff_reason="runtime_reconciliation_apply_failed",
            )
            self._capture_account_truth(reason="runtime_reconciliation_apply_failed")

        if should_persist:
            self._persist_state()
        self._emit_notifications(notifications)
        if not result.is_clean:
            self._handle_discrepancy(result)
            runtime_guard = evaluate_runtime_guard(
                is_paper_trading=self.is_paper_trading,
                allow_unsafe_trading=self.config.allow_unsafe_trading,
                has_discrepancies=True,
            )
            if runtime_guard.should_block_trading:
                self._latch_trading_guard(degraded_reason=runtime_guard.degraded_reason)
                self._notify_guardrail_once(
                    key="runtime_reconciliation_drift",
                    event_type="error.runtime_reconciliation_drift",
                    level=NotificationLevel.CRITICAL,
                    title="Runtime Reconciliation Drift",
                    error_type="RuntimeReconciliationDrift",
                    error_category="broker_state",
                    operation="runtime_reconciliation",
                    recoverable=False,
                    error_message="Broker/local state drift detected during runtime reconciliation.",
                    discrepancy_count=len(getattr(result, "discrepancies", [])),
                    is_paper_trading=self.is_paper_trading,
                )

    def _restore_risk_controls(self) -> None:
        controls = self._state.risk_controls if isinstance(self._state.risk_controls, dict) else {}

        self._daily_kill_switch_active = bool(controls.get("daily_kill_switch_active", False))
        self._daily_pnl_date = controls.get("daily_pnl_date")

        baseline = controls.get("daily_baseline_equity")
        self._daily_baseline_equity = None
        if baseline not in (None, ""):
            try:
                self._daily_baseline_equity = Decimal(str(baseline))
            except Exception:
                self._daily_baseline_equity = None

        realized = controls.get("daily_realized_pnl", "0")
        unrealized = controls.get("daily_unrealized_pnl", "0")
        try:
            self._daily_realized_pnl = Decimal(str(realized))
        except Exception:
            self._daily_realized_pnl = Decimal("0")
        try:
            self._daily_unrealized_pnl = Decimal(str(unrealized))
        except Exception:
            self._daily_unrealized_pnl = Decimal("0")

        triggered_at_raw = controls.get("daily_kill_switch_triggered_at")
        self._daily_kill_switch_triggered_at = None
        if triggered_at_raw:
            try:
                self._daily_kill_switch_triggered_at = datetime.fromisoformat(str(triggered_at_raw))
            except Exception:
                self._daily_kill_switch_triggered_at = None

    def _export_risk_controls(self) -> dict[str, Any]:
        return {
            "daily_kill_switch_active": self._daily_kill_switch_active,
            "daily_kill_switch_triggered_at": (
                self._daily_kill_switch_triggered_at.isoformat()
                if self._daily_kill_switch_triggered_at
                else None
            ),
            "daily_pnl_date": self._daily_pnl_date,
            "daily_baseline_equity": (
                str(self._daily_baseline_equity)
                if self._daily_baseline_equity is not None
                else None
            ),
            "daily_realized_pnl": str(self._daily_realized_pnl),
            "daily_unrealized_pnl": str(self._daily_unrealized_pnl),
        }

    def _rollover_daily_metrics_if_needed(self, *, now: datetime) -> None:
        current_day = now.date().isoformat()
        if self._daily_pnl_date == current_day:
            return

        previous_day = self._daily_pnl_date
        had_active_kill_switch = self._daily_kill_switch_active
        self._daily_pnl_date = current_day
        self._daily_baseline_equity = None
        self._daily_realized_pnl = Decimal("0")
        self._daily_unrealized_pnl = Decimal("0")
        self._daily_kill_switch_active = False
        self._daily_kill_switch_triggered_at = None
        if self._degraded_reason == "daily_loss_killswitch":
            self._set_operational_state(operational_state="normal", degraded_reason=None)

        if had_active_kill_switch:
            self._notify(
                "risk.killswitch.cleared",
                NotificationLevel.INFO,
                "Daily Loss Kill-Switch Cleared",
                previous_day=previous_day,
                reset_at=now.isoformat(),
            )

    def _compute_unrealized_pnl(self) -> Decimal:
        unrealized = Decimal("0")
        for position in self._position_manager.get_all_positions().values():
            current_price = position.current_price or position.entry_price
            unrealized += (current_price - position.entry_price) * Decimal(position.quantity)
        return unrealized

    def _evaluate_daily_loss_killswitch(self, *, unrealized_pnl: Decimal) -> None:
        self._daily_unrealized_pnl = unrealized_pnl
        baseline = self._daily_baseline_equity
        if baseline is None or baseline <= 0:
            return

        daily_pnl = self._daily_realized_pnl + unrealized_pnl
        daily_pnl_pct = daily_pnl / baseline
        threshold_pct = Decimal(str(self.config.daily_loss_limit_pct))

        if daily_pnl_pct > -threshold_pct or self._daily_kill_switch_active:
            return

        self._daily_kill_switch_active = True
        self._daily_kill_switch_triggered_at = datetime.now(timezone.utc)
        self._latch_trading_guard(degraded_reason="daily_loss_killswitch")
        self._notify(
            "risk.killswitch.triggered",
            NotificationLevel.CRITICAL,
            "Daily Loss Kill-Switch Triggered",
            threshold_pct=str(threshold_pct),
            baseline_equity=str(baseline),
            daily_pnl=str(daily_pnl),
            daily_pnl_pct=str(daily_pnl_pct),
            realized_pnl=str(self._daily_realized_pnl),
            unrealized_pnl=str(unrealized_pnl),
        )

    def _record_realized_pnl(
        self, *, position: Position | None, sold_quantity: int, sold_price: int
    ) -> None:
        if position is None:
            return

        now = datetime.now(timezone.utc)
        self._rollover_daily_metrics_if_needed(now=now)

        effective_qty = min(max(int(sold_quantity), 0), int(position.quantity))
        if effective_qty <= 0:
            return

        realized = (Decimal(str(sold_price)) - position.entry_price) * Decimal(effective_qty)
        self._daily_realized_pnl += realized

    def _handle_stop_loss(self, symbol: str):
        """Auto-sell position when stop-loss is triggered.

        Args:
            symbol: Stock symbol that hit stop-loss
        """
        logger.warning(f"Stop-loss triggered for {symbol}")

        position = self._position_manager.get_position(symbol)
        self._notify(
            "position.stop_loss",
            NotificationLevel.WARNING,
            "Stop-Loss Triggered",
            symbol=symbol,
            entry_price=str(position.entry_price) if position else None,
            trigger_price=str(position.current_price) if position else None,
        )
        if not position or position.quantity == 0:
            logger.warning(f"No position found for stop-loss: {symbol}")
            return
        if self._has_pending_order(symbol, side="sell"):
            logger.info("Skipping stop-loss auto-exit; pending sell exists", extra={"symbol": symbol})
            return
        if not self._should_process_auto_exit(symbol, trigger_type="stop_loss"):
            logger.info("Skipping duplicate stop-loss auto-exit", extra={"symbol": symbol})
            return

        # Get current price for market order
        try:
            current_price = self._get_current_price(symbol)
            order_decision = resolve_auto_exit_order(
                trigger_type="stop_loss",
                current_price=current_price,
            )
            result = self.sell(
                symbol=symbol,
                quantity=position.quantity,
                price=order_decision.price,
                origin="stop_loss",
                exit_reason="STOP_LOSS",
            )

            if result.success:
                logger.info(f"Stop-loss order executed for {symbol}: {result.order_id}")
            else:
                logger.error(f"Stop-loss order failed for {symbol}: {result.message}")
        except Exception as e:
            logger.error(f"Failed to execute stop-loss for {symbol}: {e}", exc_info=True)
            self._notify(
                "error.stop_loss_failed",
                NotificationLevel.ERROR,
                "손절 실행 실패",
                **self._build_error_context(e, symbol=symbol, operation="stop_loss"),
            )

    def _handle_take_profit(self, symbol: str):
        """Auto-sell position when take-profit is triggered.

        Args:
            symbol: Stock symbol that hit take-profit
        """
        logger.info(f"Take-profit triggered for {symbol}")

        position = self._position_manager.get_position(symbol)
        self._notify(
            "position.take_profit",
            NotificationLevel.INFO,
            "Take-Profit Triggered",
            symbol=symbol,
            entry_price=str(position.entry_price) if position else None,
            trigger_price=str(position.current_price) if position else None,
        )
        if not position or position.quantity == 0:
            logger.warning(f"No position found for take-profit: {symbol}")
            return
        if self._has_pending_order(symbol, side="sell"):
            logger.info(
                "Skipping take-profit auto-exit; pending sell exists",
                extra={"symbol": symbol},
            )
            return
        if not self._should_process_auto_exit(symbol, trigger_type="take_profit"):
            logger.info("Skipping duplicate take-profit auto-exit", extra={"symbol": symbol})
            return

        # Get current price for limit order
        try:
            current_price = self._get_current_price(symbol)
            order_decision = resolve_auto_exit_order(
                trigger_type="take_profit",
                current_price=current_price,
            )
            result = self.sell(
                symbol=symbol,
                quantity=position.quantity,
                price=order_decision.price,
                origin="take_profit",
                exit_reason="TAKE_PROFIT",
            )

            if result.success:
                logger.info(f"Take-profit order executed for {symbol}: {result.order_id}")
            else:
                logger.error(f"Take-profit order failed for {symbol}: {result.message}")
        except Exception as e:
            logger.error(f"Failed to execute take-profit for {symbol}: {e}", exc_info=True)
            self._notify(
                "error.take_profit_failed",
                NotificationLevel.ERROR,
                "익절 실행 실패",
                **self._build_error_context(e, symbol=symbol, operation="take_profit"),
            )

    def _handle_discrepancy(self, result):
        """Log position reconciliation discrepancies.

        Args:
            result: ReconciliationResult containing discrepancy details
        """
        logger.warning(
            "Position discrepancy detected",
            extra={
                "is_clean": result.is_clean,
                "discrepancies": len(result.discrepancies),
                "orphan_positions": len(result.orphan_positions),
                "missing_positions": len(result.missing_positions),
                "quantity_mismatches": len(result.quantity_mismatches),
            },
        )

        discrepancy_texts = [str(item) for item in result.discrepancies if item is not None]
        unresolved_count, primary_unresolved_reason, unresolved_reasons = self._unresolved_orders_summary()
        self._notify(
            "reconciliation.discrepancy",
            NotificationLevel.WARNING,
            "Reconciliation Discrepancy",
            is_clean=result.is_clean,
            discrepancy_count=len(result.discrepancies),
            orphan_positions=result.orphan_positions,
            missing_positions=result.missing_positions,
            quantity_mismatches=result.quantity_mismatches,
            primary_discrepancy=discrepancy_texts[0] if discrepancy_texts else None,
            discrepancies_sample=discrepancy_texts[:3],
            unresolved_order_count=unresolved_count,
            primary_unresolved_reason=primary_unresolved_reason,
            unresolved_reasons=unresolved_reasons,
        )

    def _run_preflight_checks(self) -> list[str]:
        """Run pre-start validation checks.

        Returns:
            List of error messages. Empty list means all checks passed.
        """
        errors: list[str] = []

        if not self.is_paper_trading and self._operator_action_required:
            errors.append("Operator action is required from previous session state")

        # 1. Broker truth inquiry → auto-set portfolio_value
        try:
            snapshot = self._fetch_account_truth()
            cash_summary = snapshot.cash if isinstance(snapshot.cash, dict) else {}
            total = (
                cash_summary.get("nass_amt")
                or cash_summary.get("dnca_tot_amt")
                or cash_summary.get("tot_evlu_amt")
                or "0"
            )
            try:
                self._risk_manager.portfolio_value = Decimal(str(total))
            except Exception:
                self._risk_manager.portfolio_value = Decimal("0")
            if self._risk_manager.portfolio_value <= 0:
                logger.warning("Portfolio value is 0 or negative")
        except Exception as e:
            self._mark_snapshot_unavailable(reason="startup_broker_truth_unavailable")
            errors.append(f"Broker truth inquiry failed: {e}")

        # 2. Slack notification connectivity test
        health_check_fn = getattr(self.notifier, "health_check", None)
        if health_check_fn is not None:
            if not health_check_fn():
                logger.warning("Slack notification health check failed")

        # 3. Market hours info (warning only, not an error)
        if self.config.market_hours_enabled and not self._is_market_open():
            if self._should_enforce_market_hours():
                logger.warning(
                    "Engine starting outside market hours - buy orders will be blocked"
                )
            else:
                logger.info(
                    "Engine starting outside market hours - mock mode: local market-hours block disabled"
                )

        return errors

    def _should_enforce_market_hours(self) -> bool:
        """Return whether engine-managed buy orders should be restricted by market hours."""
        return self.config.market_hours_enabled and (not self.is_paper_trading)

    def _is_market_open(self) -> bool:
        """Check if Korean stock market is currently open.

        Returns True only during weekday 09:00-15:20 KST.
        15:20 cutoff gives 10-minute buffer before 15:30 close.
        """
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        # Weekdays only (0=Monday, 6=Sunday)
        if now.weekday() >= 5:
            return False
        current_time = now.time()
        market_open = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = current_time.replace(hour=15, minute=20, second=0, microsecond=0)
        return market_open <= current_time <= market_close

    def _ensure_running(self):
        """Raise RuntimeError if engine is not running."""
        if not self._running:
            raise RuntimeError("Engine is not running. Call start() first.")

    def _coerce_recovery_result(self, result: Any) -> RecoveryResult:
        if isinstance(result, RecoveryResult):
            return result
        try:
            return RecoveryResult(str(result).lower())
        except ValueError:
            return RecoveryResult.FAILED

    def _start_strategy_orchestration(self) -> None:
        strategy = getattr(self.config, "strategy", None)
        symbols = list(getattr(self.config, "strategy_symbols", ()))
        auto_discover = bool(getattr(self.config, "strategy_auto_discover", False))
        if strategy is None:
            self._update_strategy_discovery_state(
                source="none",
                symbols=(),
                reason="strategy_not_configured",
                notify_discovery=False,
            )
            return
        if not symbols and not auto_discover:
            self._update_strategy_discovery_state(
                source="none",
                symbols=(),
                reason="symbols_not_configured",
                notify_discovery=False,
            )
            return

        try:
            self._run_strategy_cycle()
        except Exception:
            logger.error("Strategy cycle failed", exc_info=True)

        interval = float(getattr(self.config, "strategy_run_interval_sec", 0.0) or 0.0)
        if interval <= 0.0:
            return

        if self._strategy_thread and self._strategy_thread.is_alive():
            return

        self._strategy_stop_event.clear()
        self._strategy_thread = threading.Thread(
            target=self._strategy_loop,
            daemon=True,
            name="StrategyOrchestrator",
        )
        self._strategy_thread.start()

    def _stop_strategy_orchestration(self, *, timeout: float) -> None:
        try:
            self._strategy_stop_event.set()
            thread = self._strategy_thread
            if thread is None:
                return
            thread.join(timeout=timeout)
        except Exception:
            logger.debug("Strategy orchestration stop failed", exc_info=True)
        finally:
            self._strategy_thread = None

    def _strategy_loop(self) -> None:
        interval = float(getattr(self.config, "strategy_run_interval_sec", 0.0) or 0.0)
        if interval <= 0.0:
            return

        while not self._strategy_stop_event.is_set():
            if self._strategy_stop_event.wait(interval):
                break

            try:
                self._run_strategy_cycle()
            except Exception:
                logger.error("Strategy loop error", exc_info=True)

    def _run_strategy_cycle(self) -> None:
        strategy = getattr(self.config, "strategy", None)
        if strategy is None:
            self._update_strategy_discovery_state(
                source="none",
                symbols=(),
                reason="strategy_not_configured",
                notify_discovery=False,
            )
            return

        if self._running and not self._buying_enabled:
            return

        symbols = self._normalize_symbol_entries(getattr(self.config, "strategy_symbols", ()))
        auto_discover = bool(getattr(self.config, "strategy_auto_discover", False))
        notify_discovery = False
        discovery_source: StrategyDiscoverySource = "manual"
        discovery_reason: str | None = None

        if not symbols and auto_discover:
            discovery_result = self._discover_strategy_symbols()
            symbols = list(discovery_result.symbols)
            discovery_source = discovery_result.source
            discovery_reason = discovery_result.reason
            notify_discovery = True
        elif not symbols:
            discovery_source = "none"
            discovery_reason = "symbols_not_configured"

        max_symbols = int(getattr(self.config, "strategy_max_symbols_per_cycle", 0) or 0)
        if max_symbols > 0:
            symbols = symbols[:max_symbols]

        self._update_strategy_discovery_state(
            source=discovery_source,
            symbols=tuple(symbols),
            reason=discovery_reason,
            notify_discovery=notify_discovery,
        )

        if not symbols:
            return

        with self._strategy_lock:
            try:
                scores = strategy.screen(symbols)
            except Exception as e:
                logger.error("Strategy screen failed", exc_info=True)
                self._notify(
                    "strategy.error",
                    NotificationLevel.ERROR,
                    "전략 스크리닝 오류",
                    strategy=type(strategy).__name__,
                    symbols=symbols,
                    **self._build_error_context(e, operation="strategy_screen"),
                )
                return

            max_buys = int(getattr(self.config, "strategy_max_buys_per_cycle", 0) or 0)
            if max_buys <= 0:
                return
            qty = int(getattr(self.config, "strategy_order_quantity", 0) or 0)
            if qty <= 0:
                return

            submitted = 0
            for score in scores:
                if submitted >= max_buys:
                    break
                symbol = getattr(score, "symbol", None)
                if not isinstance(symbol, str) or not symbol.strip():
                    continue
                symbol = symbol.strip().upper()
                if not bool(getattr(score, "passes_all", True)):
                    continue

                if self._position_manager.get_position(symbol) is not None:
                    continue
                if self._has_pending_order(symbol, side="buy"):
                    continue

                try:
                    price = self._get_current_price(symbol)
                    result = self.buy(symbol, qty, price, origin="strategy")
                    if result.success:
                        submitted += 1
                except Exception as e:
                    logger.error("Buy submission failed", extra={"symbol": symbol}, exc_info=True)
                    self._notify(
                        "error.buy_submission_failed",
                        NotificationLevel.ERROR,
                        "매수 주문 제출 실패",
                        **self._build_error_context(e, symbol=symbol, operation="buy_submission"),
                    )

    def _should_process_auto_exit(self, symbol: str, *, trigger_type: str) -> bool:
        cooldown = float(getattr(self.config, "auto_exit_cooldown_sec", 1.0) or 0.0)
        if cooldown <= 0:
            return True

        key = (trigger_type, symbol)
        now = time.monotonic()
        with self._auto_exit_lock:
            last_triggered = self._auto_exit_last_trigger.get(key)
            if last_triggered is not None and (now - last_triggered) < cooldown:
                return False
            self._auto_exit_last_trigger[key] = now
            return True

    def _refresh_risk_state(
        self, *, order_price: int, order_quantity: int, for_buy: bool = False
    ) -> bool:
        self._rollover_daily_metrics_if_needed(now=datetime.now(timezone.utc))

        position_count = self._position_manager.position_count
        current_exposure = Decimal("0")
        for position in self._position_manager.get_all_positions().values():
            position_price = position.current_price or position.entry_price
            current_exposure += position_price * Decimal(position.quantity)

        unrealized_pnl = self._compute_unrealized_pnl()
        self._daily_unrealized_pnl = unrealized_pnl

        portfolio_value = Decimal("0")
        try:
            balance_response = self._inquire_balance()
            output2 = balance_response.get("output2")
            if isinstance(output2, list) and output2:
                portfolio_value = Decimal(
                    str(output2[0].get("tot_evlu_amt") or output2[0].get("dnca_tot_amt") or "0")
                )
                if portfolio_value > 0:
                    self._note_balance_refresh_success()
        except Exception:
            logger.debug("Failed to refresh risk state from broker balance", exc_info=True)
            if for_buy and not self._should_bypass_runtime_buy_guard():
                self._latch_trading_guard(degraded_reason="runtime_balance_unavailable")
                self._notify_guardrail_once(
                    key="runtime_balance_unavailable",
                    event_type="error.runtime_balance_unavailable",
                    level=NotificationLevel.CRITICAL,
                    title="Runtime Balance Unavailable",
                    error_type="RuntimeBalanceUnavailable",
                    error_category="broker_state",
                    operation="balance_refresh",
                    recoverable=False,
                    error_message="Broker balance refresh failed during buy precheck.",
                    is_paper_trading=self.is_paper_trading,
                )
                return False

        if portfolio_value <= 0:
            if for_buy and not self._should_bypass_runtime_buy_guard():
                self._latch_trading_guard(degraded_reason="runtime_balance_unavailable")
                self._notify_guardrail_once(
                    key="runtime_balance_unavailable",
                    event_type="error.runtime_balance_unavailable",
                    level=NotificationLevel.CRITICAL,
                    title="Runtime Balance Unavailable",
                    error_type="RuntimeBalanceUnavailable",
                    error_category="broker_state",
                    operation="balance_refresh",
                    recoverable=False,
                    error_message="Broker balance refresh returned no usable portfolio value.",
                    is_paper_trading=self.is_paper_trading,
                )
                return False
            order_value = Decimal(str(order_price)) * Decimal(order_quantity)
            max_position_size_pct = self._risk_manager.limits.max_position_size_pct
            if max_position_size_pct > 0:
                portfolio_value = order_value / max_position_size_pct
            else:
                portfolio_value = order_value

        if self._daily_baseline_equity is None and portfolio_value > 0:
            self._daily_baseline_equity = portfolio_value

        self._evaluate_daily_loss_killswitch(unrealized_pnl=unrealized_pnl)

        self._risk_manager.update_portfolio(
            portfolio_value=portfolio_value,
            current_exposure=current_exposure,
            position_count=position_count,
        )
        return True

    @staticmethod
    def _is_recovery_result(value: Any, expected: RecoveryResult) -> bool:
        if isinstance(value, RecoveryResult):
            return value == expected
        if isinstance(value, str):
            return value.lower() == expected.value
        return False

    def _build_error_context(self, exc: Exception, *, symbol: str | None = None, operation: str = "", **extra) -> dict:
        """Build standardized error context for notifications."""
        import traceback as tb_module
        category = self._classify_error(exc)
        frames = tb_module.format_exception(type(exc), exc, exc.__traceback__)
        tb_str = "".join(frames[-4:])  # last 3 frames + exception line
        if len(tb_str) > 1500:
            tb_str = tb_str[:1500] + "\n... (truncated)"

        ctx: dict = {
            "error_type": type(exc).__name__,
            "error_category": category,
            "error_message": str(exc),
            "traceback": tb_str,
            "operation": operation,
            "recoverable": self._is_recoverable(exc),
            "recovery_suggestion": self._get_recovery_suggestion(exc, category),
            **extra,
        }
        if symbol:
            ctx["symbol"] = symbol
            position = self._position_manager.get_position(symbol)
            if position:
                ctx["entry_price"] = str(position.entry_price)
                ctx["quantity"] = str(position.quantity)
                ctx["current_price"] = str(position.current_price) if position.current_price else None
        if self._running:
            import time as _time
            ctx["session_uptime_sec"] = _time.monotonic() - getattr(self, '_start_monotonic', _time.monotonic())
        return ctx

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        """Classify exception into Korean error category."""
        name = type(exc).__name__.lower()
        if any(k in name for k in ("connection", "timeout", "socket", "http", "network")):
            return "네트워크"
        if any(k in name for k in ("broker", "api", "kis", "auth")):
            return "브로커 API"
        if any(k in name for k in ("value", "key", "index", "attribute", "type")):
            return "로직 오류"
        return "시스템"

    @staticmethod
    def _is_recoverable(exc: Exception) -> bool:
        """Determine if the error is likely recoverable."""
        name = type(exc).__name__.lower()
        return any(k in name for k in ("connection", "timeout", "socket", "http", "network", "rate"))

    @staticmethod
    def _get_recovery_suggestion(exc: Exception, category: str) -> str:
        """Return Korean recovery suggestion based on error category."""
        suggestions = {
            "네트워크": "네트워크 연결 상태를 확인하고, 잠시 후 자동 재시도됩니다.",
            "브로커 API": "브로커 API 상태 및 인증 토큰을 확인하세요.",
            "로직 오류": "입력값과 설정을 확인하세요. 문제가 지속되면 로그를 검토하세요.",
            "시스템": "시스템 리소스(메모리/디스크)를 확인하세요.",
        }
        return suggestions.get(category, "로그를 확인하고 필요시 엔진을 재시작하세요.")

    def _notify(self, event_type: str, level: NotificationLevel, title: str, **details) -> None:
        """Send notification, swallowing any errors."""
        try:
            payload = dict(details)
            payload.setdefault("is_paper_trading", self.is_paper_trading)
            event = NotificationEvent(
                event_type=event_type,
                level=level,
                title=title,
                details=payload,
            )
            self.notifier.notify(event)
        except Exception as e:
            logger.debug(f"Notification error (suppressed): {e}")

    def _get_current_price(self, symbol: str) -> int:
        """Fetch current price from broker.

        Args:
            symbol: Stock symbol code

        Returns:
            Current price in KRW

        Raises:
            Exception: If price fetch fails
        """
        from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import (
            inquire_current_price,
        )

        # Call API directly - inquire_current_price makes the request and returns response
        response = inquire_current_price(
            client=self.client, stock_code=symbol, is_paper_trading=self.is_paper_trading
        )

        # Extract current price from response
        # Response has structure: {"output": {"stck_prpr": "70000"}}
        if "output" in response and "stck_prpr" in response["output"]:
            self._note_market_data_success()
            return int(response["output"]["stck_prpr"])

        raise ValueError(f"Failed to extract price from response: {response}")

    def _inquire_balance(self, client=None) -> dict:
        """Query broker balance for reconciliation.

        CRITICAL: Must use client.make_request() because API helper functions
        return request configs, not API responses.

        Returns:
            Balance response from broker API
        """
        from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
            get_default_inquire_balance_params,
            inquire_balance,
        )

        # inquire_balance() returns request config, NOT API response
        request_config = inquire_balance(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            is_paper_trading=self.is_paper_trading,
            **get_default_inquire_balance_params(),
        )

        # Must use client.make_request() to actually execute
        return self.client.make_request(
            method="GET",
            path=request_config["url_path"],
            params=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )
