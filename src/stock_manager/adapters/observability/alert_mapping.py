"""Alert mapping dataclass for log level to notification configuration.

This module defines the mapping between Python logging levels and Slack notification settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .alert_level import AlertLevel

if TYPE_CHECKING:
    from typing import Self


@dataclass(frozen=True)
class AlertMapping:
    """Mapping from log level to Slack notification configuration.

    Attributes:
        log_level: Python logging level constant (e.g., logging.ERROR).
        alert_level: AlertLevel enum for categorization.
        channel: Slack channel ID for notifications.
        emoji: Emoji indicator for the alert level.
        immediate: Whether to send immediately (True) or batch (False).
        batch_window: Batch aggregation window in seconds (None if immediate).

    Examples:
        >>> mapping = AlertMapping(
        ...     log_level=40,  # ERROR
        ...     alert_level=AlertLevel.ERROR,
        ...     channel="C12345",
        ...     emoji="x",
        ...     immediate=True,
        ...     batch_window=None,
        ... )
    """

    log_level: int
    alert_level: AlertLevel
    channel: str
    emoji: str
    immediate: bool
    batch_window: int | None

    @classmethod
    def critical(cls, channel: str) -> Self:
        """Create CRITICAL level mapping.

        Args:
            channel: Slack channel ID for critical alerts.

        Returns:
            AlertMapping configured for CRITICAL level.
        """
        return cls(
            log_level=50,  # CRITICAL
            alert_level=AlertLevel.CRITICAL,
            channel=channel,
            emoji="!",
            immediate=True,
            batch_window=None,
        )

    @classmethod
    def error(cls, channel: str) -> Self:
        """Create ERROR level mapping.

        Args:
            channel: Slack channel ID for error alerts.

        Returns:
            AlertMapping configured for ERROR level.
        """
        return cls(
            log_level=40,  # ERROR
            alert_level=AlertLevel.ERROR,
            channel=channel,
            emoji="x",
            immediate=True,
            batch_window=None,
        )

    @classmethod
    def warning(cls, channel: str, batch_window: int = 300) -> Self:
        """Create WARNING level mapping with batching.

        Args:
            channel: Slack channel ID for warning alerts.
            batch_window: Batch aggregation window in seconds (default: 300 = 5 minutes).

        Returns:
            AlertMapping configured for WARNING level.
        """
        return cls(
            log_level=30,  # WARNING
            alert_level=AlertLevel.WARNING,
            channel=channel,
            emoji="warning",
            immediate=False,
            batch_window=batch_window,
        )
