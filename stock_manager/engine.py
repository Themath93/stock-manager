"""Trading engine facade that orchestrates all trading components.

This module provides the main TradingEngine class that coordinates:
- Order execution and position management
- Risk management and rate limiting
- Price monitoring and position reconciliation
- State persistence and recovery
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
import logging

from stock_manager.trading import (
    Position, TradingConfig,
    OrderExecutor, OrderResult, PositionManager,
    RiskManager, RateLimiter
)
from stock_manager.monitoring import PriceMonitor, PositionReconciler
from stock_manager.persistence import TradingState, save_state_atomic, load_state
from stock_manager.persistence.recovery import startup_reconciliation, RecoveryReport, RecoveryResult
from stock_manager.notifications import (
    NotifierProtocol, NoOpNotifier, NotificationEvent, NotificationLevel
)
logger = logging.getLogger(__name__)


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

    # Internal components (initialized in __post_init__)
    _executor: OrderExecutor = field(init=False)
    _position_manager: PositionManager = field(init=False)
    _risk_manager: RiskManager = field(init=False)
    _rate_limiter: RateLimiter = field(init=False)
    _price_monitor: PriceMonitor = field(init=False)
    _reconciler: PositionReconciler = field(init=False)
    _state: TradingState = field(init=False)
    _running: bool = field(default=False, init=False)

    def __post_init__(self):
        """Initialize all trading components with proper dependencies."""
        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            max_requests=self.config.rate_limit_per_sec,
            window_seconds=1.0
        )

        # Initialize position manager
        self._position_manager = PositionManager()

        # Initialize risk manager (optional limits)
        self._risk_manager = RiskManager()

        # Initialize order executor
        self._executor = OrderExecutor(
            client=self.client,
            account_number=self.account_number,
            account_product_code=self.account_product_code,
            is_paper_trading=self.is_paper_trading
        )

        # Initialize price monitor
        self._price_monitor = PriceMonitor(
            client=self.client,
            interval=self.config.polling_interval_sec,
            rate_limiter=self._rate_limiter
        )

        # Initialize position reconciler
        self._reconciler = PositionReconciler(
            position_manager=self._position_manager,
            inquire_balance_func=self._inquire_balance,
            interval=60.0,  # Check every minute
            on_discrepancy=self._handle_discrepancy
        )

        # Initialize empty state
        self._state = TradingState(
            positions={},
            last_updated=datetime.now(timezone.utc)
        )

        logger.info(
            "TradingEngine initialized",
            extra={
                "account": self.account_number,
                "paper_trading": self.is_paper_trading,
                "state_path": str(self.state_path)
            }
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
                    extra={"state_path": str(self.state_path)}
                )
        except Exception as e:
            logger.warning(f"Failed to load state: {e}. Starting with empty state.")

        # Run startup reconciliation
        recovery_report = startup_reconciliation(
            local_state=self._state,
            client=self.client,
            inquire_balance_func=self._inquire_balance,
            save_state_func=save_state_atomic,
            state_path=self.state_path
        )

        # Log recovery results
        logger.info(
            "Startup reconciliation complete",
            extra={
                "result": recovery_report.result,
                "errors": len(recovery_report.errors),
                "orphan_positions": len(recovery_report.orphan_positions),
                "missing_positions": len(recovery_report.missing_positions)
            }
        )

        # Fail-fast on reconciliation failure
        if self._is_recovery_result(recovery_report.result, RecoveryResult.FAILED):
            error_message = "; ".join(recovery_report.errors) if recovery_report.errors else "unknown error"
            self._notify(
                "recovery.failed", NotificationLevel.CRITICAL, "Recovery Failed",
                errors=recovery_report.errors,
            )
            raise RuntimeError(f"Startup reconciliation failed: {error_message}")

        # Update state after reconciliation
        self._update_state()
        self._persist_state()

        # Start background monitoring threads
        symbols = list(self._position_manager.get_all_positions().keys())
        if symbols:
            self._price_monitor.start(symbols, self._on_price_update)
        self._reconciler.start()

        self._running = True
        logger.info("TradingEngine started successfully")

        # Notify engine started
        self._notify(
            "engine.started", NotificationLevel.INFO, "Engine Started",
            position_count=len(self._position_manager.get_all_positions()),
            recovery_result=recovery_report.result,
            is_paper_trading=self.is_paper_trading,
        )

        # Notify recovery events
        if self._is_recovery_result(recovery_report.result, RecoveryResult.RECONCILED):
            self._notify(
                "recovery.reconciled", NotificationLevel.WARNING, "Recovery: Position Reconciled",
                orphan_positions=recovery_report.orphan_positions,
                missing_positions=recovery_report.missing_positions,
                quantity_mismatches=recovery_report.quantity_mismatches,
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

        # Stop monitoring threads (they handle joining internally)
        self._price_monitor.stop(timeout=timeout / 2)
        self._reconciler.stop(timeout=timeout / 2)

        # Final state save
        self._update_state()
        self._persist_state()

        self._running = False
        logger.info("TradingEngine stopped")

        # Notify engine stopped
        self._notify(
            "engine.stopped", NotificationLevel.INFO, "Engine Stopped",
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
        take_profit: Optional[int] = None
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
        self._ensure_running()

        logger.info(
            f"Buy order requested: {symbol} qty={quantity} price={price}",
            extra={
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
        )

        # Execute order through executor (includes risk checks)
        result = self._executor.buy(
            symbol=symbol,
            quantity=quantity,
            price=price
        )

        if result.success:
            # Set stop-loss and take-profit if specified
            if stop_loss:
                position = self._position_manager.get_position(symbol)
                if position:
                    position.stop_loss = Decimal(str(stop_loss))
                    # Add symbol to price monitoring for stop-loss tracking
                    self._price_monitor.add_symbol(symbol)

            if take_profit:
                position = self._position_manager.get_position(symbol)
                if position:
                    position.take_profit = Decimal(str(take_profit))
                    # Add symbol to price monitoring for take-profit tracking
                    self._price_monitor.add_symbol(symbol)

            # Persist state after successful order
            self._update_state()
            self._persist_state()

            self._notify(
                "order.filled", NotificationLevel.INFO, "Order Filled",
                symbol=symbol, side="BUY", quantity=quantity,
                price=price, broker_order_id=result.broker_order_id,
            )
        else:
            self._notify(
                "order.rejected", NotificationLevel.WARNING, "Order Rejected",
                symbol=symbol, side="BUY", quantity=quantity,
                price=price, reason=result.message,
            )

        return result

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: int
    ) -> OrderResult:
        """Place a sell order to exit a position.

        Args:
            symbol: Stock symbol code
            quantity: Number of shares to sell
            price: Limit price per share (KRW)

        Returns:
            OrderResult: Result of the order placement

        Raises:
            RuntimeError: If engine is not running
        """
        self._ensure_running()

        logger.info(
            f"Sell order requested: {symbol} qty={quantity} price={price}",
            extra={"symbol": symbol, "quantity": quantity, "price": price}
        )

        # Execute order through executor
        result = self._executor.sell(
            symbol=symbol,
            quantity=quantity,
            price=price
        )

        if result.success:
            # Remove symbol from monitoring if position fully closed
            position = self._position_manager.get_position(symbol)
            if not position or position.quantity == 0:
                self._price_monitor.remove_symbol(symbol)

            # Persist state after successful order
            self._update_state()
            self._persist_state()

            self._notify(
                "order.filled", NotificationLevel.INFO, "Order Filled",
                symbol=symbol, side="SELL", quantity=quantity,
                price=price, broker_order_id=result.broker_order_id,
            )
        else:
            self._notify(
                "order.rejected", NotificationLevel.WARNING, "Order Rejected",
                symbol=symbol, side="SELL", quantity=quantity,
                price=price, reason=result.message,
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

    def get_status(self) -> EngineStatus:
        """Get current engine status.

        Returns:
            EngineStatus: Snapshot of engine health and metrics
        """
        # Check reconciler status via thread
        reconciler_running = (
            self._reconciler._thread is not None and
            self._reconciler._thread.is_alive()
        ) if self._running else False

        return EngineStatus(
            running=self._running,
            position_count=len(self._position_manager.get_all_positions()),
            price_monitor_running=self._price_monitor.is_running,
            reconciler_running=reconciler_running,
            rate_limiter_available=self._rate_limiter.available,
            state_path=str(self.state_path),
            is_paper_trading=self.is_paper_trading
        )

    def is_healthy(self) -> bool:
        """Quick health check.

        Returns:
            True if engine is running and all components are healthy
        """
        if not self._running:
            return False

        return (
            self._price_monitor.is_running and
            self._rate_limiter.available > 0
        )

    # Internal helper methods

    def _on_price_update(self, symbol: str, price: Decimal) -> None:
        """Callback for price updates from monitor.

        Args:
            symbol: Stock symbol code
            price: Current price
        """
        self._position_manager.update_price(symbol, price)

    def _persist_state(self):
        """Save current state to disk atomically."""
        try:
            save_state_atomic(self._state, self.state_path)
            logger.debug(f"State persisted to {self.state_path}")
        except Exception as e:
            logger.error(f"Failed to persist state: {e}", exc_info=True)

    def _update_state(self):
        """Sync positions from position manager to state."""
        self._state.positions = self._position_manager.get_all_positions()
        self._state.last_updated = datetime.now(timezone.utc)

    def _handle_stop_loss(self, symbol: str):
        """Auto-sell position when stop-loss is triggered.

        Args:
            symbol: Stock symbol that hit stop-loss
        """
        logger.warning(f"Stop-loss triggered for {symbol}")

        position = self._position_manager.get_position(symbol)
        self._notify(
            "position.stop_loss", NotificationLevel.WARNING, "Stop-Loss Triggered",
            symbol=symbol,
            entry_price=str(position.entry_price) if position else None,
            trigger_price=str(position.current_price) if position else None,
        )
        if not position or position.quantity == 0:
            logger.warning(f"No position found for stop-loss: {symbol}")
            return

        # Get current price for market order
        try:
            current_price = self._get_current_price(symbol)
            result = self.sell(
                symbol=symbol,
                quantity=position.quantity,
                price=current_price
            )

            if result.success:
                logger.info(f"Stop-loss order executed for {symbol}: {result.order_id}")
            else:
                logger.error(f"Stop-loss order failed for {symbol}: {result.message}")
        except Exception as e:
            logger.error(f"Failed to execute stop-loss for {symbol}: {e}", exc_info=True)

    def _handle_take_profit(self, symbol: str):
        """Auto-sell position when take-profit is triggered.

        Args:
            symbol: Stock symbol that hit take-profit
        """
        logger.info(f"Take-profit triggered for {symbol}")

        position = self._position_manager.get_position(symbol)
        self._notify(
            "position.take_profit", NotificationLevel.INFO, "Take-Profit Triggered",
            symbol=symbol,
            entry_price=str(position.entry_price) if position else None,
            trigger_price=str(position.current_price) if position else None,
        )
        if not position or position.quantity == 0:
            logger.warning(f"No position found for take-profit: {symbol}")
            return

        # Get current price for limit order
        try:
            current_price = self._get_current_price(symbol)
            result = self.sell(
                symbol=symbol,
                quantity=position.quantity,
                price=current_price
            )

            if result.success:
                logger.info(f"Take-profit order executed for {symbol}: {result.order_id}")
            else:
                logger.error(f"Take-profit order failed for {symbol}: {result.message}")
        except Exception as e:
            logger.error(f"Failed to execute take-profit for {symbol}: {e}", exc_info=True)

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
                "quantity_mismatches": len(result.quantity_mismatches)
            }
        )

        self._notify(
            "reconciliation.discrepancy", NotificationLevel.WARNING, "Reconciliation Discrepancy",
            is_clean=result.is_clean,
            discrepancy_count=len(result.discrepancies),
            orphan_positions=result.orphan_positions,
            missing_positions=result.missing_positions,
            quantity_mismatches=result.quantity_mismatches,
        )

    def _ensure_running(self):
        """Raise RuntimeError if engine is not running."""
        if not self._running:
            raise RuntimeError("Engine is not running. Call start() first.")

    @staticmethod
    def _is_recovery_result(value: Any, expected: RecoveryResult) -> bool:
        if isinstance(value, RecoveryResult):
            return value == expected
        if isinstance(value, str):
            return value.lower() == expected.value
        return False

    def _notify(self, event_type: str, level: NotificationLevel, title: str, **details) -> None:
        """Send notification, swallowing any errors."""
        try:
            event = NotificationEvent(
                event_type=event_type,
                level=level,
                title=title,
                details=details,
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
        from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price

        # Call API directly - inquire_current_price makes the request and returns response
        response = inquire_current_price(
            client=self.client,
            stock_code=symbol,
            is_paper_trading=self.is_paper_trading
        )

        # Extract current price from response
        # Response has structure: {"output": {"stck_prpr": "70000"}}
        if "output" in response and "stck_prpr" in response["output"]:
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
            headers={"tr_id": request_config["tr_id"]}
        )
