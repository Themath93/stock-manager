"""Security utilities for sensitive data masking."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# TASK-006: SPEC-BACKEND-API-001-P3 Milestone 1 - Security masking utility
def mask_account_id(account_id: Optional[str], visible_chars: int = 4) -> str:
    """Mask account ID for security (e.g., "1234******").

    This function masks sensitive account information by showing only
    the first few characters and replacing the rest with asterisks.

    Args:
        account_id: The account ID to mask (10 digit numeric string)
        visible_chars: Number of characters to show at the beginning (default: 4)

    Returns:
        str: Masked account ID (e.g., "1234******")

    Examples:
        >>> mask_account_id("1234567890")
        '1234******'
        >>> mask_account_id("1234567890", visible_chars=3)
        '123*******'
        >>> mask_account_id(None)
        ''
    """
    if account_id is None:
        return ""
    if len(account_id) <= visible_chars:
        return "*" * len(account_id)
    return account_id[:visible_chars] + "*" * (len(account_id) - visible_chars)


def mask_sensitive_data(data: str, prefix_len: int = 4, suffix_len: int = 0) -> str:
    """Mask sensitive data with configurable prefix/suffix visibility.

    Args:
        data: The sensitive data to mask
        prefix_len: Number of characters to show at the beginning
        suffix_len: Number of characters to show at the end

    Returns:
        str: Masked data

    Examples:
        >>> mask_sensitive_data("secret-token-123", prefix_len=4, suffix_len=3)
        'secr***123'
        >>> mask_sensitive_data("approval_key_xyz", prefix_len=8)
        'approval_***'
    """
    if not data:
        return ""
    total_len = len(data)
    visible_len = prefix_len + suffix_len

    if total_len <= visible_len:
        return "*" * total_len

    if suffix_len == 0:
        return data[:prefix_len] + "*" * (total_len - prefix_len)
    return data[:prefix_len] + "*" * (total_len - visible_len) + data[-suffix_len:]


class SecurityLogger:
    """Logger with automatic sensitive data masking."""

    def __init__(self, logger_instance: logging.Logger):
        """Initialize security logger.

        Args:
            logger_instance: The underlying logger instance to use
        """
        self._logger = logger_instance

    def info_with_account(self, message: str, account_id: Optional[str], **kwargs) -> None:
        """Log info message with masked account ID.

        Args:
            message: Log message
            account_id: Account ID to mask in logs
            **kwargs: Additional log fields
        """
        masked_id = mask_account_id(account_id)
        self._logger.info(message, extra={"account_id": masked_id, **kwargs})

    def warning_with_account(self, message: str, account_id: Optional[str], **kwargs) -> None:
        """Log warning message with masked account ID.

        Args:
            message: Log message
            account_id: Account ID to mask in logs
            **kwargs: Additional log fields
        """
        masked_id = mask_account_id(account_id)
        self._logger.warning(message, extra={"account_id": masked_id, **kwargs})

    def error_with_account(self, message: str, account_id: Optional[str], **kwargs) -> None:
        """Log error message with masked account ID.

        Args:
            message: Log message
            account_id: Account ID to mask in logs
            **kwargs: Additional log fields
        """
        masked_id = mask_account_id(account_id)
        self._logger.error(message, extra={"account_id": masked_id, **kwargs})
