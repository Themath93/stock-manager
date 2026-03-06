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
        assert "실행 중" in str(result["blocks"][1])

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
        assert "중지" in str(result["blocks"][1])

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
        assert "3건 불일치 발견" in result["text"]


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

        assert "조정 완료" in str(result["blocks"][1])
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

        assert "실패" in str(result["blocks"][1])
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


class TestFormatErrorDetail:
    """Test format_error_detail for enriched error notifications."""

    def _make_error_event(self, **overrides):
        details = {
            "error_type": "ConnectionError",
            "error_category": "네트워크",
            "error_message": "Connection refused",
            "traceback": "Traceback (most recent call last):\n  File \"engine.py\", line 1050\nConnectionError: refused",
            "operation": "stop_loss",
            "recoverable": True,
            "recovery_suggestion": "네트워크 연결 상태를 확인하고, 잠시 후 자동 재시도됩니다.",
            "symbol": "005930",
            "entry_price": "70000",
            "quantity": "10",
            "session_uptime_sec": 3661,
            "is_paper_trading": False,
        }
        details.update(overrides)
        return NotificationEvent(
            event_type="error.stop_loss_failed",
            level=NotificationLevel.ERROR,
            title="손절 실행 실패",
            details=details,
        )

    def test_full_fields_render(self):
        """All fields present produces header, fields, error msg, traceback, recovery, context."""
        from stock_manager.notifications.formatters import format_error_detail
        event = self._make_error_event()
        result = format_error_detail(event)

        assert "text" in result
        assert "blocks" in result
        assert "color" in result
        blocks = result["blocks"]
        assert blocks[0]["type"] == "header"
        assert "손절 실행 실패" in blocks[0]["text"]["text"]
        # Fields section
        fields_text = str(blocks[1])
        assert "종목" in fields_text
        assert "오류 유형" in fields_text
        assert "ConnectionError" in fields_text
        assert "네트워크" in fields_text
        assert "재시도 가능" in fields_text
        assert "예" in fields_text

    def test_minimal_fields(self):
        """Minimal event (no symbol, no traceback) still renders."""
        from stock_manager.notifications.formatters import format_error_detail
        event = NotificationEvent(
            event_type="error.state_persistence_failed",
            level=NotificationLevel.WARNING,
            title="상태 저장 실패",
            details={
                "error_type": "OSError",
                "error_category": "시스템",
                "error_message": "Disk full",
                "operation": "state_persistence",
                "recoverable": False,
                "is_paper_trading": False,
            },
        )
        result = format_error_detail(event)
        assert len(result["blocks"]) >= 2
        fields_text = str(result["blocks"][1])
        assert "아니오" in fields_text  # recoverable=False

    def test_traceback_in_blocks(self):
        """Traceback appears in a code block."""
        from stock_manager.notifications.formatters import format_error_detail
        event = self._make_error_event()
        result = format_error_detail(event)
        all_text = str(result["blocks"])
        assert "Traceback" in all_text

    def test_recovery_suggestion_in_blocks(self):
        """Recovery suggestion appears in context block."""
        from stock_manager.notifications.formatters import format_error_detail
        event = self._make_error_event()
        result = format_error_detail(event)
        all_text = str(result["blocks"])
        assert "조치 방안" in all_text
        assert "네트워크 연결 상태" in all_text

    def test_session_uptime_in_context(self):
        """Session uptime is rendered in the final context block."""
        from stock_manager.notifications.formatters import format_error_detail
        event = self._make_error_event(session_uptime_sec=3661)
        result = format_error_detail(event)
        all_text = str(result["blocks"])
        assert "세션 가동" in all_text
        assert "1h" in all_text

    def test_dispatcher_routes_error_events(self):
        """format_notification routes error.* events to format_error_detail."""
        event = self._make_error_event()
        result = format_notification(event)
        assert "blocks" in result
        # Should have header with Korean title
        assert "손절 실행 실패" in str(result["blocks"][0])

    def test_no_symbol_omits_symbol_field(self):
        """When no symbol in details, symbol field is omitted."""
        from stock_manager.notifications.formatters import format_error_detail
        event = NotificationEvent(
            event_type="error.state_persistence_failed",
            level=NotificationLevel.WARNING,
            title="상태 저장 실패",
            details={
                "error_type": "IOError",
                "error_category": "시스템",
                "error_message": "Write failed",
                "recoverable": False,
                "is_paper_trading": False,
            },
        )
        result = format_error_detail(event)
        fields = result["blocks"][1].get("fields", [])
        field_labels = [f["text"].split("\n")[0] for f in fields]
        assert "*종목:*" not in field_labels
