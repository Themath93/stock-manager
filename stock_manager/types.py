"""Shared data types used across multiple layers.

Types defined here are layer-neutral and may be imported by any module
(adapters, trading, engine, etc.) without violating architecture contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BrokerTruthSnapshot:
    cash: dict[str, Any]
    positions: tuple[dict[str, Any], ...]
    open_orders: tuple[dict[str, Any], ...]
    fetched_at: datetime
    snapshot_ok: bool

    @property
    def open_order_count(self) -> int:
        return len(self.open_orders)
