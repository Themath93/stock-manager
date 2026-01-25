"""Alert mapper for converting log levels to Slack notification configurations.

This module provides the mapping logic between Python logging levels and Slack alert settings.
"""

from __future__ import annotations

from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG

from .alert_level import AlertLevel
from .alert_mapping import AlertMapping


class AlertMapper:
    """Maps Python logging levels to Slack notification configurations.

    This class determines which channel, emoji, and delivery strategy to use
    based on the log level of a LogRecord.

    Examples:
        >>> mapper = AlertMapper(
        ...     critical_channel="C001",
        ...     error_channel="C002",
        ...     warning_channel="C003",
        ... )
        >>> mapping = mapper.get_alert_mapping(ERROR)
        >>> mapping.alert_level
        <AlertLevel.ERROR: 'ERROR'>
        >>> mapping.immediate
        True
    """

    def __init__(
        self,
        critical_channel: str,
        error_channel: str,
        warning_channel: str,
        batch_window: int = 300,
    ) -> None:
        """Initialize AlertMapper with channel configurations.

        Args:
            critical_channel: Slack channel ID for CRITICAL alerts.
            error_channel: Slack channel ID for ERROR alerts.
            warning_channel: Slack channel ID for WARNING alerts.
            batch_window: Batch aggregation window in seconds for WARNING (default: 300).

        Returns:
            None
        """
        self._critical_channel = critical_channel
        self._error_channel = error_channel
        self._warning_channel = warning_channel
        self._batch_window = batch_window

        # Pre-build mappings for performance
        self._mappings: dict[int, AlertMapping] = {
            CRITICAL: AlertMapping.critical(critical_channel),
            ERROR: AlertMapping.error(error_channel),
            WARNING: AlertMapping.warning(warning_channel, batch_window),
        }

    def get_alert_mapping(self, log_level: int) -> AlertMapping:
        """Get alert mapping for a given log level.

        Args:
            log_level: Python logging level constant.

        Returns:
            AlertMapping: Configuration for this log level.

        Examples:
            >>> mapper = AlertMapper("C001", "C002", "C003")
            >>> mapping = mapper.get_alert_mapping(ERROR)
            >>> mapping.channel == "C002"
            True
        """
        # Return exact match or default to WARNING mapping (lowest alert level)
        return self._mappings.get(log_level, self._mappings[WARNING])

    def should_alert(self, log_level: int) -> bool:
        """Determine if a log level should trigger a Slack notification.

        Args:
            log_level: Python logging level constant.

        Returns:
            bool: True if should alert, False otherwise (INFO/DEBUG).

        Examples:
            >>> mapper = AlertMapper("C001", "C002", "C003")
            >>> mapper.should_alert(ERROR)
            True
            >>> mapper.should_alert(INFO)
            False
        """
        return log_level in self._mappings

    def get_alert_level(self, log_level: int) -> AlertLevel:
        """Get AlertLevel enum from log level.

        Args:
            log_level: Python logging level constant.

        Returns:
            AlertLevel: Corresponding alert level.

        Examples:
            >>> mapper = AlertMapper("C001", "C002", "C003")
            >>> mapper.get_alert_level(ERROR)
            <AlertLevel.ERROR: 'ERROR'>
        """
        return AlertLevel.from_log_level(log_level)
