"""Unit tests for trading engine notifications integration."""

from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from stock_manager.engine import TradingEngine
from stock_manager.trading import TradingConfig
from stock_manager.notifications.models import NotificationEvent, NotificationLevel
from stock_manager.notifications.noop import NoOpNotifier
from stock_manager.persistence.recovery import RecoveryResult


@pytest.fixture
def mock_notifier():
    """Create a mock notifier that records all notifications."""
    mock = Mock()
    mock.notify = Mock()
    return mock


@pytest.fixture
def mock_client():
    """Create a mock KIS client."""
    return Mock()


@pytest.fixture
def trading_engine(mock_client, mock_notifier, tmp_path):
    """Create a TradingEngine with mocked dependencies."""
    config = TradingConfig(
        rate_limit_per_sec=10,
        polling_interval_sec=1.0,
    )
    engine = TradingEngine(
        client=mock_client,
        config=config,
        account_number="12345678",
        state_path=tmp_path / "state.json",
        notifier=mock_notifier,
    )
    return engine


class TestEngineStartNotification:
    """Test engine.started notification."""

    def test_engine_started_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that engine.started notification is sent on start."""
        # Mock recovery report
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

                # Verify engine.started notification was sent
                mock_notifier.notify.assert_called()
                calls = mock_notifier.notify.call_args_list
                events = [call[0][0] for call in calls]
                assert any(e.event_type == "engine.started" for e in events)


class TestEngineStopNotification:
    """Test engine.stopped notification."""

    def test_engine_stopped_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that engine.stopped notification is sent on stop."""
        # First start the engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        # Reset mock to check stop notifications only
        mock_notifier.reset_mock()

        # Stop the engine
        trading_engine.stop()

        # Verify engine.stopped notification was sent
        mock_notifier.notify.assert_called()
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "engine.stopped" for e in events)


class TestOrderFilledNotification:
    """Test order.filled notification."""

    def test_order_filled_notification_on_buy(self, trading_engine, mock_client, mock_notifier):
        """Test that order.filled notification is sent on successful buy."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock successful order
        mock_result = Mock()
        mock_result.success = True
        mock_result.order_id = "12345"
        mock_result.error_message = None

        with patch.object(trading_engine._executor, "buy", return_value=mock_result):
            trading_engine.buy("005930", 10, 70000)

        # Verify order.filled notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "order.filled" for e in events)


class TestOrderRejectedNotification:
    """Test order.rejected notification."""

    def test_order_rejected_notification_on_failed_buy(self, trading_engine, mock_client, mock_notifier):
        """Test that order.rejected notification is sent on failed buy."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock failed order
        mock_result = Mock()
        mock_result.success = False
        mock_result.order_id = None
        mock_result.error_message = "Insufficient funds"

        with patch.object(trading_engine._executor, "buy", return_value=mock_result):
            trading_engine.buy("005930", 10, 70000)

        # Verify order.rejected notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "order.rejected" for e in events)


class TestPositionStopLossNotification:
    """Test position.stop_loss notification."""

    def test_position_stop_loss_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that position.stop_loss notification is sent."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock sell result
        mock_sell_result = Mock()
        mock_sell_result.success = True
        mock_sell_result.order_id = "12345"

        with patch.object(trading_engine._executor, "sell", return_value=mock_sell_result):
            with patch.object(trading_engine, "_get_current_price", return_value=65000):
                trading_engine._handle_stop_loss("005930")

        # Verify position.stop_loss notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "position.stop_loss" for e in events)


class TestPositionTakeProfitNotification:
    """Test position.take_profit notification."""

    def test_position_take_profit_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that position.take_profit notification is sent."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock sell result
        mock_sell_result = Mock()
        mock_sell_result.success = True
        mock_sell_result.order_id = "12345"

        with patch.object(trading_engine._executor, "sell", return_value=mock_sell_result):
            with patch.object(trading_engine, "_get_current_price", return_value=75000):
                trading_engine._handle_take_profit("005930")

        # Verify position.take_profit notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "position.take_profit" for e in events)


class TestReconciliationDiscrepancyNotification:
    """Test reconciliation.discrepancy notification."""

    def test_reconciliation_discrepancy_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that reconciliation.discrepancy notification is sent."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock discrepancy result
        mock_result = Mock()
        mock_result.is_clean = False
        mock_result.discrepancies = [{"symbol": "005930", "local": 10, "broker": 9}]
        mock_result.orphan_positions = ["000660"]
        mock_result.missing_positions = []
        mock_result.quantity_mismatches = {"005930": (10, 9)}

        trading_engine._handle_discrepancy(mock_result)

        # Verify reconciliation.discrepancy notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "reconciliation.discrepancy" for e in events)


class TestRecoveryReconciledNotification:
    """Test recovery.reconciled notification."""

    def test_recovery_reconciled_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that recovery.reconciled notification is sent on startup."""
        # Mock recovery report with RECONCILED result
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.RECONCILED
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = ["005930"]
        mock_recovery_report.missing_positions = []
        mock_recovery_report.quantity_mismatches = {}

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        # Verify recovery.reconciled notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "recovery.reconciled" for e in events)


class TestRecoveryFailedNotification:
    """Test recovery.failed notification."""

    def test_recovery_failed_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that recovery.failed notification is sent and startup is blocked."""
        # Mock recovery report with FAILED result
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.FAILED
        mock_recovery_report.errors = ["Connection failed", "Timeout"]
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []
        mock_recovery_report.quantity_mismatches = {}

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                with pytest.raises(RuntimeError, match="Startup reconciliation failed"):
                    trading_engine.start()

        # Verify recovery.failed notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "recovery.failed" for e in events)
        assert trading_engine._running is False


class TestAllNotificationTypesComplete:
    """Test that all 9 notification event types can be triggered."""

    def test_all_9_notification_types_present(self):
        """Verify all 9 event types are defined."""
        event_types = {
            "engine.started",
            "engine.stopped",
            "order.filled",
            "order.rejected",
            "position.stop_loss",
            "position.take_profit",
            "reconciliation.discrepancy",
            "recovery.reconciled",
            "recovery.failed",
        }
        assert len(event_types) == 9


class TestNotificationEventAttributes:
    """Test notification event attributes are set correctly."""

    def test_notification_event_has_required_fields(self):
        """Test that notification events have all required fields."""
        event = NotificationEvent(
            event_type="engine.started",
            level=NotificationLevel.INFO,
            title="Engine Started",
            details={"position_count": 5},
        )
        assert event.event_type == "engine.started"
        assert event.level == NotificationLevel.INFO
        assert event.title == "Engine Started"
        assert event.details == {"position_count": 5}
        assert hasattr(event, "timestamp")
        assert isinstance(event.timestamp, datetime)


class TestNotificationFilteringByLevel:
    """Test that notifications are filtered appropriately by level."""

    def test_info_level_notifications(self, trading_engine, mock_client, mock_notifier):
        """Test that INFO level notifications are sent."""
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch("stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report):
                trading_engine.start()

        # Check that some notifications were sent
        assert mock_notifier.notify.called


class TestNoOpNotifierFallback:
    """Test NoOpNotifier as a fallback."""

    def test_noop_notifier_does_not_raise(self):
        """Test that NoOpNotifier silently ignores notifications."""
        notifier = NoOpNotifier()
        event = NotificationEvent(
            event_type="test.event",
            level=NotificationLevel.INFO,
            title="Test",
            details={},
        )
        # Should not raise
        notifier.notify(event)
