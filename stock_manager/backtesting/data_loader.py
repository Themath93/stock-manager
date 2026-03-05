"""Historical data loading for backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class HistoricalBar:
    """Single OHLCV bar."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class HistoricalDataLoader:
    """Loads historical OHLCV data for backtesting.

    Currently supports loading from list of dicts (in-memory).
    Future: CSV files, database, API.
    """

    def __init__(self) -> None:
        self._cache: dict[str, list[HistoricalBar]] = {}

    def load_from_records(self, symbol: str, records: list[dict]) -> None:
        """Load bars from list of dicts with keys: date, open, high, low, close, volume."""
        bars = []
        for r in records:
            bars.append(
                HistoricalBar(
                    date=r["date"]
                    if isinstance(r["date"], date)
                    else date.fromisoformat(str(r["date"])),
                    open=Decimal(str(r["open"])),
                    high=Decimal(str(r["high"])),
                    low=Decimal(str(r["low"])),
                    close=Decimal(str(r["close"])),
                    volume=int(r["volume"]),
                )
            )
        bars.sort(key=lambda b: b.date)
        self._cache[symbol] = bars

    def get_bars(self, symbol: str, start: date, end: date) -> list[HistoricalBar]:
        """Get bars for symbol within date range (inclusive)."""
        all_bars = self._cache.get(symbol, [])
        return [b for b in all_bars if start <= b.date <= end]

    def get_bar_on_date(self, symbol: str, target: date) -> HistoricalBar | None:
        """Get single bar for exact date, or None."""
        bars = self._cache.get(symbol, [])
        for b in bars:
            if b.date == target:
                return b
        return None

    def available_symbols(self) -> list[str]:
        """Return list of symbols with loaded data."""
        return list(self._cache.keys())
