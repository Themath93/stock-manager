"""Compute-once-daily cache for expensive risk metrics.

Risk metrics (sector exposure, portfolio beta, correlation matrix) are
computed ONCE daily and cached, not recalculated every 5-minute cycle.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any


class DailyRiskMetricsCache:
    """Compute-once-daily cache for expensive risk metrics."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._computed_date: date | None = None

    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """Get cached value or compute and cache it.

        Cache invalidates automatically at day boundary.

        Args:
            key: Cache key for this metric.
            compute_fn: Zero-arg callable to compute the metric if not cached.

        Returns:
            Cached or freshly computed metric value.
        """
        today = date.today()
        if self._computed_date != today:
            self._cache.clear()
            self._computed_date = today
        if key not in self._cache:
            self._cache[key] = compute_fn()
        return self._cache[key]

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate a specific key or the entire cache.

        Args:
            key: Specific key to remove. If None, clears everything.
        """
        if key is None:
            self._cache.clear()
            self._computed_date = None
        else:
            self._cache.pop(key, None)

    @property
    def is_stale(self) -> bool:
        """Check if cache needs refresh (new day or empty)."""
        return self._computed_date != date.today()
