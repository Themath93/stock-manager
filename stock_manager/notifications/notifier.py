"""Thread-safe Slack notifier for trading events.

Uses slack_sdk.WebClient for message posting with:
- Threading lock for concurrent access safety
- Fault-tolerant design (never raises into trading logic)
- Level-based filtering and channel routing
"""

import logging
import threading

from stock_manager.notifications.config import SlackConfig
from stock_manager.notifications.formatters import format_notification
from stock_manager.notifications.models import NotificationEvent, NotificationLevel

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Thread-safe Slack notifier that sends trading events to Slack channels.

    Features:
        - Thread-safe: Uses threading.Lock around Slack API calls
        - Fault-tolerant: All exceptions caught and logged, never propagated
        - Level filtering: Respects min_level from config
        - Channel routing: Routes events to appropriate channels

    Example:
        >>> config = SlackConfig(enabled=True, bot_token="xoxb-...", default_channel="#trading")
        >>> notifier = SlackNotifier(config)
        >>> notifier.notify(event)  # Thread-safe, never raises
    """

    def __init__(self, config: SlackConfig) -> None:
        self._config = config
        self._client = None
        self._lock = threading.Lock()
        self._min_level = config.get_min_level()

        if config.enabled and config.bot_token:
            try:
                from slack_sdk import WebClient
                self._client = WebClient(token=config.bot_token.get_secret_value())
                logger.info("SlackNotifier initialized with WebClient")
            except ImportError:
                logger.warning("slack_sdk not available, falling back to no-op")
            except Exception as e:
                logger.warning(f"Failed to initialize Slack WebClient: {e}")

    def notify(self, event: NotificationEvent) -> None:
        """Send notification to Slack (thread-safe, fault-tolerant).

        This method:
        1. Checks if notification should be sent (level, enabled, client)
        2. Formats the event using Block Kit formatters
        3. Sends to the appropriate channel
        4. Catches ALL exceptions (never propagates)

        Args:
            event: Notification event to send
        """
        if not self._should_send(event):
            return

        try:
            formatted = format_notification(event)
            channel = self._resolve_channel(event)

            with self._lock:
                self._client.chat_postMessage(
                    channel=channel,
                    text=formatted["text"],
                    attachments=[{
                        "color": formatted["color"],
                        "blocks": formatted["blocks"],
                    }],
                )
            logger.debug(f"Slack notification sent: {event.event_type}")
        except Exception as e:
            logger.warning(f"Slack notification failed: {e}", exc_info=False)

    def _should_send(self, event: NotificationEvent) -> bool:
        """Check if event should be sent based on config and level.

        Returns:
            True if event meets all sending criteria
        """
        if self._client is None:
            return False
        if not self._config.enabled:
            return False
        if event.level < self._min_level:
            return False
        return True

    def _resolve_channel(self, event: NotificationEvent) -> str:
        """Route event to appropriate Slack channel.

        Routing rules:
        1. Order events (order.*) -> order_channel if set
        2. Warning+ events -> alert_channel if set
        3. Fallback -> default_channel

        Args:
            event: Notification event to route

        Returns:
            Channel ID or name string
        """
        # Order events to order channel
        if event.event_type.startswith("order.") and self._config.order_channel:
            return self._config.order_channel

        # Warning+ events to alert channel
        if event.level >= NotificationLevel.WARNING and self._config.alert_channel:
            return self._config.alert_channel

        return self._config.default_channel
