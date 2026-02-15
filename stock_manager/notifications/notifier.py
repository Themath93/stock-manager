"""Thread-safe Slack notifier for trading events.

Uses slack_sdk.WebClient for message posting with:
- Threading lock for concurrent access safety
- Fault-tolerant design (never raises into trading logic)
- Level-based filtering and channel routing
"""

import logging
import queue
import threading
from typing import TYPE_CHECKING, Any, Protocol, cast

from stock_manager.notifications.config import SlackConfig
from stock_manager.notifications.formatters import format_notification
from stock_manager.notifications.models import NotificationEvent, NotificationLevel

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from slack_sdk import WebClient


class _SlackClient(Protocol):
    def chat_postMessage(self, **kwargs: Any) -> Any: ...


class SlackNotifier:
    """Thread-safe Slack notifier that sends trading events to Slack channels.

    Features:
        - Thread-safe: Uses threading.Lock around Slack API calls
        - Fault-tolerant: All exceptions caught and logged, never propagated
        - Level filtering: Respects min_level from config
        - Channel routing: Routes events to appropriate channels

    Example:
        >>> config = SlackConfig(enabled=True, bot_token="xoxb-...", default_channel="#trading")
        >>> notifier = SlackNotifier(config)
        >>> notifier.notify(event)  # Thread-safe, never raises
    """

    def __init__(self, config: SlackConfig) -> None:
        self._config = config
        self._client: _SlackClient | None = None
        self._lock = threading.Lock()
        self._min_level = config.get_min_level()
        self._async_enabled = False
        self._queue: queue.Queue[NotificationEvent] | None = None
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        if config.enabled and config.bot_token:
            try:
                from slack_sdk import WebClient

                self._client = cast(
                    _SlackClient, WebClient(token=config.bot_token.get_secret_value())
                )
                logger.info("SlackNotifier initialized with WebClient")
                self._async_enabled = config.async_enabled
                if self._async_enabled:
                    self._queue = queue.Queue(maxsize=max(1, config.queue_maxsize))
                    self._worker_thread = threading.Thread(
                        target=self._worker_loop,
                        name="SlackNotifierWorker",
                        daemon=True,
                    )
                    self._worker_thread.start()
            except ImportError:
                logger.warning("slack_sdk not available, falling back to no-op")
            except Exception as e:
                logger.warning(f"Failed to initialize Slack WebClient: {e}")

    def notify(self, event: NotificationEvent) -> None:
        """Send notification to Slack (thread-safe, fault-tolerant).

        This method:
        1. Checks if notification should be sent (level, enabled, client)
        2. Formats the event using Block Kit formatters
        3. Sends to the appropriate channel
        4. Catches ALL exceptions (never propagates)

        Args:
            event: Notification event to send
        """
        if not self._should_send(event):
            return

        if self._async_enabled and self._queue is not None:
            try:
                self._queue.put_nowait(event)
                return
            except queue.Full:
                if event.level >= NotificationLevel.ERROR:
                    logger.warning(
                        "Slack queue full, using synchronous fallback for %s", event.event_type
                    )
                    self._send_sync(event)
                    return
                logger.warning("Slack queue full, dropping %s", event.event_type)
                return

        self._send_sync(event)

    def _should_send(self, event: NotificationEvent) -> bool:
        """Check if event should be sent based on config and level.

        Returns:
            True if event meets all sending criteria
        """
        if self._client is None:
            return False
        if not self._config.enabled:
            return False
        if event.level < self._min_level:
            return False
        return True

    def _resolve_channel(self, event: NotificationEvent) -> str:
        """Route event to appropriate Slack channel.

        Routing rules:
        1. Order events (order.*) -> order_channel if set
        2. Warning+ events -> alert_channel if set
        3. Fallback -> default_channel

        Args:
            event: Notification event to route

        Returns:
            Channel ID or name string
        """
        # Order events to order channel
        if event.event_type.startswith("order.") and self._config.order_channel:
            return self._config.order_channel

        # Warning+ events to alert channel
        if event.level >= NotificationLevel.WARNING and self._config.alert_channel:
            return self._config.alert_channel

        return self._config.default_channel

    def close(self, timeout: float = 2.0) -> None:
        """Stop async worker if enabled."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            self._worker_thread = None

    def _worker_loop(self) -> None:
        """Background worker that drains Slack events."""
        if self._queue is None:
            return

        while True:
            if self._stop_event.is_set() and self._queue.empty():
                return

            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._send_sync(event)
            finally:
                self._queue.task_done()

    def _send_sync(self, event: NotificationEvent) -> None:
        """Synchronous send path shared by direct and async worker modes."""
        client = self._client
        if client is None:
            return
        try:
            formatted = format_notification(event)
            channel = self._resolve_channel(event)

            with self._lock:
                client.chat_postMessage(
                    channel=channel,
                    text=formatted["text"],
                    attachments=[
                        {
                            "color": formatted["color"],
                            "blocks": formatted["blocks"],
                        }
                    ],
                )
            logger.debug(f"Slack notification sent: {event.event_type}")
        except Exception as e:
            logger.warning(f"Slack notification failed: {e}", exc_info=False)
