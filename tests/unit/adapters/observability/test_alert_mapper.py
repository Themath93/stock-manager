"""Tests for AlertMapper."""

import pytest
from logging import CRITICAL, ERROR, WARNING, INFO

from stock_manager.adapters.observability.alert_mapper import AlertMapper
from stock_manager.adapters.observability.alert_level import AlertLevel


class TestAlertMapper:
    """Test AlertMapper class."""

    @pytest.fixture
    def mapper(self):
        """Create test AlertMapper instance."""
        return AlertMapper(
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
            batch_window=300,
        )

    def test_initialization(self, mapper):
        """Test mapper initialization."""
        assert mapper._critical_channel == "C001"
        assert mapper._error_channel == "C002"
        assert mapper._warning_channel == "C003"
        assert mapper._batch_window == 300

    def test_get_alert_mapping_critical(self, mapper):
        """Test getting mapping for CRITICAL level."""
        mapping = mapper.get_alert_mapping(CRITICAL)

        assert mapping.log_level == CRITICAL
        assert mapping.alert_level == AlertLevel.CRITICAL
        assert mapping.channel == "C001"
        assert mapping.emoji == "!"
        assert mapping.immediate is True
        assert mapping.batch_window is None

    def test_get_alert_mapping_error(self, mapper):
        """Test getting mapping for ERROR level."""
        mapping = mapper.get_alert_mapping(ERROR)

        assert mapping.log_level == ERROR
        assert mapping.alert_level == AlertLevel.ERROR
        assert mapping.channel == "C002"
        assert mapping.emoji == "x"
        assert mapping.immediate is True
        assert mapping.batch_window is None

    def test_get_alert_mapping_warning(self, mapper):
        """Test getting mapping for WARNING level."""
        mapping = mapper.get_alert_mapping(WARNING)

        assert mapping.log_level == WARNING
        assert mapping.alert_level == AlertLevel.WARNING
        assert mapping.channel == "C003"
        assert mapping.emoji == "warning"
        assert mapping.immediate is False
        assert mapping.batch_window == 300

    def test_get_alert_mapping_unknown_defaults_to_warning(self, mapper):
        """Test that unknown levels default to WARNING mapping."""
        mapping = mapper.get_alert_mapping(INFO)

        # Should return WARNING mapping (lowest alert level)
        assert mapping.alert_level == AlertLevel.WARNING
        assert mapping.channel == "C003"

    def test_should_alert_critical(self, mapper):
        """Test should_alert for CRITICAL."""
        assert mapper.should_alert(CRITICAL) is True

    def test_should_alert_error(self, mapper):
        """Test should_alert for ERROR."""
        assert mapper.should_alert(ERROR) is True

    def test_should_alert_warning(self, mapper):
        """Test should_alert for WARNING."""
        assert mapper.should_alert(WARNING) is True

    def test_should_alert_info(self, mapper):
        """Test should_alert for INFO (should not alert)."""
        assert mapper.should_alert(INFO) is False

    def test_get_alert_level(self, mapper):
        """Test get_alert_level method."""
        assert mapper.get_alert_level(ERROR) == AlertLevel.ERROR
        assert mapper.get_alert_level(WARNING) == AlertLevel.WARNING
