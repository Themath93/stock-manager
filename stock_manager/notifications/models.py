"""Notification models for trading event alerts.

This module provides core data models for the notification system:
- NotificationLevel enum for severity classification
- NotificationEvent frozen dataclass for event data
- NotifierProtocol for notifier interface
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Protocol


class NotificationLevel(IntEnum):
    """Notification severity levels.

    Uses IntEnum for natural ordering (INFO < WARNING < ERROR < CRITICAL).
    """
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


@dataclass(frozen=True)
class NotificationEvent:
    """Immutable notification event data.

    Attributes:
        event_type: Dotted event type (e.g., "order.filled", "engine.started")
        level: Severity level
        title: Human-readable title for the notification
        details: Event-specific key-value data
        timestamp: Event timestamp (auto-populated with UTC now)
    """
    event_type: str
    level: NotificationLevel
    title: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NotifierProtocol(Protocol):
    """Protocol for notification senders.

    Any notifier implementation must provide a notify() method
    that accepts a NotificationEvent and returns None.
    """

    def notify(self, event: NotificationEvent) -> None:
        """Send a notification event."""
        ...
