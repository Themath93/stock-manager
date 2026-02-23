"""TTL-based cache for MarketSnapshot objects.

Follows the IndicatorCache pattern from pipeline/indicators.py (line 1022+)
but caches MarketSnapshot instances with configurable TTL expiry.

Thread-safe via RLock for single-writer + multiple-reader pattern.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from stock_manager.trading.personas.models import MarketSnapshot


@dataclass
class _CacheEntry:
    """Internal cache entry with timestamp for TTL checks."""

    snapshot: MarketSnapshot
    cached_at: float  # time.monotonic() timestamp


class OHLCVCache:
    """Thread-safe TTL-based cache for MarketSnapshot objects.

    Stores the latest MarketSnapshot per symbol with automatic expiry.
    Expired entries are lazily removed on access.

    Args:
        ttl_seconds: Time-to-live for cache entries (default 60s).

    Usage:
        cache = OHLCVCache(ttl_seconds=60)

        # Writer thread (price update loop)
        snapshot = fetcher.fetch_snapshot("005930")
        cache.update("005930", snapshot)

        # Reader threads (persona evaluation)
        snap = cache.get("005930")
        if snap is not None:
            vote = persona.evaluate(snap)

    Thread safety:
        Uses RLock. Safe for single-writer + multiple-reader pattern.
        All public methods are atomic.
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._data: dict[str, _CacheEntry] = {}
        self._ttl: float = ttl_seconds

    @property
    def ttl_seconds(self) -> float:
        """Current TTL setting in seconds."""
        return self._ttl

    @ttl_seconds.setter
    def ttl_seconds(self, value: float) -> None:
        """Update TTL. Does not affect already-cached entries' timestamps."""
        with self._lock:
            self._ttl = max(0.0, value)

    def get(self, symbol: str) -> Optional[MarketSnapshot]:
        """Return cached snapshot if present and not expired, else None.

        Expired entries are lazily removed on access.
        """
        with self._lock:
            entry = self._data.get(symbol)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._data[symbol]
                return None
            return entry.snapshot

    def update(self, symbol: str, snapshot: MarketSnapshot) -> None:
        """Store or replace the snapshot for a symbol, resetting the TTL."""
        with self._lock:
            self._data[symbol] = _CacheEntry(
                snapshot=snapshot,
                cached_at=time.monotonic(),
            )

    def get_all(self) -> dict[str, MarketSnapshot]:
        """Return a dict of all non-expired snapshots (shallow copy)."""
        with self._lock:
            self._evict_expired()
            return {k: v.snapshot for k, v in self._data.items()}

    def symbols(self) -> list[str]:
        """Return sorted list of symbols with non-expired snapshots."""
        with self._lock:
            self._evict_expired()
            return sorted(self._data.keys())

    def clear(self, symbol: Optional[str] = None) -> None:
        """Clear one symbol or all entries.

        Args:
            symbol: If provided, clear only that symbol. Otherwise clear all.
        """
        with self._lock:
            if symbol is None:
                self._data.clear()
            else:
                self._data.pop(symbol, None)

    def is_fresh(self, symbol: str) -> bool:
        """Check if a symbol has a non-expired cache entry."""
        with self._lock:
            entry = self._data.get(symbol)
            if entry is None:
                return False
            return not self._is_expired(entry)

    def age(self, symbol: str) -> Optional[float]:
        """Return seconds since the entry was cached, or None if absent.

        Returns age even for expired entries (before they're evicted).
        """
        with self._lock:
            entry = self._data.get(symbol)
            if entry is None:
                return None
            return time.monotonic() - entry.cached_at

    def __len__(self) -> int:
        """Number of entries (including potentially expired ones)."""
        with self._lock:
            return len(self._data)

    def __repr__(self) -> str:
        with self._lock:
            self._evict_expired()
            symbols = sorted(self._data.keys())
            return f"OHLCVCache(ttl={self._ttl}s, {len(symbols)} symbols: {symbols})"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_expired(self, entry: _CacheEntry) -> bool:
        """Check if a cache entry has exceeded the TTL."""
        return (time.monotonic() - entry.cached_at) > self._ttl

    def _evict_expired(self) -> None:
        """Remove all expired entries. Must be called under lock."""
        expired = [
            symbol
            for symbol, entry in self._data.items()
            if self._is_expired(entry)
        ]
        for symbol in expired:
            del self._data[symbol]
