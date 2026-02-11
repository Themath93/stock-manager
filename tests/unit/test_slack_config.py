"""Unit tests for SlackConfig."""


from stock_manager.notifications.config import SlackConfig
from stock_manager.notifications.models import NotificationLevel


class TestSlackConfigDefaults:
    """Test default configuration values."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = SlackConfig(_env_file=None)
        assert config.enabled is False
        assert config.bot_token is None
        assert config.default_channel == ""
        assert config.order_channel == ""
        assert config.alert_channel == ""
        assert config.min_level == "INFO"


class TestSlackConfigEnvLoading:
    """Test environment variable loading."""

    def test_env_var_loading(self, monkeypatch):
        """Test that SLACK_ prefixed env vars are loaded."""
        monkeypatch.setenv("SLACK_ENABLED", "true")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "test-bot-token-12345")
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#trading")
        monkeypatch.setenv("SLACK_ORDER_CHANNEL", "#orders")
        monkeypatch.setenv("SLACK_ALERT_CHANNEL", "#alerts")
        monkeypatch.setenv("SLACK_MIN_LEVEL", "WARNING")

        config = SlackConfig(_env_file=None)
        assert config.enabled is True
        assert config.bot_token.get_secret_value() == "test-bot-token-12345"
        assert config.default_channel == "#trading"
        assert config.order_channel == "#orders"
        assert config.alert_channel == "#alerts"
        assert config.min_level == "WARNING"


class TestGetMinLevel:
    """Test get_min_level() method."""

    def test_valid_level_info(self):
        """Test parsing valid INFO level."""
        config = SlackConfig(min_level="INFO", _env_file=None)
        assert config.get_min_level() == NotificationLevel.INFO

    def test_valid_level_warning(self):
        """Test parsing valid WARNING level."""
        config = SlackConfig(min_level="WARNING", _env_file=None)
        assert config.get_min_level() == NotificationLevel.WARNING

    def test_invalid_level_defaults_to_info(self):
        """Test that invalid level defaults to INFO."""
        config = SlackConfig(min_level="INVALID", _env_file=None)
        assert config.get_min_level() == NotificationLevel.INFO

    def test_case_insensitive_parsing(self):
        """Test case-insensitive level parsing."""
        config = SlackConfig(min_level="error", _env_file=None)
        assert config.get_min_level() == NotificationLevel.ERROR

    def test_all_levels(self):
        """Test all valid notification levels."""
        levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        for level_str in levels:
            config = SlackConfig(min_level=level_str, _env_file=None)
            parsed = config.get_min_level()
            assert parsed == NotificationLevel[level_str]
