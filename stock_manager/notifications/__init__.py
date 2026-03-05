"""Slack notification system for trading events."""

from stock_manager.notifications.backends import (
    NOTIFICATION_TIMEOUT,
    LogNotifier,
    NotificationBackend,
    NotificationDispatcher,
)
from stock_manager.notifications.backends import (
    SlackNotifier as SlackWebhookNotifier,
)
from stock_manager.notifications.config import SlackConfig
from stock_manager.notifications.models import (
    NotificationEvent,
    NotificationLevel,
    NotifierProtocol,
)
from stock_manager.notifications.notifier import SlackNotifier
from stock_manager.notifications.noop import NoOpNotifier

__all__ = [
    "NOTIFICATION_TIMEOUT",
    "LogNotifier",
    "NotificationBackend",
    "NotificationDispatcher",
    "SlackWebhookNotifier",
    "SlackConfig",
    "SlackNotifier",
    "NoOpNotifier",
    "NotificationEvent",
    "NotificationLevel",
    "NotifierProtocol",
]
