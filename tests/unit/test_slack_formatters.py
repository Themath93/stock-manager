"""Unit tests for Slack message formatters."""

from decimal import Decimal


from stock_manager.notifications.formatters import (
    format_notification,
    format_engine_event,
    format_order_event,
    format_position_event,
    format_reconciliation_event,
    format_recovery_event,
    _level_to_color,
    _level_to_emoji,
    _format_currency,
)
from stock_manager.notifications.models import NotificationEvent, NotificationLevel


class TestFormatNotificationDispatcher:
    """Test format_notification dispatcher function."""

    def test_dispatches_engine_events(self):
        """Test that engine events are dispatched to format_engine_event."""
        event = NotificationEvent(
            event_type="engine.started",
            level=NotificationLevel.INFO,
            title="Engine Started",
            details={"position_count": 5},
        )
        result = format_notification(event)
        assert "blocks" in result
        assert "text" in result
        assert "color" in result

    def test_dispatches_order_events(self):
        """Test that order events are dispatched to format_order_event."""
        event = NotificationEvent(
            event_type="order.filled",
            level=NotificationLevel.INFO,
            title="Order Filled",
            details={"symbol": "005930", "quantity": 10},
        )
        result = format_notification(event)
        assert "blocks" in result

    def test_unknown_event_type_uses_generic_formatter(self):
        """Test that unknown event types use generic formatter."""
        event = NotificationEvent(
            event_type="unknown.event",
            level=NotificationLevel.INFO,
            title="Unknown Event",
            details={"foo": "bar"},
        )
        result = format_notification(event)
        assert "blocks" in result
        assert event.event_type in result["text"]


class TestFormatEngineEvent:
    """Test engine event formatting."""

    def test_format_engine_started(self):
        """Test engine.started event formatting."""
        event = NotificationEvent(
            event_type="engine.started",
            level=NotificationLevel.INFO,
            title="Engine Started",
            details={
                "position_count": 5,
                "is_paper_trading": False,
                "recovery_result": "HEALTHY",
            },
        )
        result = format_engine_event(event)

        assert result["text"] == "🚀 Engine Started"
        assert result["color"] == "#36a64f"
        assert len(result["blocks"]) == 3
        assert result["blocks"][0]["type"] == "header"
        assert "Running" in str(result["blocks"][1])

    def test_format_engine_stopped(self):
        """Test engine.stopped event formatting."""
        event = NotificationEvent(
            event_type="engine.stopped",
            level=NotificationLevel.INFO,
            title="Engine Stopping",
            details={"position_count": 3},
        )
        result = format_engine_event(event)

        assert "🛑" in result["text"]
        assert "Stopped" in str(result["blocks"][1])

    def test_mock_mode_adds_mock_prefix_to_engine_event(self):
        """Test engine event adds [MOCK] prefix when is_paper_trading is true."""
        event = NotificationEvent(
            event_type="engine.started",
            level=NotificationLevel.INFO,
            title="Engine Started",
            details={
                "position_count": 1,
                "is_paper_trading": True,
                "recovery_result": "CLEAN",
            },
        )
        result = format_engine_event(event)

        assert result["text"].startswith("[MOCK] ")
        assert result["blocks"][0]["text"]["text"].startswith("[MOCK] ")


class TestFormatOrderEvent:
    """Test order event formatting."""

    def test_format_order_filled(self):
        """Test order.filled event formatting."""
        event = NotificationEvent(
            event_type="order.filled",
            level=NotificationLevel.INFO,
            title="Order Filled",
            details={
                "symbol": "005930",
                "quantity": 100,
                "price": 70000,
                "order_id": "12345",
                "side": "BUY",
            },
        )
        result = format_order_event(event)

        assert result["text"] == "✅ Order Filled: 🟢 BUY 100x 삼성전자(005930)"
        assert result["color"] == "#36a64f"
        assert len(result["blocks"]) == 3

    def test_format_order_rejected(self):
        """Test order.rejected event formatting."""
        event = NotificationEvent(
            event_type="order.rejected",
            level=NotificationLevel.WARNING,
            title="Order Rejected",
            details={
                "symbol": "005930",
                "quantity": 50,
                "side": "SELL",
                "reason": "Insufficient funds",
            },
        )
        result = format_order_event(event)

        assert "❌" in result["text"]
        assert result["color"] == "#ECB22E"

    def test_format_order_with_explicit_symbol_name(self):
        """Test order formatter prefers explicit symbol_name from details."""
        event = NotificationEvent(
            event_type="order.filled",
            level=NotificationLevel.INFO,
            title="Order Filled",
            details={
                "symbol": "123456",
                "symbol_name": "테스트종목",
                "quantity": 1,
                "price": 1000,
                "side": "SELL",
            },
        )
        result = format_order_event(event)

        assert "테스트종목(123456)" in result["text"]
        assert "🔴" in result["text"]

    def test_mock_mode_adds_mock_prefix_to_order_event(self):
        """Test order event adds [MOCK] prefix when is_paper_trading is true."""
        event = NotificationEvent(
            event_type="order.filled",
            level=NotificationLevel.INFO,
            title="Order Filled",
            details={
                "symbol": "005930",
                "quantity": 1,
                "price": 70000,
                "side": "BUY",
                "is_paper_trading": True,
            },
        )
        result = format_order_event(event)

        assert result["text"].startswith("[MOCK] ")
        assert result["blocks"][0]["text"]["text"].startswith("[MOCK] ")


class TestFormatPositionEvent:
    """Test position event formatting."""

    def test_format_position_stop_loss(self):
        """Test position.stop_loss event formatting."""
        event = NotificationEvent(
            event_type="position.stop_loss",
            level=NotificationLevel.WARNING,
            title="Stop-Loss Triggered",
            details={"symbol": "005930"},
        )
        result = format_position_event(event)

        assert "🛡️" in result["text"]
        assert "삼성전자(005930)" in result["text"]
        assert result["color"] == "#ECB22E"

    def test_format_position_take_profit(self):
        """Test position.take_profit event formatting."""
        event = NotificationEvent(
            event_type="position.take_profit",
            level=NotificationLevel.INFO,
            title="Take-Profit Triggered",
            details={"symbol": "000660"},
        )
        result = format_position_event(event)

        assert "💰" in result["text"]
        assert "SK하이닉스(000660)" in result["text"]

    def test_position_event_with_pnl_calculation(self):
        """Test position event with P&L calculation."""
        event = NotificationEvent(
            event_type="position.stop_loss",
            level=NotificationLevel.WARNING,
            title="Stop-Loss Triggered",
            details={
                "symbol": "005930",
                "entry_price": 70000,
                "trigger_price": 75000,
            },
        )
        result = format_position_event(event)

        # P&L should be calculated and included
        pnl_text = str(result["blocks"][1])
        assert "P&L" in pnl_text or "KRW" in pnl_text

    def test_position_event_pnl_with_invalid_values(self):
        """Test position event with invalid P&L calculation doesn't crash."""
        event = NotificationEvent(
            event_type="position.stop_loss",
            level=NotificationLevel.WARNING,
            title="Stop-Loss Triggered",
            details={
                "symbol": "005930",
                "entry_price": "invalid",
                "trigger_price": 75000,
            },
        )
        # Should not raise exception
        result = format_position_event(event)
        assert "blocks" in result


class TestFormatReconciliationEvent:
    """Test reconciliation event formatting."""

    def test_format_reconciliation_discrepancy(self):
        """Test reconciliation.discrepancy event formatting."""
        event = NotificationEvent(
            event_type="reconciliation.discrepancy",
            level=NotificationLevel.WARNING,
            title="Reconciliation Discrepancy",
            details={
                "orphan_positions": ["005930", "000660"],
                "missing_positions": ["011200"],
                "quantity_mismatches": {"005930": (100, 90)},
                "discrepancy_count": 3,
            },
        )
        result = format_reconciliation_event(event)

        assert "Reconciliation Discrepancy" in result["blocks"][0]["text"]["text"]
        assert result["color"] == "#ECB22E"
        assert "3 discrepancies found" in result["text"]


class TestFormatRecoveryEvent:
    """Test recovery event formatting."""

    def test_format_recovery_reconciled(self):
        """Test recovery.reconciled event formatting."""
        event = NotificationEvent(
            event_type="recovery.reconciled",
            level=NotificationLevel.WARNING,
            title="Recovery: Position Reconciled",
            details={
                "orphan_positions": ["005930"],
                "missing_positions": [],
                "quantity_mismatches": {},
            },
        )
        result = format_recovery_event(event)

        assert "RECONCILED" in str(result["blocks"][1])
        assert result["color"] == "#ECB22E"

    def test_format_recovery_failed(self):
        """Test recovery.failed event formatting."""
        event = NotificationEvent(
            event_type="recovery.failed",
            level=NotificationLevel.CRITICAL,
            title="Recovery Failed",
            details={"errors": ["Connection failed", "Timeout"]},
        )
        result = format_recovery_event(event)

        assert "FAILED" in str(result["blocks"][1])
        assert result["color"] == "#E01E5A"


class TestLevelToColor:
    """Test notification level to color mapping."""

    def test_info_color(self):
        """Test INFO level color."""
        assert _level_to_color(NotificationLevel.INFO) == "#36a64f"

    def test_warning_color(self):
        """Test WARNING level color."""
        assert _level_to_color(NotificationLevel.WARNING) == "#ECB22E"

    def test_error_color(self):
        """Test ERROR level color."""
        assert _level_to_color(NotificationLevel.ERROR) == "#E01E5A"

    def test_critical_color(self):
        """Test CRITICAL level color."""
        assert _level_to_color(NotificationLevel.CRITICAL) == "#E01E5A"


class TestLevelToEmoji:
    """Test notification level to emoji mapping."""

    def test_info_emoji(self):
        """Test INFO level emoji."""
        assert _level_to_emoji(NotificationLevel.INFO) == ":white_check_mark:"

    def test_warning_emoji(self):
        """Test WARNING level emoji."""
        assert _level_to_emoji(NotificationLevel.WARNING) == ":warning:"

    def test_error_emoji(self):
        """Test ERROR level emoji."""
        assert _level_to_emoji(NotificationLevel.ERROR) == ":x:"

    def test_critical_emoji(self):
        """Test CRITICAL level emoji."""
        assert _level_to_emoji(NotificationLevel.CRITICAL) == ":rotating_light:"


class TestFormatCurrency:
    """Test currency formatting."""

    def test_format_integer(self):
        """Test formatting integer as currency."""
        assert _format_currency(70000) == "70,000 KRW"

    def test_format_float(self):
        """Test formatting float as currency."""
        assert _format_currency(70000.5) == "70,000 KRW"

    def test_format_decimal(self):
        """Test formatting Decimal as currency."""
        assert _format_currency(Decimal("70000")) == "70,000 KRW"

    def test_format_none(self):
        """Test formatting None value."""
        assert _format_currency(None) == "N/A"

    def test_format_invalid_value(self):
        """Test formatting invalid value."""
        result = _format_currency("invalid")
        assert result == "invalid"
