"""Configuration for SlackHandler using Pydantic for validation.

This module defines the configuration model for Slack notification handler.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SlackHandlerConfig(BaseModel):
    """Configuration for Slack logging handler.

    This configuration controls how log messages are sent to Slack,
    including channels, timeouts, batching, and deduplication settings.

    Attributes:
        bot_token: Slack Bot Token (FORMAT_PLACEHOLDER).
        critical_channel: Channel ID for CRITICAL level alerts.
        error_channel: Channel ID for ERROR level alerts.
        warning_channel: Channel ID for WARNING level alerts.
        timeout: Request timeout in seconds (default: 3.0).
        batch_interval: Batch aggregation interval in seconds (default: 300 = 5 minutes).
        enable_duplicates_filter: Enable duplicate message filtering (default: True).
        duplicate_window: Deduplication time window in seconds (default: 60 = 1 minute).

    Examples:
        >>> config = SlackHandlerConfig(
        ...     bot_token="PLACEHOLDER_TOKEN",
        ...     critical_channel="C001",
        ...     error_channel="C002",
        ...     warning_channel="C003",
        ... )
    """

    bot_token: str = Field(..., description="Slack Bot Token")
    critical_channel: str = Field(..., description="Channel ID for CRITICAL alerts")
    error_channel: str = Field(..., description="Channel ID for ERROR alerts")
    warning_channel: str = Field(..., description="Channel ID for WARNING alerts")

    timeout: float = Field(default=3.0, ge=0.1, le=30.0, description="Request timeout in seconds")
    batch_interval: int = Field(default=300, ge=10, le=3600, description="Batch interval in seconds")
    enable_duplicates_filter: bool = Field(default=True, description="Enable duplicate filtering")
    duplicate_window: int = Field(default=60, ge=10, le=600, description="Deduplication window in seconds")

    model_config = {
        "arbitrary_types_allowed": True,
        "frozen": True,
        "extra": "forbid",
    }

    @classmethod
    def from_env(cls, **kwargs: Any) -> SlackHandlerConfig:
        """Create configuration from environment variables or keyword arguments.

        Args:
            **kwargs: Configuration values (takes precedence over env vars).

        Returns:
            SlackHandlerConfig: Validated configuration instance.

        Examples:
            >>> config = SlackHandlerConfig.from_env(
            ...     bot_token="PLACEHOLDER",
            ...     critical_channel="C001",
            ...     error_channel="C002",
            ...     warning_channel="C003",
            ... )
        """
        return cls(**kwargs)
