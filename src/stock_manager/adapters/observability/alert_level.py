"""Alert level enumeration for Slack notifications.

This module defines the alert levels that map to Python logging levels.
"""

from __future__ import annotations

from enum import Enum
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG


class AlertLevel(Enum):
    """Alert level for Slack notifications.

    Maps directly to Python logging levels for seamless integration.
    """

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"

    @classmethod
    def from_log_level(cls, log_level: int) -> AlertLevel:
        """Convert Python logging level to AlertLevel.

        Args:
            log_level: Python logging level constant.

        Returns:
            AlertLevel: Corresponding alert level.

        Examples:
            >>> AlertLevel.from_log_level(ERROR)
            <AlertLevel.ERROR: 'ERROR'>
        """
        level_map = {
            CRITICAL: cls.CRITICAL,
            ERROR: cls.ERROR,
            WARNING: cls.WARNING,
            INFO: cls.INFO,
            DEBUG: cls.DEBUG,
        }
        # Default to INFO for unknown levels
        return level_map.get(log_level, cls.INFO)
