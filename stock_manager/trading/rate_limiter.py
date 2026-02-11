"""
KIS API rate limiter - 20 requests per second recommended.

Thread-safe sliding window implementation.
"""

from threading import Lock
from time import time, sleep
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.

    Default: 20 requests per second to comply with KIS API limits.
    """

    def __init__(self, max_requests: int = 20, window_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: list[float] = []
        self._lock = Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Block until request is allowed.

        Args:
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if acquired, False if timeout
        """
        start_time = time()

        while True:
            with self._lock:
                now = time()

                # Remove old requests outside window
                self.requests = [t for t in self.requests if now - t < self.window]

                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True

                # Calculate wait time
                if self.requests:
                    sleep_time = self.requests[0] + self.window - now
                else:
                    sleep_time = 0

            # Check timeout
            if timeout is not None and (time() - start_time + sleep_time) > timeout:
                return False

            if sleep_time > 0:
                sleep(min(sleep_time, 0.1))  # Sleep in small increments

    def try_acquire(self) -> bool:
        """
        Non-blocking attempt to acquire.

        Returns:
            True if acquired, False if rate limited
        """
        with self._lock:
            now = time()
            self.requests = [t for t in self.requests if now - t < self.window]

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False

    @property
    def available(self) -> int:
        """Number of requests available in current window."""
        with self._lock:
            now = time()
            self.requests = [t for t in self.requests if now - t < self.window]
            return self.max_requests - len(self.requests)

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self.requests.clear()
