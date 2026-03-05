"""Notification backends with mandatory 5-second timeout."""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)

NOTIFICATION_TIMEOUT = 5  # seconds, connect + read


class NotificationBackend(Protocol):
    """Protocol for notification backends."""

    def send(self, message: str) -> bool:
        """Send a notification message. Returns True on success."""
        ...


class SlackNotifier:
    """Slack webhook notifier with 5-second timeout."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, message: str) -> bool:
        """Send message via Slack webhook with timeout."""
        import requests

        try:
            response = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=NOTIFICATION_TIMEOUT,
            )
            return response.ok
        except Exception:
            logger.warning("Slack notification failed")
            return False


class LogNotifier:
    """Fallback notifier that logs messages."""

    def send(self, message: str) -> bool:
        """Log notification message at INFO level."""
        logger.info("NOTIFICATION: %s", message)
        return True


class NotificationDispatcher:
    """Dispatches to multiple backends. Failure never blocks trading."""

    def __init__(self, backends: list[NotificationBackend] | None = None) -> None:
        self._backends: list[NotificationBackend] = backends or [LogNotifier()]

    def notify(self, message: str) -> None:
        """Send message to all backends. Exceptions are caught and logged."""
        for backend in self._backends:
            try:
                backend.send(message)
            except Exception:
                logger.warning("Notification backend %s failed", type(backend).__name__)
