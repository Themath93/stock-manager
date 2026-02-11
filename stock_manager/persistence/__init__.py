"""
Persistence layer for durable state management.

Provides atomic write operations with crash recovery guarantees.
"""

from stock_manager.persistence.state import (
    TradingState,
    save_state_atomic,
    load_state,
)

__all__ = [
    "TradingState",
    "save_state_atomic",
    "load_state",
]
