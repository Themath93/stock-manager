"""Tests for AlertLevel enumeration."""

import pytest
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG

from stock_manager.adapters.observability.alert_level import AlertLevel


class TestAlertLevel:
    """Test AlertLevel enum."""

    def test_alert_level_values(self):
        """Test that all expected alert levels exist."""
        assert AlertLevel.CRITICAL.value == "CRITICAL"
        assert AlertLevel.ERROR.value == "ERROR"
        assert AlertLevel.WARNING.value == "WARNING"
        assert AlertLevel.INFO.value == "INFO"
        assert AlertLevel.DEBUG.value == "DEBUG"

    def test_from_log_level_critical(self):
        """Test converting CRITICAL log level to AlertLevel."""
        result = AlertLevel.from_log_level(CRITICAL)
        assert result == AlertLevel.CRITICAL

    def test_from_log_level_error(self):
        """Test converting ERROR log level to AlertLevel."""
        result = AlertLevel.from_log_level(ERROR)
        assert result == AlertLevel.ERROR

    def test_from_log_level_warning(self):
        """Test converting WARNING log level to AlertLevel."""
        result = AlertLevel.from_log_level(WARNING)
        assert result == AlertLevel.WARNING

    def test_from_log_level_info(self):
        """Test converting INFO log level to AlertLevel."""
        result = AlertLevel.from_log_level(INFO)
        assert result == AlertLevel.INFO

    def test_from_log_level_debug(self):
        """Test converting DEBUG log level to AlertLevel."""
        result = AlertLevel.from_log_level(DEBUG)
        assert result == AlertLevel.DEBUG

    def test_from_log_level_unknown_defaults_to_info(self):
        """Test that unknown log levels default to INFO."""
        result = AlertLevel.from_log_level(0)  # NOTSET
        assert result == AlertLevel.INFO
