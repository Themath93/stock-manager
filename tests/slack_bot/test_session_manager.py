"""Unit tests for SessionManager."""
import time
import pytest
from unittest.mock import MagicMock, patch

from stock_manager.slack_bot.session_manager import (
    SessionManager,
    SessionParams,
    SessionState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_BUILD_RUNTIME = "stock_manager.slack_bot.session_manager._build_runtime_context"
_PATCH_PROMOTION_GATE = "stock_manager.slack_bot.session_manager._enforce_live_promotion_gate"
_PATCH_RESOLVE_STRATEGY = "stock_manager.slack_bot.session_manager._resolve_strategy_config"
_PATCH_TRADING_ENGINE = "stock_manager.slack_bot.session_manager.TradingEngine"
_PATCH_SLACK_NOTIFIER = "stock_manager.slack_bot.session_manager.SlackNotifier"


def _make_mock_runtime(use_mock: bool = True) -> MagicMock:
    runtime = MagicMock()
    runtime.config.use_mock = use_mock
    runtime.account_number = "12345678"
    runtime.account_product_code = "01"
    return runtime


def _wait_for_state(manager: SessionManager, state: SessionState, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while manager.state != state and time.monotonic() < deadline:
        time.sleep(0.05)
    return manager.state == state


# ---------------------------------------------------------------------------
# Init / default state
# ---------------------------------------------------------------------------

class TestSessionManagerInit:
    def test_initial_state_is_stopped(self):
        manager = SessionManager()
        assert manager.state == SessionState.STOPPED

    def test_is_running_false_initially(self):
        manager = SessionManager()
        assert manager.is_running is False

    def test_get_session_info_when_stopped(self):
        manager = SessionManager()
        info = manager.get_session_info()
        assert info["state"] == "STOPPED"
        assert info["uptime_sec"] is None

    def test_get_status_returns_none_when_stopped(self):
        manager = SessionManager()
        assert manager.get_status() is None

    def test_session_info_params_all_none_when_stopped(self):
        manager = SessionManager()
        info = manager.get_session_info()
        params = info["params"]
        assert params["strategy"] is None
        assert params["symbols"] == []

    def test_start_time_is_none_when_stopped(self):
        manager = SessionManager()
        info = manager.get_session_info()
        assert info["start_time"] is None


# ---------------------------------------------------------------------------
# Double-start rejection
# ---------------------------------------------------------------------------

class TestSessionManagerDoubleStart:
    def test_start_while_starting_raises(self):
        manager = SessionManager()
        manager._state = SessionState.STARTING

        with pytest.raises(RuntimeError, match="already active"):
            manager.start_session(SessionParams())

    def test_start_while_running_raises(self):
        manager = SessionManager()
        manager._state = SessionState.RUNNING

        with pytest.raises(RuntimeError, match="already active"):
            manager.start_session(SessionParams())

    def test_error_state_can_be_restarted(self):
        """After ERROR the manager should accept a new start_session call."""
        manager = SessionManager()
        manager._state = SessionState.ERROR

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            # Should not raise
            manager.start_session(SessionParams(is_mock=True))
            # State transitions to STARTING
            assert manager.state in (SessionState.STARTING, SessionState.RUNNING)

            # Clean up background thread
            manager.stop_session()
            if manager._thread:
                manager._thread.join(timeout=3.0)


# ---------------------------------------------------------------------------
# Stop behaviour
# ---------------------------------------------------------------------------

class TestSessionManagerStop:
    def test_stop_when_stopped_is_noop(self):
        manager = SessionManager()
        manager.stop_session()
        assert manager.state == SessionState.STOPPED

    def test_stop_when_error_is_noop(self):
        manager = SessionManager()
        manager._state = SessionState.ERROR
        manager.stop_session()
        # Should remain ERROR (not transitioning to STOPPING)
        assert manager.state == SessionState.ERROR

    def test_stop_sets_stop_event_when_running(self):
        manager = SessionManager()
        manager._state = SessionState.RUNNING
        manager.stop_session()
        assert manager._stop_event.is_set()
        assert manager.state == SessionState.STOPPING

    def test_stop_sets_stop_event_when_starting(self):
        manager = SessionManager()
        manager._state = SessionState.STARTING
        manager.stop_session()
        assert manager._stop_event.is_set()
        assert manager.state == SessionState.STOPPING


# ---------------------------------------------------------------------------
# get_session_info
# ---------------------------------------------------------------------------

class TestGetSessionInfo:
    def test_uptime_increases_over_time(self):
        manager = SessionManager()
        manager._state = SessionState.RUNNING
        manager._started_at = time.monotonic() - 5.0
        manager._params = SessionParams(strategy="test")

        info = manager.get_session_info()
        assert info["uptime_sec"] >= 5.0

    def test_params_reflected_in_info(self):
        manager = SessionManager()
        params = SessionParams(
            strategy="consensus",
            symbols=("005930", "000660"),
            duration_sec=3600,
            is_mock=True,
            order_quantity=2,
            run_interval_sec=30.0,
        )
        manager._params = params
        manager._started_at = time.monotonic()

        info = manager.get_session_info()["params"]
        assert info["strategy"] == "consensus"
        assert info["symbols"] == ["005930", "000660"]
        assert info["duration_sec"] == 3600
        assert info["is_mock"] is True
        assert info["order_quantity"] == 2
        assert info["run_interval_sec"] == 30.0


# ---------------------------------------------------------------------------
# Integration-style tests with mocked engine
# ---------------------------------------------------------------------------

class TestSessionManagerWithMockEngine:
    def test_start_session_transitions_to_running(self):
        manager = SessionManager()
        params = SessionParams(is_mock=True)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True
        mock_engine.get_status.return_value = MagicMock()

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            assert _wait_for_state(manager, SessionState.RUNNING), (
                f"Expected RUNNING, got {manager.state}"
            )
            assert manager.is_running is True

            manager.stop_session()
            if manager._thread:
                manager._thread.join(timeout=3.0)

    def test_engine_crash_sets_error_state(self):
        crash_events: list[Exception] = []

        def on_crash(exc: Exception) -> None:
            crash_events.append(exc)

        manager = SessionManager(on_crash=on_crash)
        params = SessionParams(is_mock=True)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.start.side_effect = RuntimeError("Engine start failed")

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            assert _wait_for_state(manager, SessionState.ERROR), (
                f"Expected ERROR, got {manager.state}"
            )

        assert len(crash_events) == 1
        assert "Engine start failed" in str(crash_events[0])

    def test_stop_session_transitions_to_stopped(self):
        manager = SessionManager()
        params = SessionParams(is_mock=True)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            _wait_for_state(manager, SessionState.RUNNING)

            manager.stop_session()
            if manager._thread:
                manager._thread.join(timeout=3.0)

            assert manager.state == SessionState.STOPPED
            assert manager.is_running is False

    def test_duration_elapsed_stops_session(self):
        """A very short duration should auto-stop the engine."""
        manager = SessionManager()
        params = SessionParams(is_mock=True, duration_sec=1)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            # Wait up to 5 seconds for auto-stop after 1s duration
            _wait_for_state(manager, SessionState.RUNNING)
            if manager._thread:
                manager._thread.join(timeout=5.0)

            assert manager.state == SessionState.STOPPED

    def test_unhealthy_engine_stops_session(self):
        """If engine.is_healthy() returns False the session should stop."""
        manager = SessionManager()
        params = SessionParams(is_mock=True)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        # Immediately report unhealthy after first check
        mock_engine.is_healthy.return_value = False

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            if manager._thread:
                manager._thread.join(timeout=5.0)

            assert manager.state == SessionState.STOPPED

    def test_on_crash_not_called_on_clean_stop(self):
        crash_events: list[Exception] = []

        def on_crash(exc: Exception) -> None:
            crash_events.append(exc)

        manager = SessionManager(on_crash=on_crash)
        params = SessionParams(is_mock=True)

        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            _wait_for_state(manager, SessionState.RUNNING)
            manager.stop_session()
            if manager._thread:
                manager._thread.join(timeout=3.0)

        assert crash_events == []

    def test_get_status_returns_engine_status_when_running(self):
        manager = SessionManager()
        params = SessionParams(is_mock=True)

        expected_status = MagicMock()
        mock_runtime = _make_mock_runtime()
        mock_engine = MagicMock()
        mock_engine.is_healthy.return_value = True
        mock_engine.get_status.return_value = expected_status

        with patch(_PATCH_BUILD_RUNTIME, return_value=mock_runtime), \
             patch(_PATCH_PROMOTION_GATE), \
             patch(_PATCH_RESOLVE_STRATEGY, return_value=(None, ())), \
             patch(_PATCH_TRADING_ENGINE, return_value=mock_engine), \
             patch(_PATCH_SLACK_NOTIFIER):

            manager.start_session(params)
            _wait_for_state(manager, SessionState.RUNNING)

            status = manager.get_status()
            assert status is expected_status

            manager.stop_session()
            if manager._thread:
                manager._thread.join(timeout=3.0)
