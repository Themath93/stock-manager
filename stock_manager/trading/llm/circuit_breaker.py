"""Three-state finite-state-machine circuit breaker for LLM calls.

Protects the system from cascading failures when the Claude CLI is
unavailable or consistently failing. Thread-safe via :class:`threading.RLock`.

States::

    CLOSED  ──(failures >= threshold)──▸  OPEN
    OPEN    ──(cooldown elapsed)──────▸  HALF_OPEN
    HALF_OPEN ──(success)──────────────▸  CLOSED
    HALF_OPEN ──(failure)──────────────▸  OPEN
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Sliding-window circuit breaker with automatic OPEN -> HALF_OPEN transition.

    Args:
        failure_threshold: Number of failures within the sliding window
            that triggers the OPEN state. Configurable via
            ``LLM_CB_FAILURE_THRESHOLD`` env var.
        cooldown_sec: Seconds to wait in OPEN before transitioning to
            HALF_OPEN. Configurable via ``LLM_CB_COOLDOWN_SEC`` env var.
        sliding_window_sec: Width of the sliding failure-counting window
            in seconds.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        cooldown_sec: float | None = None,
        sliding_window_sec: float = 300.0,
    ) -> None:
        self._failure_threshold = failure_threshold or int(
            os.environ.get("LLM_CB_FAILURE_THRESHOLD", "5")
        )
        self._cooldown_sec = cooldown_sec or float(
            os.environ.get("LLM_CB_COOLDOWN_SEC", "60")
        )
        self._sliding_window_sec = sliding_window_sec

        self._state = CircuitState.CLOSED
        self._failure_timestamps: deque[float] = deque()
        self._opened_at: float = 0.0
        self._lock = threading.RLock()

    # -- Properties -----------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current state with automatic OPEN -> HALF_OPEN transition."""
        with self._lock:
            if (
                self._state == CircuitState.OPEN
                and (time.monotonic() - self._opened_at) >= self._cooldown_sec
            ):
                self._state = CircuitState.HALF_OPEN
            return self._state

    @property
    def failure_count(self) -> int:
        """Number of failures within the current sliding window."""
        with self._lock:
            self._prune_window()
            return len(self._failure_timestamps)

    # -- Public API -----------------------------------------------------------

    def allow_request(self) -> bool:
        """Whether a request should be permitted.

        Returns:
            True for CLOSED and HALF_OPEN states, False for OPEN.
        """
        current = self.state  # triggers auto-transition
        return current != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call. Resets to CLOSED."""
        with self._lock:
            self._failure_timestamps.clear()
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call. May trip the breaker to OPEN."""
        with self._lock:
            now = time.monotonic()
            self._failure_timestamps.append(now)
            self._prune_window()

            if len(self._failure_timestamps) >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = now

    # -- Internal -------------------------------------------------------------

    def _prune_window(self) -> None:
        """Remove failure timestamps outside the sliding window."""
        cutoff = time.monotonic() - self._sliding_window_sec
        while self._failure_timestamps and self._failure_timestamps[0] < cutoff:
            self._failure_timestamps.popleft()
