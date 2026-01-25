"""Tests for AlertMapping dataclass."""

import pytest

from stock_manager.adapters.observability.alert_level import AlertLevel
from stock_manager.adapters.observability.alert_mapping import AlertMapping


class TestAlertMapping:
    """Test AlertMapping dataclass."""

    def test_create_alert_mapping(self):
        """Test creating AlertMapping with all fields."""
        mapping = AlertMapping(
            log_level=40,  # ERROR
            alert_level=AlertLevel.ERROR,
            channel="C12345",
            emoji="x",
            immediate=True,
            batch_window=None,
        )

        assert mapping.log_level == 40
        assert mapping.alert_level == AlertLevel.ERROR
        assert mapping.channel == "C12345"
        assert mapping.emoji == "x"
        assert mapping.immediate is True
        assert mapping.batch_window is None

    def test_critical_factory(self):
        """Test critical() factory method."""
        mapping = AlertMapping.critical("C001")

        assert mapping.log_level == 50  # CRITICAL
        assert mapping.alert_level == AlertLevel.CRITICAL
        assert mapping.channel == "C001"
        assert mapping.emoji == "!"
        assert mapping.immediate is True
        assert mapping.batch_window is None

    def test_error_factory(self):
        """Test error() factory method."""
        mapping = AlertMapping.error("C002")

        assert mapping.log_level == 40  # ERROR
        assert mapping.alert_level == AlertLevel.ERROR
        assert mapping.channel == "C002"
        assert mapping.emoji == "x"
        assert mapping.immediate is True
        assert mapping.batch_window is None

    def test_warning_factory_default_batch(self):
        """Test warning() factory method with default batch window."""
        mapping = AlertMapping.warning("C003")

        assert mapping.log_level == 30  # WARNING
        assert mapping.alert_level == AlertLevel.WARNING
        assert mapping.channel == "C003"
        assert mapping.emoji == "warning"
        assert mapping.immediate is False
        assert mapping.batch_window == 300  # 5 minutes

    def test_warning_factory_custom_batch(self):
        """Test warning() factory method with custom batch window."""
        mapping = AlertMapping.warning("C003", batch_window=600)

        assert mapping.immediate is False
        assert mapping.batch_window == 600  # 10 minutes

    def test_frozen_immutability(self):
        """Test that AlertMapping is frozen (immutable)."""
        mapping = AlertMapping.critical("C001")

        with pytest.raises(Exception):  # FrozenInstanceError
            mapping.channel = "C999"
