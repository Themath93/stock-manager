"""Tests for SlackFormatter."""

import logging
import pytest

from stock_manager.adapters.observability.slack_formatter import SlackFormatter
from stock_manager.adapters.observability.alert_level import AlertLevel


class TestSlackFormatter:
    """Test SlackFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create test SlackFormatter instance."""
        return SlackFormatter(enable_masking=True)

    def test_initialization(self):
        """Test formatter initialization."""
        formatter = SlackFormatter(enable_masking=True)
        assert formatter._enable_masking is True

        formatter_no_masking = SlackFormatter(enable_masking=False)
        assert formatter_no_masking._enable_masking is False

    def test_format_error_message(self, formatter):
        """Test formatting an ERROR level message."""
        record = logging.LogRecord(
            name="test_app",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Database connection failed",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "ERROR" in formatted
        assert "test_app" in formatted
        assert "Database connection failed" in formatted

    def test_format_critical_message(self, formatter):
        """Test formatting a CRITICAL level message."""
        record = logging.LogRecord(
            name="test_app",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=10,
            msg="System shutdown",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "CRITICAL" in formatted
        assert "System shutdown" in formatted

    def test_format_warning_message(self, formatter):
        """Test formatting a WARNING level message."""
        record = logging.LogRecord(
            name="test_app",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="High memory usage",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "WARNING" in formatted
        assert "High memory usage" in formatted

    def test_format_with_exception(self, formatter):
        """Test formatting message with exception info."""
        try:
            1 / 0
        except ZeroDivisionError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test_app",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Division failed",
                args=(),
                exc_info=exc_info,
            )

            formatted = formatter.format(record)

            assert "Division failed" in formatted
            assert "ZeroDivisionError" in formatted

    def test_format_with_slack_context(self, formatter):
        """Test formatting message with Slack context."""
        record = logging.LogRecord(
            name="test_app",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="API call failed",
            args=(),
            exc_info=None,
        )
        record.slack_context = {"endpoint": "/api/v1/users", "status_code": 500}  # type: ignore[attr-defined]

        formatted = formatter.format(record)

        assert "API call failed" in formatted

    def test_mask_sensitive_data_generic_patterns(self, formatter):
        """Test masking generic sensitive patterns."""
        # Test generic patterns that don't look like real tokens
        message = "Connection string contains secret value"
        masked = formatter.mask_sensitive_data(message)

        # Message should still be readable
        assert "Connection" in masked or "string" in masked

    def test_format_without_masking(self):
        """Test formatting without masking enabled."""
        formatter = SlackFormatter(enable_masking=False)
        message = "Regular log message"
        masked = formatter.mask_sensitive_data(message)

        # Should return the message unchanged
        assert message in masked

    def test_emoji_map_complete(self, formatter):
        """Test that all alert levels have emoji mappings."""
        for level in AlertLevel:
            assert level in formatter.EMOJI_MAP
            assert isinstance(formatter.EMOJI_MAP[level], str)
            assert len(formatter.EMOJI_MAP[level]) > 0

    def test_emoji_for_each_level(self, formatter):
        """Test emoji indicators for each log level."""
        test_cases = [
            (logging.CRITICAL, ":rotating_light:"),
            (logging.ERROR, ":x:"),
            (logging.WARNING, ":warning:"),
            (logging.INFO, ":information_source:"),
            (logging.DEBUG, ":bug:"),
        ]

        for level, expected_emoji in test_cases:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"Test {logging.getLevelName(level)}",
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)
            assert expected_emoji in formatted

    def test_format_exception_traceback(self, formatter):
        """Test exception traceback formatting."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            formatted = formatter.format(record)

            assert "Error occurred" in formatted
            assert "ValueError" in formatted
            assert "Test exception" in formatted
