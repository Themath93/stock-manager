from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from stock_manager.cli.trading_commands import (
    _build_runtime_context,
    _enforce_live_promotion_gate,
    _resolve_strategy_config,
    _parse_strategy_symbols,
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
        # Synchronous promotion gate check — gives immediate user feedback
        # before spawning background thread.
        use_mock_for_gate = params.is_mock
        if use_mock_for_gate is None:
            from stock_manager.adapters.broker.kis.config import KISConfig
            use_mock_for_gate = KISConfig().use_mock
        _enforce_live_promotion_gate(use_mock=use_mock_for_gate)

        with self._lock:
            if self._state in (SessionState.RUNNING, SessionState.STARTING):
                raise RuntimeError(f"Session already active (state={self._state.value})")
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
            },
            "start_time": started_at,
            "uptime_sec": uptime_sec,
        }

    def _run_engine(self, params: SessionParams) -> None:
        """Background thread that runs the engine."""
        engine: TradingEngine | None = None
        try:
            runtime = _build_runtime_context()

            # Override mock mode if specified in params
            use_mock = params.is_mock if params.is_mock is not None else runtime.config.use_mock
            _enforce_live_promotion_gate(use_mock=use_mock)

            runtime.client.authenticate()

            symbols_str = ",".join(params.symbols) if params.symbols else None
            resolved_strategy, resolved_symbols = _resolve_strategy_config(
                strategy=params.strategy,
                strategy_symbols=symbols_str,
                client=runtime.client,
            )

            notifier = SlackNotifier(SlackConfig())
            engine = TradingEngine(
                client=runtime.client,
                config=TradingConfig(
                    strategy=resolved_strategy,
                    strategy_symbols=resolved_symbols,
                    strategy_order_quantity=params.order_quantity,
                    strategy_run_interval_sec=params.run_interval_sec,
                ),
                account_number=runtime.account_number,
                account_product_code=runtime.account_product_code,
                is_paper_trading=use_mock,
                notifier=notifier,
            )

            engine.start()

            with self._lock:
                self._engine = engine
                if self._state == SessionState.STARTING:
                    self._state = SessionState.RUNNING

            logger.info("Trading session running (duration_sec=%s)", params.duration_sec)

            started_at = time.monotonic()
            while not self._stop_event.is_set():
                if params.duration_sec > 0 and (time.monotonic() - started_at) >= params.duration_sec:
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
