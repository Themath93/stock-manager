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
        SLACK_ANALYSIS_CHANNEL: Channel for analysis events (#trading-analysis)
        SLACK_ORDERS_CHANNEL: Channel for order events (#trading-orders)
        SLACK_POSITIONS_CHANNEL: Channel for position events (#trading-positions)
        SLACK_ALERTS_CHANNEL: Channel for alert events (#trading-alerts)
        SLACK_RESULTS_CHANNEL: Channel for trade result events (#trading-results)
        SLACK_MIN_LEVEL: Minimum notification level to send (default: "INFO")
        SLACK_APP_TOKEN: Slack App-Level Token for Socket Mode (xapp-...)
        SLACK_ALLOWED_USER_IDS: Comma-separated Slack User IDs allowed to use bot (empty = all users)
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
    async_enabled: bool = False
    queue_maxsize: int = 1000

    # Socket Mode (for Slack Bot trigger system)
    app_token: SecretStr | None = None  # SLACK_APP_TOKEN (xapp-...)
    allowed_user_ids: str = ""          # SLACK_ALLOWED_USER_IDS (comma-separated)

    # Pipeline-specific channels (loaded from SLACK_<NAME>_CHANNEL env vars)
    analysis_channel: str = ""    # #trading-analysis
    orders_channel: str = ""      # #trading-orders
    positions_channel: str = ""   # #trading-positions
    alerts_channel: str = ""      # #trading-alerts
    results_channel: str = ""     # #trading-results

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

    def get_channel_for_event(self, event_type: str) -> str:
        """Resolve the appropriate Slack channel for a pipeline event type.

        Looks up the event type in CHANNEL_MAP, then resolves the channel
        field on this config instance. Falls back to default_channel if the
        mapped channel is empty.

        Args:
            event_type: Pipeline event type (e.g. "agent_vote", "buy_decision").

        Returns:
            Channel name string. Empty string if no channel configured.
        """
        field_name = CHANNEL_MAP.get(event_type, "default_channel")
        channel = getattr(self, field_name, "") or ""
        return channel or self.default_channel


# Maps pipeline event types to SlackConfig channel field names.
CHANNEL_MAP: dict[str, str] = {
    # Analysis events -> analysis_channel
    "screening_complete": "analysis_channel",
    "agent_vote": "analysis_channel",
    "advisory_vote": "analysis_channel",
    "consensus_result": "analysis_channel",
    # Order events -> orders_channel
    "buy_decision": "orders_channel",
    "order_executed": "orders_channel",
    # Position events -> positions_channel
    "state_change": "positions_channel",
    "condition_check": "positions_channel",
    # Alert events -> alerts_channel
    "condition_warning": "alerts_channel",
    "sell_trigger": "alerts_channel",
    "error": "alerts_channel",
    # Result events -> results_channel
    "trade_complete": "results_channel",
}
