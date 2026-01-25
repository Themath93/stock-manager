"""Tests for SlackHandlerConfig Pydantic model."""

import pytest

from stock_manager.adapters.observability.slack_handler_config import SlackHandlerConfig


class TestSlackHandlerConfig:
    """Test SlackHandlerConfig model."""

    def test_create_config(self):
        """Test creating configuration with all fields."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        assert config.bot_token == "PLACEHOLDER_TOKEN"
        assert config.critical_channel == "C001"
        assert config.error_channel == "C002"
        assert config.warning_channel == "C003"

    def test_default_timeout(self):
        """Test default timeout value."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        assert config.timeout == 3.0

    def test_default_batch_interval(self):
        """Test default batch interval value."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        assert config.batch_interval == 300

    def test_default_duplicates_filter(self):
        """Test default duplicates filter setting."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        assert config.enable_duplicates_filter is True
        assert config.duplicate_window == 60

    def test_custom_timeout(self):
        """Test custom timeout value."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
            timeout=5.0,
        )

        assert config.timeout == 5.0

    def test_custom_batch_interval(self):
        """Test custom batch interval value."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
            batch_interval=600,
        )

        assert config.batch_interval == 600

    def test_timeout_validation_minimum(self):
        """Test timeout validation - minimum value."""
        with pytest.raises(ValueError):
            SlackHandlerConfig(
                bot_token="PLACEHOLDER_TOKEN",
                critical_channel="C001",
                error_channel="C002",
                warning_channel="C003",
                timeout=0.05,  # Too small
            )

    def test_timeout_validation_maximum(self):
        """Test timeout validation - maximum value."""
        with pytest.raises(ValueError):
            SlackHandlerConfig(
                bot_token="PLACEHOLDER_TOKEN",
                critical_channel="C001",
                error_channel="C002",
                warning_channel="C003",
                timeout=60.0,  # Too large
            )

    def test_from_env_factory(self):
        """Test from_env() factory method."""
        config = SlackHandlerConfig.from_env(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        assert config.bot_token == "PLACEHOLDER_TOKEN"
        assert config.critical_channel == "C001"

    def test_frozen_immutability(self):
        """Test that config is frozen (immutable)."""
        config = SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
        )

        with pytest.raises(Exception):  # ValidationError
            config.critical_channel = "C999"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(Exception):  # ValidationError
            SlackHandlerConfig(
                bot_token="PLACEHOLDER_TOKEN",
                critical_channel="C001",
                error_channel="C002",
                warning_channel="C003",
                unknown_field="value",
            )
