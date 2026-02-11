"""
Sync-based price monitoring with polling.

Uses threading for background price updates while main thread handles trading logic.
"""

import logging
import threading
from decimal import Decimal
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

class PriceMonitor:
    """
    Sync-based price monitoring with polling.

    Runs in background thread, calls callbacks when prices update.
    """

    def __init__(
        self,
        client: Any,  # KISRestClient
        interval: float = 2.0,  # 2 second polling interval
        rate_limiter: Optional[Any] = None  # RateLimiter
    ):
        self.client = client
        self.interval = interval
        self.rate_limiter = rate_limiter
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._symbols: list[str] = []
        self._symbols_lock = threading.Lock()
        self._callback: Optional[Callable[[str, Decimal], None]] = None

    def start(
        self,
        symbols: list[str],
        callback: Callable[[str, Decimal], None]
    ) -> None:
        """
        Start monitoring in background thread.

        Args:
            symbols: List of stock symbols to monitor
            callback: Function called with (symbol, price) on each update
        """
        if self._thread and self._thread.is_alive():
            logger.warning("Monitor already running")
            return

        self._symbols = symbols
        self._callback = callback
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="PriceMonitor"
        )
        self._thread.start()
        logger.info(f"Price monitor started for {len(symbols)} symbols")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop monitoring gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("Price monitor thread did not stop cleanly")
            self._thread = None
        logger.info("Price monitor stopped")

    def add_symbol(self, symbol: str) -> None:
        """Add symbol to monitoring list (thread-safe)."""
        with self._symbols_lock:
            if symbol not in self._symbols:
                self._symbols.append(symbol)
                logger.info(f"Added {symbol} to price monitor")

    def remove_symbol(self, symbol: str) -> None:
        """Remove symbol from monitoring list (thread-safe)."""
        with self._symbols_lock:
            if symbol in self._symbols:
                self._symbols.remove(symbol)
                logger.info(f"Removed {symbol} from price monitor")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._thread is not None and self._thread.is_alive()

    def _poll_loop(self) -> None:
        """Polling loop - runs in background thread."""
        # Import here to avoid circular imports
        from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price

        while not self._stop_event.is_set():
            for symbol in list(self._symbols):  # Copy list for thread safety
                if self._stop_event.is_set():
                    break

                try:
                    # Rate limit if available
                    if self.rate_limiter:
                        self.rate_limiter.acquire()

                    # Fetch current price
                    response = inquire_current_price(self.client, symbol)

                    if response.get("rt_cd") == "0":
                        output = response.get("output", {})
                        price_str = output.get("stck_prpr", "0")
                        price = Decimal(price_str)

                        if self._callback:
                            self._callback(symbol, price)
                    else:
                        logger.warning(
                            f"Price fetch failed for {symbol}: {response.get('msg1')}"
                        )

                except Exception as e:
                    logger.warning(f"Price fetch error for {symbol}: {e}")

            # Wait for next poll interval
            self._stop_event.wait(self.interval)
