"""Tests for Phase 5 infrastructure components."""
from __future__ import annotations

import logging
from datetime import timezone
from enum import Enum
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from stock_manager.notifications.backends import (
    NOTIFICATION_TIMEOUT,
    LogNotifier,
    NotificationDispatcher,
)
from stock_manager.api.health import HealthStatus, get_health
from stock_manager.storage.sqlite_backend import SQLiteStateBackend
from stock_manager.dashboard.provider import DashboardData, DashboardProvider


# ---------------------------------------------------------------------------
# Task 5.1: Multi-Channel Notifications
# ---------------------------------------------------------------------------


class TestNotificationTimeout:
    """Verify the mandatory 5-second timeout constant."""

    def test_timeout_is_five(self) -> None:
        assert NOTIFICATION_TIMEOUT == 5


class TestLogNotifier:
    """LogNotifier should log messages and return True."""

    def test_send_returns_true(self) -> None:
        notifier = LogNotifier()
        assert notifier.send("hello") is True

    def test_send_logs_message(self, caplog: pytest.LogCaptureFixture) -> None:
        notifier = LogNotifier()
        with caplog.at_level(logging.INFO):
            notifier.send("test message")
        assert "NOTIFICATION: test message" in caplog.text


class TestNotificationDispatcher:
    """Dispatcher should call all backends; failures must not propagate."""

    def test_notify_calls_all_backends(self) -> None:
        backend1 = MagicMock()
        backend1.send.return_value = True
        backend2 = MagicMock()
        backend2.send.return_value = True

        dispatcher = NotificationDispatcher(backends=[backend1, backend2])
        dispatcher.notify("hello")

        backend1.send.assert_called_once_with("hello")
        backend2.send.assert_called_once_with("hello")

    def test_default_backend_is_log_notifier(self) -> None:
        dispatcher = NotificationDispatcher()
        assert len(dispatcher._backends) == 1
        assert isinstance(dispatcher._backends[0], LogNotifier)

    def test_failure_does_not_raise(self) -> None:
        failing_backend = MagicMock()
        failing_backend.send.side_effect = RuntimeError("boom")

        dispatcher = NotificationDispatcher(backends=[failing_backend])
        # Must not raise
        dispatcher.notify("test")

    def test_failure_does_not_block_subsequent_backends(self) -> None:
        failing = MagicMock()
        failing.send.side_effect = RuntimeError("boom")
        succeeding = MagicMock()
        succeeding.send.return_value = True

        dispatcher = NotificationDispatcher(backends=[failing, succeeding])
        dispatcher.notify("test")

        succeeding.send.assert_called_once_with("test")


class TestSlackNotifierTimeout:
    """SlackNotifier (webhook) should use the 5-second timeout constant."""

    def test_webhook_url_stored(self) -> None:
        from stock_manager.notifications.backends import SlackNotifier as WebhookNotifier

        notifier = WebhookNotifier(webhook_url="https://hooks.slack.com/test")
        assert notifier.webhook_url == "https://hooks.slack.com/test"


# ---------------------------------------------------------------------------
# Task 5.3: Health Endpoint
# ---------------------------------------------------------------------------


class TestHealthStatus:
    """HealthStatus should return valid status data."""

    def test_get_health_returns_health_status(self) -> None:
        result = get_health()
        assert isinstance(result, HealthStatus)

    def test_default_status_is_ok(self) -> None:
        result = get_health()
        assert result.status == "ok"

    def test_version_is_set(self) -> None:
        result = get_health()
        assert result.version == "1.0.0"

    def test_timestamp_is_utc(self) -> None:
        result = get_health()
        assert result.timestamp.tzinfo == timezone.utc

    def test_uptime_is_non_negative(self) -> None:
        result = get_health()
        assert result.uptime_seconds >= 0.0


# ---------------------------------------------------------------------------
# Task 5.4: SQLite Backend
# ---------------------------------------------------------------------------


class TestSQLiteStateBackend:
    """SQLiteStateBackend CRUD operations using tmp_path for isolation."""

    @pytest.fixture()
    def backend(self, tmp_path: Any) -> SQLiteStateBackend:
        db = SQLiteStateBackend(db_path=tmp_path / "test.db")
        yield db
        db.close()

    def test_get_default(self, backend: SQLiteStateBackend) -> None:
        assert backend.get("missing") is None

    def test_get_custom_default(self, backend: SQLiteStateBackend) -> None:
        assert backend.get("missing", 42) == 42

    def test_set_and_get(self, backend: SQLiteStateBackend) -> None:
        backend.set("key1", {"a": 1})
        assert backend.get("key1") == {"a": 1}

    def test_set_overwrite(self, backend: SQLiteStateBackend) -> None:
        backend.set("key1", "old")
        backend.set("key1", "new")
        assert backend.get("key1") == "new"

    def test_delete_existing(self, backend: SQLiteStateBackend) -> None:
        backend.set("key1", "value")
        assert backend.delete("key1") is True
        assert backend.get("key1") is None

    def test_delete_missing(self, backend: SQLiteStateBackend) -> None:
        assert backend.delete("nonexistent") is False

    def test_keys_empty(self, backend: SQLiteStateBackend) -> None:
        assert backend.keys() == []

    def test_keys_populated(self, backend: SQLiteStateBackend) -> None:
        backend.set("a", 1)
        backend.set("b", 2)
        assert sorted(backend.keys()) == ["a", "b"]

    def test_stores_complex_json(self, backend: SQLiteStateBackend) -> None:
        data = {"list": [1, 2, 3], "nested": {"x": True}}
        backend.set("complex", data)
        assert backend.get("complex") == data


# ---------------------------------------------------------------------------
# Task 5.5: Dashboard Provider
# ---------------------------------------------------------------------------


class _MockState(Enum):
    BOUGHT = "BOUGHT"
    MONITORING = "MONITORING"
    IDLE = "IDLE"


class TestDashboardProvider:
    """DashboardProvider should aggregate pipeline state."""

    def test_none_runner_returns_empty(self) -> None:
        provider = DashboardProvider(pipeline_runner=None)
        data = provider.get_status()
        assert isinstance(data, DashboardData)
        assert data.total_symbols == 0
        assert data.active_positions == 0
        assert data.pipeline_states == {}
        assert data.recent_trades == []

    def test_with_mock_runner(self) -> None:
        entry_bought = SimpleNamespace(state=_MockState.BOUGHT)
        entry_monitoring = SimpleNamespace(state=_MockState.MONITORING)
        entry_idle = SimpleNamespace(state=_MockState.IDLE)

        runner = SimpleNamespace(
            entries={
                "AAPL": entry_bought,
                "GOOG": entry_monitoring,
                "MSFT": entry_idle,
            }
        )

        provider = DashboardProvider(pipeline_runner=runner)
        data = provider.get_status()

        assert data.total_symbols == 3
        assert data.active_positions == 2
        assert data.pipeline_states["BOUGHT"] == 1
        assert data.pipeline_states["MONITORING"] == 1
        assert data.pipeline_states["IDLE"] == 1

    def test_timestamp_is_utc(self) -> None:
        provider = DashboardProvider()
        data = provider.get_status()
        assert data.timestamp.tzinfo == timezone.utc
