"""Slack notification handler for Python logging framework.

This module implements a custom logging.Handler that sends log records
to Slack channels based on their severity level.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import hashlib
from typing import Any

from slack_sdk import WebClient

from stock_manager.utils.slack import SlackClient

from .slack_handler_config import SlackHandlerConfig
from .alert_mapper import AlertMapper
from .slack_formatter import SlackFormatter


class SlackHandler(logging.Handler):
    """Logging handler that sends notifications to Slack.

    This handler integrates with Python's logging framework to automatically
    send error and critical messages to designated Slack channels.

    Features:
    - Asynchronous non-blocking delivery
    - Level-based channel routing
    - Batch aggregation for warnings
    - Duplicate message filtering
    - Sensitive data masking

    Examples:
        >>> import logging
        >>> config = SlackHandlerConfig(
        ...     bot_token="PLACEHOLDER",
        ...     critical_channel="C001",
        ...     error_channel="C002",
        ...     warning_channel="C003",
        ... )
        >>> handler = SlackHandler(config)
        >>> logger = logging.getLogger("myapp")
        >>> logger.addHandler(handler)
        >>> logger.error("Database connection failed")  # Sends to Slack
    """

    def __init__(self, config: SlackHandlerConfig) -> None:
        """Initialize SlackHandler with configuration.

        Args:
            config: Handler configuration including channels and timeouts.

        Returns:
            None
        """
        super().__init__()

        self._config = config
        self._client = SlackClient(
            token=config.bot_token,
            timeout=config.timeout,
        )
        self._mapper = AlertMapper(
            critical_channel=config.critical_channel,
            error_channel=config.error_channel,
            warning_channel=config.warning_channel,
            batch_window=config.batch_interval,
        )
        self._formatter = SlackFormatter(enable_masking=True)

        # Async delivery queue
        self._queue: queue.Queue[tuple[logging.LogRecord, AlertMapping]] = queue.Queue()
        self._batch_queue: list[logging.LogRecord] = []

        # Duplicate filter
        self._duplicate_hashes: dict[str, float] = {}
        self._duplicate_lock = threading.Lock()

        # Worker thread
        self._worker_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

        # Batching timer
        self._last_batch_time = time.time()

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record and send to Slack if appropriate.

        This method is called by the logging framework for each log record.
        It determines if the record should be sent to Slack and queues it
        for asynchronous delivery.

        Args:
            record: The LogRecord to process.

        Returns:
            None

        Note:
            This method never raises exceptions to prevent logging failures
            from affecting application behavior.
        """
        try:
            # Check if we should alert for this level
            if not self._mapper.should_alert(record.levelno):
                return

            # Get alert mapping
            mapping = self._mapper.get_alert_mapping(record.levelno)

            # Check duplicates if enabled
            if self._config.enable_duplicates_filter:
                if self._is_duplicate(record):
                    return

            # Handle immediate vs batch delivery
            if mapping.immediate:
                self._queue.put((record, mapping))
                self._ensure_worker()
            else:
                self._handle_batch(record, mapping)

        except Exception:  # pragma: no cover - safety net
            # Never let logging failures affect the application
            self.handleError(record)

    def _is_duplicate(self, record: logging.LogRecord) -> bool:
        """Check if this record is a duplicate of a recent message.

        Args:
            record: The LogRecord to check.

        Returns:
            bool: True if duplicate, False otherwise.
        """
        # Create hash from message and exception info
        hash_parts = [record.getMessage()]
        if record.exc_info:
            hash_parts.append(str(record.exc_info))

        hash_input = "|".join(hash_parts).encode("utf-8")
        message_hash = hashlib.sha256(hash_input).hexdigest()

        current_time = time.time()

        with self._duplicate_lock:
            # Clean old hashes
            self._cleanup_old_hashes(current_time)

            # Check if duplicate
            if message_hash in self._duplicate_hashes:
                return True

            # Record this hash
            self._duplicate_hashes[message_hash] = current_time
            return False

    def _cleanup_old_hashes(self, current_time: float) -> None:
        """Remove old hashes outside the duplicate window.

        Args:
            current_time: Current Unix timestamp.

        Returns:
            None
        """
        cutoff = current_time - self._config.duplicate_window
        self._duplicate_hashes = {
            h: t for h, t in self._duplicate_hashes.items()
            if t > cutoff
        }

    def _handle_batch(self, record: logging.LogRecord, mapping: Any) -> None:
        """Handle batch aggregation for non-immediate messages.

        Args:
            record: The LogRecord to batch.
            mapping: Alert mapping configuration.

        Returns:
            None
        """
        self._batch_queue.append(record)

        # Check if batch window has elapsed
        current_time = time.time()
        if current_time - self._last_batch_time >= self._config.batch_interval:
            self._flush_batch()
            self._last_batch_time = current_time
        else:
            # Ensure worker is running to handle batch flush
            self._ensure_worker()

    def _flush_batch(self) -> None:
        """Flush batched messages to Slack.

        Returns:
            None
        """
        if not self._batch_queue:
            return

        # Create aggregated message
        batch_records = self._batch_queue[:]
        self._batch_queue.clear()

        if len(batch_records) == 1:
            # Single message, send normally
            record = batch_records[0]
            mapping = self._mapper.get_alert_mapping(record.levelno)
            self._queue.put((record, mapping))
        else:
            # Multiple messages, aggregate
            aggregated_msg = f"*{len(batch_records)} warnings aggregated*\n"
            for record in batch_records[-5:]:  # Last 5 only
                aggregated_msg += f"• {record.getMessage()}\n"

            if len(batch_records) > 5:
                aggregated_msg += f"\n... and {len(batch_records) - 5} more"

            # Create a wrapper record for the aggregated message
            wrapper_record = logging.LogRecord(
                name="batch_aggregator",
                level=logging.WARNING,
                pathname="",
                lineno=0,
                msg=aggregated_msg,
                args=(),
                exc_info=None,
            )
            mapping = self._mapper.get_alert_mapping(logging.WARNING)
            self._queue.put((wrapper_record, mapping))

    def _ensure_worker(self) -> None:
        """Ensure the worker thread is running.

        Returns:
            None
        """
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="SlackHandler-Worker",
            )
            self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Worker thread loop for processing the queue.

        Returns:
            None
        """
        while not self._shutdown_event.is_set():
            try:
                # Get item with timeout to allow shutdown check
                try:
                    record, mapping = self._queue.get(timeout=1.0)
                except queue.Empty:
                    # Timeout, check batch flush
                    if self._batch_queue:
                        self._flush_batch()
                    continue

                # Format and send
                message = self._formatter.format(record)
                self._send_to_slack(message, mapping.channel)

            except Exception:  # pragma: no cover - safety net
                # Log but continue processing
                continue

    def _send_to_slack(self, message: str, channel: str) -> None:
        """Send formatted message to Slack.

        Args:
            message: Formatted message string.
            channel: Slack channel ID.

        Returns:
            None
        """
        try:
            self._client.post_message(
                text=message,
                channel=channel,
            )
        except Exception:  # pragma: no cover - safety net
            # Send failed, but don't affect application
            pass

    def close(self) -> None:
        """Close the handler and cleanup resources.

        Returns:
            None
        """
        self._shutdown_event.set()

        # Flush any remaining batch
        if self._batch_queue:
            self._flush_batch()

        # Wait for worker to finish (with timeout)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

        super().close()

    def __enter__(self) -> SlackHandler:
        """Context manager entry.

        Returns:
            SlackHandler: Self for context manager support.
        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit.

        Args:
            *args: Exception info if any.

        Returns:
            None
        """
        self.close()
