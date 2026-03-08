"""Unit tests for trading engine notifications integration."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
import pytest

from stock_manager.engine import TradingEngine
from stock_manager.trading import TradingConfig, OrderResult
from stock_manager.notifications.models import NotificationEvent, NotificationLevel
from stock_manager.notifications.noop import NoOpNotifier
from stock_manager.persistence.recovery import RecoveryResult


class _NoopStrategy:
    def screen(self, symbols: list[str]) -> list[object]:
        return []


@pytest.fixture
def mock_notifier():
    """Create a mock notifier that records all notifications."""
    mock = Mock()
    mock.notify = Mock()
    return mock


@pytest.fixture
def mock_client():
    """Create a mock KIS client."""
    client = Mock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg_cd": "0",
        "output": {"stck_prpr": "70000"},
        "output2": [{"dnca_tot_amt": "10000000"}],
    }
    return client


@pytest.fixture
def trading_engine(mock_client, mock_notifier, tmp_path):
    """Create a TradingEngine with mocked dependencies."""
    config = TradingConfig(
        rate_limit_per_sec=10,
        polling_interval_sec=1.0,
        market_hours_enabled=False,
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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

                # Verify engine.started notification was sent
                mock_notifier.notify.assert_called()
                calls = mock_notifier.notify.call_args_list
                events = [call[0][0] for call in calls]
                assert any(e.event_type == "engine.started" for e in events)
                started_event = next(e for e in events if e.event_type == "engine.started")
                assert started_event.details.get("is_paper_trading") is False


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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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


class TestOrderSubmissionNotification:
    """Test order submission notification semantics."""

    def test_order_submitted_notification_on_buy(self, trading_engine, mock_client, mock_notifier):
        """Test that successful buy submission emits order.submitted until broker fill arrives."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        mock_notifier.reset_mock()

        # Mock successful order
        with patch.object(
            trading_engine._executor,
            "buy",
            return_value=OrderResult(success=True, order_id="12345"),
        ):
            trading_engine.buy("005930", 10, 70000)

        # Verify order.submitted notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "order.submitted" for e in events)
        submitted_event = next(e for e in events if e.event_type == "order.submitted")
        assert submitted_event.details.get("is_paper_trading") is False

    def test_order_filled_notification_on_execution(self, trading_engine, mock_client, mock_notifier):
        """Test that broker-confirmed execution emits order.filled."""
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        mock_notifier.reset_mock()

        with patch.object(
            trading_engine._executor,
            "buy",
            return_value=OrderResult(success=True, order_id="12345"),
        ):
            trading_engine.buy("005930", 10, 70000)

        event = Mock(
            symbol="005930",
            order_id="12345",
            broker_order_id=None,
            side="buy",
            executed_price=Decimal("70000"),
            executed_quantity=Decimal("10"),
            cumulative_quantity=None,
            quantity=Decimal("10"),
            price=Decimal("70000"),
            event_status="filled",
            timestamp="2026-03-08T00:00:00+00:00",
        )
        trading_engine._apply_execution_event(event)

        events = [call[0][0] for call in mock_notifier.notify.call_args_list]
        assert any(e.event_type == "order.filled" for e in events)


class TestOrderRejectedNotification:
    """Test order.rejected notification."""

    def test_order_rejected_notification_on_failed_buy(
        self, trading_engine, mock_client, mock_notifier
    ):
        """Test that order.rejected notification is sent on failed buy."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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

    def test_reconciliation_discrepancy_notification(
        self, trading_engine, mock_client, mock_notifier
    ):
        """Test that reconciliation.discrepancy notification is sent."""
        # Setup engine
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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
        discrepancy_event = next(e for e in events if e.event_type == "reconciliation.discrepancy")
        assert discrepancy_event.details["discrepancy_count"] == 1
        assert discrepancy_event.details["primary_discrepancy"] is not None
        assert "005930" in discrepancy_event.details["primary_discrepancy"]
        assert discrepancy_event.details["discrepancies_sample"]


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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        # Verify recovery.reconciled notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "recovery.reconciled" for e in events)


class TestRecoveryFailedNotification:
    """Test recovery.failed notification."""

    def test_recovery_failed_notification(self, trading_engine, mock_client, mock_notifier):
        """Test that recovery.failed notification is sent and trading is blocked."""
        # Mock recovery report with FAILED result
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.FAILED
        mock_recovery_report.errors = ["Connection failed", "Timeout"]
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []
        mock_recovery_report.quantity_mismatches = {}

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        # Verify recovery.failed notification was sent
        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "recovery.failed" for e in events)
        assert trading_engine._running is True
        assert trading_engine._trading_enabled is False

    def test_engine_started_includes_degraded_fields_on_recovery_failure(
        self, trading_engine, mock_client, mock_notifier
    ):
        """engine.started should include degraded trading flags."""
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.FAILED
        mock_recovery_report.errors = ["Connection failed"]
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls if call[0][0].event_type == "engine.started"]
        assert len(events) == 1
        started = events[0]
        assert started.details.get("trading_enabled") is False
        assert started.details.get("degraded_reason") == "startup_recovery_failed"


class TestKillSwitchNotifications:
    def test_killswitch_triggered_notification(self, trading_engine, mock_client, mock_notifier):
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        mock_notifier.reset_mock()
        trading_engine._daily_pnl_date = datetime.now().date().isoformat()
        trading_engine._daily_baseline_equity = Decimal("1000000")
        trading_engine._daily_realized_pnl = Decimal("-6000")

        trading_engine._evaluate_daily_loss_killswitch(unrealized_pnl=Decimal("-5000"))

        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "risk.killswitch.triggered" for e in events)
        event = next(e for e in events if e.event_type == "risk.killswitch.triggered")
        assert event.level == NotificationLevel.CRITICAL

    def test_killswitch_cleared_notification_on_rollover(
        self, trading_engine, mock_client, mock_notifier
    ):
        mock_recovery_report = Mock()
        mock_recovery_report.result = RecoveryResult.CLEAN
        mock_recovery_report.errors = []
        mock_recovery_report.orphan_positions = []
        mock_recovery_report.missing_positions = []

        with patch("stock_manager.engine.load_state", return_value=None):
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
                trading_engine.start()

        trading_engine._daily_kill_switch_active = True
        trading_engine._daily_pnl_date = "2000-01-01"
        trading_engine._degraded_reason = "daily_loss_killswitch"
        mock_notifier.reset_mock()

        trading_engine._rollover_daily_metrics_if_needed(now=datetime.now())

        calls = mock_notifier.notify.call_args_list
        events = [call[0][0] for call in calls]
        assert any(e.event_type == "risk.killswitch.cleared" for e in events)
        event = next(e for e in events if e.event_type == "risk.killswitch.cleared")
        assert event.level == NotificationLevel.INFO


class TestStrategyDiscoveryNotifications:
    def test_screening_complete_emitted_once_for_unchanged_discovery(
        self, trading_engine, mock_notifier
    ):
        trading_engine.is_paper_trading = True
        trading_engine.config = TradingConfig(
            strategy=_NoopStrategy(),
            strategy_symbols=(),
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930", "000660"),
            strategy_max_buys_per_cycle=0,
            strategy_run_interval_sec=0.0,
            market_hours_enabled=False,
        )

        mock_notifier.reset_mock()
        trading_engine._run_strategy_cycle()
        trading_engine._run_strategy_cycle()

        events = [call[0][0] for call in mock_notifier.notify.call_args_list]
        screening_events = [e for e in events if e.event_type == "pipeline.screening_complete"]
        assert len(screening_events) == 1
        assert screening_events[0].details.get("discovery_source") == "mock_fallback"
        assert screening_events[0].details.get("symbols") == ["005930", "000660"]

    def test_screening_complete_reemits_when_discovery_source_changes(
        self, trading_engine, mock_notifier
    ):
        trading_engine.is_paper_trading = True
        trading_engine.config = TradingConfig(
            strategy=_NoopStrategy(),
            strategy_symbols=(),
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930", "000660"),
            strategy_max_buys_per_cycle=0,
            strategy_run_interval_sec=0.0,
            market_hours_enabled=False,
        )

        mock_notifier.reset_mock()
        trading_engine._run_strategy_cycle()

        trading_engine.is_paper_trading = False
        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.ranking.get_volume_rank",
            return_value={
                "rt_cd": "0",
                "output": [
                    {"stck_shrn_iscd": "005930"},
                    {"mksc_shrn_iscd": "000660"},
                ],
            },
        ):
            trading_engine._run_strategy_cycle()

        events = [call[0][0] for call in mock_notifier.notify.call_args_list]
        screening_events = [e for e in events if e.event_type == "pipeline.screening_complete"]
        assert len(screening_events) == 2
        assert screening_events[0].details.get("discovery_source") == "mock_fallback"
        assert screening_events[1].details.get("discovery_source") == "volume_rank"


class TestAllNotificationTypesComplete:
    def test_all_13_notification_types_present(self):
        event_types = {
            "engine.started",
            "engine.stopped",
            "order.filled",
            "order.execution_notice",
            "order.rejected",
            "position.stop_loss",
            "position.take_profit",
            "reconciliation.discrepancy",
            "recovery.reconciled",
            "recovery.failed",
            "risk.killswitch.triggered",
            "risk.killswitch.cleared",
            "pipeline.screening_complete",
        }
        assert len(event_types) == 13


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
            with patch(
                "stock_manager.engine.startup_reconciliation", return_value=mock_recovery_report
            ):
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
