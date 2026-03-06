from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from stock_manager.cli.trading_commands import (
    _build_runtime_context,
    _enforce_live_promotion_gate,
    _resolve_strategy_config,
)
from stock_manager.trading import TradingConfig
from stock_manager.notifications import SlackNotifier, SlackConfig
from stock_manager.engine import TradingEngine

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass
class SessionParams:
    strategy: str | None = None
    symbols: tuple[str, ...] = ()
    duration_sec: int = 0  # 0 = run until stopped
    is_mock: bool | None = None  # None = use KIS_USE_MOCK env
    order_quantity: int = 1
    run_interval_sec: float = 60.0
    strategy_auto_discover: bool = False
    strategy_discovery_limit: int = 20
    strategy_discovery_fallback_symbols: tuple[str, ...] = ()
    llm_mode: str = "off"


class SessionManager:
    """Manages TradingEngine lifecycle for Slack-triggered sessions.

    State machine:
        STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED
                                       -> ERROR (on crash)
        ERROR -> STOPPED (manual reset on next start)
    """

    def __init__(
        self,
        *,
        on_crash: Callable[[Exception], None] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._state = SessionState.STOPPED
        self._stop_event = threading.Event()
        self._started_at: float | None = None
        self._params: SessionParams | None = None
        self._engine: TradingEngine | None = None
        self._thread: threading.Thread | None = None
        self._on_crash = on_crash

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state == SessionState.RUNNING

    def start_session(self, params: SessionParams) -> None:
        """Start a new trading session.

        Raises:
            RuntimeError: If session already running or starting
            ValueError: If promotion gate blocks live trading
        """
        with self._lock:
            if self._state in (SessionState.RUNNING, SessionState.STARTING):
                raise RuntimeError(f"Session already active (state={self._state.value})")

        # Synchronous promotion gate check — gives immediate user feedback
        # before spawning background thread.
        use_mock_for_gate = params.is_mock
        if use_mock_for_gate is None:
            from stock_manager.adapters.broker.kis.config import KISConfig

            use_mock_for_gate = KISConfig().use_mock
        _enforce_live_promotion_gate(use_mock=use_mock_for_gate)

        with self._lock:
            # Reset ERROR state to allow restart
            self._state = SessionState.STARTING
            self._params = params
            self._stop_event.clear()
            self._started_at = time.monotonic()

        thread = threading.Thread(
            target=self._run_engine,
            args=(params,),
            name="SessionManagerEngine",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def stop_session(self) -> None:
        """Stop the current trading session gracefully."""
        with self._lock:
            if self._state not in (SessionState.RUNNING, SessionState.STARTING):
                return
            self._state = SessionState.STOPPING

        self._stop_event.set()

    def get_status(self) -> Any | None:
        """Get EngineStatus or None if not running."""
        with self._lock:
            engine = self._engine
            if self._state != SessionState.RUNNING or engine is None:
                return None
        return engine.get_status()

    def get_session_info(self) -> dict:
        """Get session info dict with state, params, start_time, uptime_sec."""
        with self._lock:
            state = self._state
            params = self._params
            started_at = self._started_at

        uptime_sec: float | None = None
        if started_at is not None:
            uptime_sec = time.monotonic() - started_at

        return {
            "state": state.value,
            "params": {
                "strategy": params.strategy if params else None,
                "symbols": list(params.symbols) if params else [],
                "duration_sec": params.duration_sec if params else 0,
                "is_mock": params.is_mock if params else None,
                "order_quantity": params.order_quantity if params else 1,
                "run_interval_sec": params.run_interval_sec if params else 60.0,
                "strategy_auto_discover": (
                    params.strategy_auto_discover if params else False
                ),
                "strategy_discovery_limit": (
                    params.strategy_discovery_limit if params else 20
                ),
                "strategy_discovery_fallback_symbols": (
                    list(params.strategy_discovery_fallback_symbols) if params else []
                ),
                "llm_mode": params.llm_mode if params else "off",
            },
            "start_time": started_at,
            "uptime_sec": uptime_sec,
        }

    @staticmethod
    def _build_dalio_hybrid_persona(base_persona: Any):
        """Build Dalio hybrid persona with env-driven LLM runtime settings."""
        from stock_manager.trading.llm.circuit_breaker import CircuitBreaker
        from stock_manager.trading.llm.config import InvocationCounter, LLMConfig
        from stock_manager.trading.personas.dalio_hybrid_persona import DalioHybridPersona

        llm_config = LLMConfig.from_env()
        circuit_breaker = CircuitBreaker(
            failure_threshold=llm_config.cb_failure_threshold,
            cooldown_sec=llm_config.cb_cooldown_sec,
            sliding_window_sec=llm_config.cb_sliding_window_sec,
        )
        return DalioHybridPersona(
            base_persona=base_persona,
            circuit_breaker=circuit_breaker,
            llm_config=llm_config,
            invocation_counter=InvocationCounter(),
        )

    @staticmethod
    def _apply_selective_llm_overlay(strategy: Any) -> Any:
        """Enable hybrid LLM only for Dalio persona in consensus strategy."""
        from stock_manager.trading.strategies.consensus import ConsensusStrategy

        if not isinstance(strategy, ConsensusStrategy):
            raise ValueError("--llm-mode selective requires --strategy consensus.")

        personas = strategy.evaluator.personas
        dalio_indexes = [
            idx for idx, persona in enumerate(personas) if getattr(persona, "name", "") == "Dalio"
        ]
        if len(dalio_indexes) != 1:
            raise RuntimeError(
                "Selective LLM overlay requires exactly one Dalio persona "
                f"(found {len(dalio_indexes)})."
            )

        dalio_idx = dalio_indexes[0]
        personas[dalio_idx] = SessionManager._build_dalio_hybrid_persona(personas[dalio_idx])
        logger.info(
            "Applied strategy overlay: llm_mode=selective, dalio_hybrid_enabled=true"
        )
        return strategy

    def get_balance(self) -> dict | None:
        """Get account balance, or None if not running."""
        with self._lock:
            engine = self._engine
            if self._state != SessionState.RUNNING or engine is None:
                return None
        return engine.get_balance()

    def get_daily_orders(self) -> dict | None:
        """Get today's order history, or None if not running."""
        with self._lock:
            engine = self._engine
            if self._state != SessionState.RUNNING or engine is None:
                return None
        return engine.get_daily_orders()

    def get_positions(self) -> dict | None:
        """Get all positions, or None if not running."""
        with self._lock:
            engine = self._engine
            if self._state != SessionState.RUNNING or engine is None:
                return None
        return {
            sym: {
                "symbol": sym,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "status": pos.status.value,
            }
            for sym, pos in engine.get_positions().items()
        }

    def liquidate_all(self) -> list[dict] | None:
        """Liquidate all positions, or None if not running."""
        with self._lock:
            engine = self._engine
            if self._state != SessionState.RUNNING or engine is None:
                return None
        return engine.liquidate_all()

    def _run_engine(self, params: SessionParams) -> None:
        """Background thread that runs the engine."""
        engine: TradingEngine | None = None
        try:
            runtime = _build_runtime_context(use_mock_override=params.is_mock)
            effective_use_mock = runtime.config.use_mock
            _enforce_live_promotion_gate(use_mock=effective_use_mock)

            runtime.client.authenticate()

            symbols_str = ",".join(params.symbols) if params.symbols else None
            resolved_strategy, resolved_symbols = _resolve_strategy_config(
                strategy=params.strategy,
                strategy_symbols=symbols_str,
                client=runtime.client,
            )
            if params.llm_mode == "selective":
                resolved_strategy = self._apply_selective_llm_overlay(resolved_strategy)

            notifier = SlackNotifier(SlackConfig())
            engine = TradingEngine(
                client=runtime.client,
                config=TradingConfig(
                    strategy=resolved_strategy,
                    strategy_symbols=resolved_symbols,
                    strategy_order_quantity=params.order_quantity,
                    strategy_run_interval_sec=params.run_interval_sec,
                    strategy_auto_discover=params.strategy_auto_discover,
                    strategy_discovery_limit=params.strategy_discovery_limit,
                    strategy_discovery_fallback_symbols=(
                        params.strategy_discovery_fallback_symbols
                    ),
                ),
                account_number=runtime.account_number,
                account_product_code=runtime.account_product_code,
                is_paper_trading=effective_use_mock,
                notifier=notifier,
            )

            engine_mode = getattr(engine, "is_paper_trading", None)
            if isinstance(engine_mode, bool) and engine_mode != runtime.config.use_mock:
                raise RuntimeError(
                    "Session mode mismatch: engine and KIS client are using different trading modes."
                )

            engine.start()

            with self._lock:
                self._engine = engine
                if self._state == SessionState.STARTING:
                    self._state = SessionState.RUNNING

            logger.info("Trading session running (duration_sec=%s)", params.duration_sec)

            started_at = time.monotonic()
            while not self._stop_event.is_set():
                if (
                    params.duration_sec > 0
                    and (time.monotonic() - started_at) >= params.duration_sec
                ):
                    logger.info("Session duration elapsed, stopping.")
                    break
                if not engine.is_healthy():
                    logger.warning("Engine reports unhealthy, stopping session.")
                    break
                self._stop_event.wait(timeout=0.5)

        except Exception as exc:
            logger.exception("Session engine crashed: %s", exc)
            with self._lock:
                self._state = SessionState.ERROR
                self._engine = None
            if self._on_crash is not None:
                try:
                    self._on_crash(exc)
                except Exception:
                    logger.exception("on_crash callback raised")
            return

        # Graceful shutdown
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                logger.exception("Error stopping engine")

        try:
            notifier.close()  # type: ignore[possibly-undefined]
        except Exception:
            logger.exception("Error closing notifier")

        with self._lock:
            self._engine = None
            self._state = SessionState.STOPPED

        logger.info("Trading session stopped.")
