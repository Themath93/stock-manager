"""Sector exposure tracking from frozen position snapshots.

Computes sector allocations from an immutable copy of positions
taken at cycle start, ensuring consistent calculations within a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class Position:
    """Minimal position representation for exposure calculation."""
    symbol: str
    sector: str
    market_value: Decimal


@dataclass(frozen=True)
class SectorExposureSnapshot:
    """Immutable snapshot of sector allocations at cycle start."""
    exposures: dict[str, Decimal]  # sector -> total value
    total_value: Decimal
    timestamp: datetime

    def get_pct(self, sector: str) -> float:
        """Get sector allocation as percentage (0-100)."""
        if self.total_value <= 0:
            return 0.0
        return float(self.exposures.get(sector, Decimal("0")) / self.total_value * 100)

    def exceeds_limit(self, sector: str, limit_pct: float) -> bool:
        """Check if a sector exceeds the given percentage limit."""
        return self.get_pct(sector) > limit_pct


def compute_sector_exposure(positions: list[Position]) -> SectorExposureSnapshot:
    """Compute sector exposure from a FROZEN copy of positions.

    Args:
        positions: List of positions (should be a snapshot, not live data).

    Returns:
        Immutable sector exposure snapshot.
    """
    exposures: dict[str, Decimal] = {}
    total = Decimal("0")
    for pos in positions:
        exposures[pos.sector] = exposures.get(pos.sector, Decimal("0")) + pos.market_value
        total += pos.market_value
    return SectorExposureSnapshot(
        exposures=exposures,
        total_value=total,
        timestamp=datetime.now(timezone.utc),
    )
