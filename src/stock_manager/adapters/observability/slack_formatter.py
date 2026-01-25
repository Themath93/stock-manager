"""Slack message formatter for structured log notifications.

This module provides a custom logging.Formatter that formats log records
into Slack-friendly messages with sensitive data masking.
"""

from __future__ import annotations

import logging
import re
import traceback
from typing import Any

from .alert_level import AlertLevel


class SlackFormatter(logging.Formatter):
    """Formats log records into Slack-compatible messages.

    This formatter creates structured messages suitable for Slack notifications,
    including emoji indicators, level badges, and sensitive data masking.

    Examples:
        >>> formatter = SlackFormatter()
        >>> record = logging.LogRecord(
        ...     name="test",
        ...     level=logging.ERROR,
        ...     pathname="test.py",
        ...     lineno=1,
        ...     msg="Database connection failed",
        ...     args=(),
        ...     exc_info=None,
        ... )
        >>> message = formatter.format(record)
        >>> "ERROR" in message
        True
    """

    # Sensitive data patterns to mask
    SENSITIVE_PATTERNS = [
        r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-@.=]+["\']?',
        r'secret["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-@.=]+["\']?',
        r'password["\']?\s*[:=]\s*["\']?[^\s"\']+["\']?',
        r'api_key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-@.=]+["\']?',
        r'apikey["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-@.=]+["\']?',
        r'xoxb-[A-Za-z0-9\-]+',
        r'xoxp-[A-Za-z0-9\-]+',
        r'Bearer [A-Za-z0-9_\-\.=]+',
        r'sk-[a-zA-Z0-9]{32,}',
    ]

    # Emoji mapping for alert levels
    EMOJI_MAP = {
        AlertLevel.CRITICAL: ":rotating_light:",
        AlertLevel.ERROR: ":x:",
        AlertLevel.WARNING: ":warning:",
        AlertLevel.INFO: ":information_source:",
        AlertLevel.DEBUG: ":bug:",
    }

    def __init__(self, enable_masking: bool = True) -> None:
        """Initialize SlackFormatter.

        Args:
            enable_masking: Whether to mask sensitive data (default: True).

        Returns:
            None
        """
        super().__init__()
        self._enable_masking = enable_masking
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SENSITIVE_PATTERNS
        ]

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record into a Slack message.

        Args:
            record: The LogRecord to format.

        Returns:
            str: Formatted message suitable for Slack.

        Examples:
            >>> formatter = SlackFormatter()
            >>> record = logging.LogRecord(
            ...     name="app",
            ...     level=logging.ERROR,
            ...     pathname="app.py",
            ...     lineno=10,
            ...     msg="Error occurred",
            ...     args=(),
            ...     exc_info=None,
            ... )
            >>> msg = formatter.format(record)
            >>> isinstance(msg, str)
            True
        """
        alert_level = AlertLevel.from_log_level(record.levelno)
        emoji = self.EMOJI_MAP.get(alert_level, "")

        # Build message parts
        parts = [
            f"{emoji} *{alert_level.value}*",
            f"from *{record.name}*",
        ]

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            parts.append(f"\n```\n{exc_text}\n```")

        # Add the main message
        message = self._format_message(record.getMessage())
        parts.append(f"\n{message}")

        # Add context if available
        if hasattr(record, "slack_context"):
            context = record.slack_context  # type: ignore[attr-defined]
            if isinstance(context, dict):
                context_parts = [f"• *{k}*: `{v}`" for k, v in context.items()]
                parts.append(f"\n{''.join(context_parts)}")

        formatted = "\n".join(parts)

        # Apply masking if enabled
        if self._enable_masking:
            formatted = self.mask_sensitive_data(formatted)

        return formatted

    def _format_message(self, message: str) -> str:
        """Format the main message part.

        Args:
            message: Raw message string.

        Returns:
            str: Formatted message.
        """
        # Convert to string if needed
        if not isinstance(message, str):
            message = str(message)
        return message

    def mask_sensitive_data(self, message: str) -> str:
        """Mask sensitive data in the message.

        Args:
            message: Message that may contain sensitive data.

        Returns:
            str: Message with sensitive data masked.

        Examples:
            >>> formatter = SlackFormatter()
            >>> masked = formatter.mask_sensitive_data("token=abc123")
            >>> "abc123" not in masked
            True
            >>> "token" in masked or "***" in masked
            True
        """
        masked = message

        for pattern in self._compiled_patterns:
            masked = pattern.sub(
                lambda m: f"{m.group(0).split('=')[0] if '=' in m.group(0) else m.group(0)[:10]}***",
                masked
            )

        return masked

    def formatException(self, exc_info: Any) -> str:
        """Format exception information.

        Args:
            exc_info: Exception info tuple from sys.exc_info().

        Returns:
            str: Formatted exception traceback.

        Examples:
            >>> try:
            ...     1 / 0
            ... except ZeroDivisionError:
            ...     exc_info = True  # Simplified
            ...     formatter = SlackFormatter()
            ...     # formatter.formatException(sys.exc_info())
            ...     "ZeroDivisionError" in str(sys.exc_info())
            True
        """
        if exc_info:
            return "".join(traceback.format_exception(*exc_info))
        return ""
