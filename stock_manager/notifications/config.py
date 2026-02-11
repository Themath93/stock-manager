"""Slack notification configuration.

Uses pydantic-settings for environment variable loading with SLACK_ prefix,
following the same pattern as KISConfig (adapters/broker/kis/config.py).
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from stock_manager.notifications.models import NotificationLevel
from stock_manager.config.paths import default_env_file


class SlackConfig(BaseSettings):
    """Slack notification configuration.

    All settings loaded from environment variables with SLACK_ prefix.
    Disabled by default - requires explicit SLACK_ENABLED=true to activate.

    Environment Variables:
        SLACK_ENABLED: Enable/disable notifications (default: false)
        SLACK_BOT_TOKEN: Slack Bot OAuth token (xoxb-...)
        SLACK_DEFAULT_CHANNEL: Default channel for all notifications
        SLACK_ORDER_CHANNEL: Override channel for order events (optional)
        SLACK_ALERT_CHANNEL: Override channel for warnings/errors (optional)
        SLACK_MIN_LEVEL: Minimum notification level to send (default: "INFO")
    """

    _DEFAULT_ENV_FILE = str(default_env_file())
    model_config = SettingsConfigDict(
        env_prefix="SLACK_",
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = False
    bot_token: SecretStr | None = None
    default_channel: str = ""
    order_channel: str = ""
    alert_channel: str = ""
    min_level: str = "INFO"

    def get_min_level(self) -> NotificationLevel:
        """Parse min_level string to NotificationLevel enum.

        Returns:
            NotificationLevel corresponding to min_level string.
            Defaults to INFO if invalid.
        """
        try:
            return NotificationLevel[self.min_level.upper()]
        except KeyError:
            return NotificationLevel.INFO
