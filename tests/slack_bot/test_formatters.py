"""Unit tests for Block Kit formatters."""
import pytest
from stock_manager.slack_bot.formatters import (
    format_started,
    format_stopped,
    format_status,
    format_config,
    format_error,
    format_help,
    _format_uptime,
)


class TestFormatUptime:
    def test_seconds_only(self):
        assert _format_uptime(45) == "45s"

    def test_zero_seconds(self):
        assert _format_uptime(0) == "0s"

    def test_minutes_and_seconds(self):
        result = _format_uptime(90)
        assert "1m" in result
        assert "30s" in result

    def test_hours_minutes_seconds(self):
        result = _format_uptime(3723)  # 1h 2m 3s
        assert "1h" in result
        assert "2m" in result
        assert "3s" in result

    def test_exact_hour(self):
        result = _format_uptime(3600)
        assert "1h" in result
        assert "0s" in result

    def test_exact_minute(self):
        result = _format_uptime(60)
        assert "1m" in result
        assert "0s" in result

    def test_float_truncated(self):
        # Fractional seconds are truncated to int
        result = _format_uptime(61.9)
        assert "1m" in result
        assert "1s" in result


class TestFormatStarted:
    def _base_info(self):
        return {
            "strategy": "consensus",
            "symbols": "005930, 000660",
            "mode": "MOCK",
            "duration": "until stopped",
        }

    def test_returns_text_and_blocks(self):
        result = format_started(self._base_info())
        assert "text" in result
        assert "blocks" in result
        assert isinstance(result["text"], str)
        assert isinstance(result["blocks"], list)
        assert len(result["blocks"]) > 0

    def test_text_contains_started(self):
        result = format_started(self._base_info())
        assert "start" in result["text"].lower()

    def test_strategy_in_blocks(self):
        result = format_started(self._base_info())
        blocks_text = str(result["blocks"])
        assert "consensus" in blocks_text

    def test_mode_in_blocks(self):
        result = format_started(self._base_info())
        blocks_text = str(result["blocks"])
        assert "MOCK" in blocks_text

    def test_symbols_list_joined(self):
        info = {"strategy": "s", "symbols": ["005930", "000660"], "mode": "MOCK", "duration": "1h"}
        result = format_started(info)
        blocks_text = str(result["blocks"])
        assert "005930" in blocks_text

    def test_missing_keys_use_defaults(self):
        # Should not raise even with empty dict
        result = format_started({})
        assert "text" in result
        assert "blocks" in result


class TestFormatError:
    def test_returns_text_and_blocks(self):
        result = format_error("Something went wrong")
        assert "text" in result
        assert "blocks" in result

    def test_text_contains_error_prefix(self):
        result = format_error("Something went wrong")
        assert "Error:" in result["text"]
        assert "Something went wrong" in result["text"]

    def test_x_emoji_in_blocks(self):
        result = format_error("bad thing")
        blocks_text = str(result["blocks"])
        assert ":x:" in blocks_text

    def test_message_in_blocks(self):
        result = format_error("connection timeout")
        blocks_text = str(result["blocks"])
        assert "connection timeout" in blocks_text

    def test_blocks_is_list_with_one_item(self):
        result = format_error("oops")
        assert isinstance(result["blocks"], list)
        assert len(result["blocks"]) == 1


class TestFormatStatus:
    def test_no_session_stopped(self):
        result = format_status(None, {"state": "STOPPED"})
        assert "text" in result
        assert "blocks" in result
        assert isinstance(result["blocks"], list)

    def test_state_in_text(self):
        result = format_status(None, {"state": "RUNNING"})
        assert "RUNNING" in result["text"]

    def test_running_state_in_blocks(self):
        result = format_status(None, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "RUNNING" in output

    def test_with_uptime(self):
        result = format_status(None, {"state": "RUNNING", "uptime_str": "1h 30m 0s"})
        output = str(result["blocks"])
        assert "1h 30m 0s" in output

    def test_with_engine_status(self):
        from unittest.mock import MagicMock
        mock_status = MagicMock()
        mock_status.position_count = 3
        mock_status.price_monitor_running = True
        mock_status.trading_enabled = True
        mock_status.degraded_reason = None

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "3" in output
        assert "Active" in output
        assert "Enabled" in output

    def test_with_degraded_engine(self):
        from unittest.mock import MagicMock
        mock_status = MagicMock()
        mock_status.position_count = 0
        mock_status.price_monitor_running = False
        mock_status.trading_enabled = False
        mock_status.degraded_reason = "API error"

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "API error" in output

    def test_symbols_list_joined(self):
        result = format_status(None, {"state": "STOPPED", "symbols": ["005930", "000660"]})
        output = str(result["blocks"])
        assert "005930" in output

    def test_missing_keys_use_defaults(self):
        result = format_status(None, {})
        assert "text" in result
        assert "UNKNOWN" in result["text"]


class TestFormatHelp:
    def test_returns_text_and_blocks(self):
        result = format_help()
        assert "text" in result
        assert "blocks" in result

    def test_contains_commands(self):
        result = format_help()
        text = str(result)
        assert "start" in text.lower()
        assert "stop" in text.lower()
        assert "status" in text.lower()

    def test_blocks_has_header_and_section(self):
        result = format_help()
        types = [b["type"] for b in result["blocks"]]
        assert "header" in types
        assert "section" in types

    def test_text_field_is_string(self):
        result = format_help()
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0


class TestFormatStopped:
    def test_returns_text_and_blocks(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        assert "text" in result
        assert "blocks" in result

    def test_stop_in_text(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        assert "stop" in result["text"].lower()

    def test_uptime_in_blocks(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        output = str(result["blocks"])
        assert "30m 0s" in output

    def test_missing_keys_use_defaults(self):
        result = format_stopped({})
        assert "text" in result
        assert "blocks" in result


class TestFormatConfig:
    def test_returns_text_and_blocks(self):
        result = format_config({"slack_enabled": True, "default_channel": "#trading"})
        assert "text" in result
        assert "blocks" in result

    def test_config_keys_in_blocks(self):
        result = format_config({"slack_enabled": True, "default_channel": "#trading"})
        output = str(result["blocks"])
        assert "slack_enabled" in output
        assert "#trading" in output

    def test_empty_config_shows_no_config_message(self):
        result = format_config({})
        output = str(result["blocks"])
        assert "No configuration" in output or "no configuration" in output.lower()

    def test_text_field_is_string(self):
        result = format_config({"key": "value"})
        assert isinstance(result["text"], str)
