"""
Durable state persistence with crash recovery guarantees.

Protocol:
1. Write to temp file in same directory
2. fsync temp file (force to disk)
3. Atomic rename
4. fsync directory (ensure rename is durable)
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import Position, Order from trading.models (will exist)


@dataclass
class TradingState:
    """Complete trading state for persistence."""
    positions: dict[str, Any] = field(default_factory=dict)  # symbol -> Position dict
    pending_orders: dict[str, Any] = field(default_factory=dict)  # order_id -> Order dict
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "positions": self.positions,
            "pending_orders": self.pending_orders,
            "last_updated": self.last_updated.isoformat(),
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradingState":
        """Create from dict."""
        return cls(
            positions=data.get("positions", {}),
            pending_orders=data.get("pending_orders", {}),
            last_updated=datetime.fromisoformat(data.get("last_updated", datetime.now(timezone.utc).isoformat())),
            version=data.get("version", 1)
        )


def save_state_atomic(state: TradingState, path: Path) -> None:
    """
    Atomic write with durability guarantee.

    CRITICAL: This ensures state survives power failure/crash.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"

    # Step 1: Write to temp file
    with open(tmp_path, 'w') as f:
        json.dump(state.to_dict(), f, indent=2, default=str)
        # Step 2: Force to disk (CRITICAL)
        f.flush()
        os.fsync(f.fileno())

    # Step 3: Atomic rename (POSIX guarantee)
    tmp_path.replace(path)

    # Step 4: Sync directory entry
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def load_state(path: Path) -> TradingState | None:
    """Load state from file, return None if not exists."""
    path = Path(path)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        data = json.load(f)
    return TradingState.from_dict(data)
