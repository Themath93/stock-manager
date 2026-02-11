"""No-op notifier for disabled Slack or testing environments."""

import logging

from stock_manager.notifications.models import NotificationEvent

logger = logging.getLogger(__name__)


class NoOpNotifier:
    """No-op notifier that logs events at DEBUG level.

    Used when Slack notifications are disabled or in test environments.
    Satisfies NotifierProtocol without any external dependencies.
    """

    def notify(self, event: NotificationEvent) -> None:
        """Log notification at DEBUG level without sending."""
        logger.debug(f"Notification (no-op): {event.event_type} - {event.title}")
