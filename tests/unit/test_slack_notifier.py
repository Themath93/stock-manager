"""Unit tests for SlackNotifier."""

from unittest.mock import patch, MagicMock

from stock_manager.notifications.config import SlackConfig
from stock_manager.notifications.models import NotificationEvent, NotificationLevel
from stock_manager.notifications.notifier import SlackNotifier


class TestSlackNotifierInitialization:
    """Test SlackNotifier initialization."""

    def test_initialization_with_enabled_config(self):
        """Test initialization with enabled config and valid token."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient"):
            notifier = SlackNotifier(config)
            assert notifier._config == config
            assert notifier._client is not None
            assert notifier._min_level == NotificationLevel.INFO

    def test_initialization_with_disabled_config(self):
        """Test initialization with disabled config creates no client."""
        config = SlackConfig(enabled=False, _env_file=None)
        notifier = SlackNotifier(config)
        assert notifier._client is None

    def test_initialization_without_slack_sdk(self):
        """Test initialization gracefully handles missing slack_sdk."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient", side_effect=ImportError):
            notifier = SlackNotifier(config)
            assert notifier._client is None

    def test_initialization_with_webclient_exception(self):
        """Test initialization handles WebClient initialization errors."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient", side_effect=Exception("Connection failed")):
            notifier = SlackNotifier(config)
            assert notifier._client is None


class TestNotifyFiltering:
    """Test notification filtering by level."""

    def test_notify_skips_if_client_not_initialized(self):
        """Test notify returns early if client is None."""
        config = SlackConfig(enabled=False, _env_file=None)
        notifier = SlackNotifier(config)

        event = NotificationEvent(
            event_type="test.event",
            level=NotificationLevel.INFO,
            title="Test",
            details={},
        )
        # Should not raise, just return
        notifier.notify(event)

    def test_notify_filters_by_min_level(self):
        """Test notify respects min_level filtering."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            min_level="WARNING",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            # INFO event should be filtered out
            info_event = NotificationEvent(
                event_type="test.info",
                level=NotificationLevel.INFO,
                title="Info Event",
                details={},
            )
            notifier.notify(info_event)
            mock_client.chat_postMessage.assert_not_called()

            # WARNING event should be sent
            warning_event = NotificationEvent(
                event_type="test.warning",
                level=NotificationLevel.WARNING,
                title="Warning Event",
                details={},
            )
            notifier.notify(warning_event)
            mock_client.chat_postMessage.assert_called()


class TestChannelRouting:
    """Test channel routing logic."""

    def test_notify_sends_to_default_channel(self):
        """Test notify sends to default channel when no override."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="test.event",
                level=NotificationLevel.INFO,
                title="Test",
                details={},
            )
            notifier.notify(event)

            mock_client.chat_postMessage.assert_called()
            args, kwargs = mock_client.chat_postMessage.call_args
            assert kwargs["channel"] == "#trading"

    def test_notify_routes_orders_to_order_channel(self):
        """Test order events route to order_channel if set."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            order_channel="#orders",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="order.filled",
                level=NotificationLevel.INFO,
                title="Order Filled",
                details={"symbol": "005930"},
            )
            notifier.notify(event)

            args, kwargs = mock_client.chat_postMessage.call_args
            assert kwargs["channel"] == "#orders"

    def test_notify_routes_warnings_to_alert_channel(self):
        """Test warning+ events route to alert_channel if set."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            alert_channel="#alerts",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="position.stop_loss",
                level=NotificationLevel.WARNING,
                title="Stop-Loss Triggered",
                details={"symbol": "005930"},
            )
            notifier.notify(event)

            args, kwargs = mock_client.chat_postMessage.call_args
            assert kwargs["channel"] == "#alerts"

    def test_channel_routing_respects_priority(self):
        """Test channel routing priority: orders > warnings > default."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            order_channel="#orders",
            alert_channel="#alerts",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            # Order event should go to order channel, not alert channel
            event = NotificationEvent(
                event_type="order.rejected",
                level=NotificationLevel.WARNING,
                title="Order Rejected",
                details={},
            )
            notifier.notify(event)

            args, kwargs = mock_client.chat_postMessage.call_args
            assert kwargs["channel"] == "#orders"


class TestThreadSafety:
    """Test thread safety with locking."""

    def test_notify_uses_lock(self):
        """Test that notify uses threading lock for concurrent access."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            # Verify lock exists and is a threading lock
            import threading
            assert isinstance(notifier._lock, type(threading.Lock()))

            # Send notification - should use lock without raising
            event = NotificationEvent(
                event_type="test.event",
                level=NotificationLevel.INFO,
                title="Test",
                details={},
            )
            notifier.notify(event)
            mock_client.chat_postMessage.assert_called()


class TestFaultTolerance:
    """Test fault-tolerant error handling."""

    def test_notify_catches_exceptions(self):
        """Test that notify catches and logs exceptions without raising."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_postMessage.side_effect = Exception("Slack API error")
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="test.event",
                level=NotificationLevel.INFO,
                title="Test",
                details={},
            )
            # Should not raise exception
            notifier.notify(event)


class TestCriticalNotificationRetry:
    """Test CRITICAL notification retry behavior."""

    def test_critical_notification_retries_on_failure(self):
        """CRITICAL notifications should retry up to 3 times."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            # Fail twice, succeed third time
            mock_client.chat_postMessage.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                MagicMock(),  # Success
            ]
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="engine.critical_failure",
                level=NotificationLevel.CRITICAL,
                title="Critical Failure",
                details={},
            )
            with patch("time.sleep"):
                notifier.notify(event)

            assert mock_client.chat_postMessage.call_count == 3

    def test_info_notification_no_retry(self):
        """INFO notifications should NOT retry on failure."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_postMessage.side_effect = Exception("Network error")
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="test.info",
                level=NotificationLevel.INFO,
                title="Info Event",
                details={},
            )
            notifier.notify(event)

            # Only 1 attempt, no retry
            assert mock_client.chat_postMessage.call_count == 1


class TestHealthCheck:
    """Test SlackNotifier health_check method."""

    def test_health_check_returns_true_on_success(self):
        """health_check() should return True when auth_test succeeds."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.auth_test.return_value = {"ok": True}
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)
            assert notifier.health_check() is True

    def test_health_check_returns_false_on_failure(self):
        """health_check() should return False when auth_test fails."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.auth_test.side_effect = Exception("invalid_auth")
            mock_client_class.return_value = mock_client

            notifier = SlackNotifier(config)
            assert notifier.health_check() is False

    def test_health_check_returns_false_when_no_client(self):
        """health_check() should return False when client is not initialized."""
        config = SlackConfig(enabled=False, _env_file=None)
        notifier = SlackNotifier(config)
        assert notifier.health_check() is False


class TestAsyncQueueMode:
    """Test async queue mode behavior."""

    def test_async_mode_enqueues_event(self):
        """When async is enabled, notify should enqueue and worker should send."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            async_enabled=True,
            queue_maxsize=10,
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            notifier = SlackNotifier(config)

            event = NotificationEvent(
                event_type="order.filled",
                level=NotificationLevel.INFO,
                title="Order Filled",
                details={},
            )
            notifier.notify(event)

            # Wait briefly for worker thread.
            import time
            time.sleep(0.05)

            mock_client.chat_postMessage.assert_called()
            notifier.close()

    def test_queue_full_drops_low_priority(self):
        """INFO/WARNING events should be dropped when queue is full."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            async_enabled=True,
            queue_maxsize=1,
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            notifier = SlackNotifier(config)

            # Stop worker so queue stays full deterministically.
            notifier._stop_event.set()
            notifier._queue.put_nowait(
                NotificationEvent(
                    event_type="test.prefill",
                    level=NotificationLevel.INFO,
                    title="Prefill",
                    details={},
                )
            )

            event = NotificationEvent(
                event_type="test.info",
                level=NotificationLevel.INFO,
                title="Info Event",
                details={},
            )
            notifier.notify(event)

            mock_client.chat_postMessage.assert_not_called()
            notifier.close()

    def test_queue_full_fallback_for_error(self):
        """ERROR+ events should use synchronous fallback when queue is full."""
        config = SlackConfig(
            enabled=True,
            bot_token="test-bot-token",
            default_channel="#trading",
            async_enabled=True,
            queue_maxsize=1,
            _env_file=None,
        )
        with patch("slack_sdk.WebClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            notifier = SlackNotifier(config)

            # Stop worker so queue stays full deterministically.
            notifier._stop_event.set()
            notifier._queue.put_nowait(
                NotificationEvent(
                    event_type="test.prefill",
                    level=NotificationLevel.INFO,
                    title="Prefill",
                    details={},
                )
            )

            event = NotificationEvent(
                event_type="test.error",
                level=NotificationLevel.ERROR,
                title="Error Event",
                details={},
            )
            notifier.notify(event)

            mock_client.chat_postMessage.assert_called()
            notifier.close()
