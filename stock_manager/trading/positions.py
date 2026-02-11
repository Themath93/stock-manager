"""
Thread-safe position management.

Uses RLock to protect shared state accessed from multiple threads
(main thread and price monitor thread).
"""

from threading import RLock
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Callable, Optional
import logging

from .models import Position, PositionStatus

logger = logging.getLogger(__name__)


def is_stop_loss_triggered(
    current_price: Decimal | None,
    stop_loss: Decimal | None
) -> bool:
    """Check if stop-loss price has been triggered.

    Pure function - no side effects, easily testable.

    Args:
        current_price: Current market price (None if unknown)
        stop_loss: Stop-loss price level (None if not set)

    Returns:
        True if stop-loss is triggered (price <= stop_loss)
    """
    if current_price is None or stop_loss is None:
        return False
    return current_price <= stop_loss


def is_take_profit_triggered(
    current_price: Decimal | None,
    take_profit: Decimal | None
) -> bool:
    """Check if take-profit price has been triggered.

    Pure function - no side effects, easily testable.

    Args:
        current_price: Current market price (None if unknown)
        take_profit: Take-profit price level (None if not set)

    Returns:
        True if take-profit is triggered (price >= take_profit)
    """
    if current_price is None or take_profit is None:
        return False
    return current_price >= take_profit


def calculate_unrealized_pnl(
    current_price: Decimal,
    entry_price: Decimal,
    quantity: int
) -> Decimal:
    """Calculate unrealized P&L for a position.

    Pure function - no side effects, easily testable.

    Args:
        current_price: Current market price
        entry_price: Original entry price
        quantity: Number of shares (positive for long)

    Returns:
        Unrealized P&L (positive = profit, negative = loss)
    """
    return (current_price - entry_price) * quantity


@dataclass
class PositionManager:
    """Thread-safe position management."""

    _positions: dict[str, Position] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _on_stop_loss: Optional[Callable[[str], None]] = None
    _on_take_profit: Optional[Callable[[str], None]] = None

    def update_price(self, symbol: str, price: Decimal) -> None:
        """Thread-safe price update (called from monitor thread)."""
        callback_to_call = None
        callback_symbol = None

        with self._lock:
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.unrealized_pnl = calculate_unrealized_pnl(price, pos.entry_price, pos.quantity)

                # Determine callback (inside lock)
                if self.check_stop_loss(symbol) and self._on_stop_loss:
                    callback_to_call = self._on_stop_loss
                    callback_symbol = symbol
                elif self.check_take_profit(symbol) and self._on_take_profit:
                    callback_to_call = self._on_take_profit
                    callback_symbol = symbol

        # Execute callback (outside lock)
        if callback_to_call and callback_symbol:
            callback_to_call(callback_symbol)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Thread-safe position retrieval."""
        with self._lock:
            return self._positions.get(symbol)

    def get_all_positions(self) -> dict[str, Position]:
        """Thread-safe copy of all positions."""
        with self._lock:
            return dict(self._positions)

    def open_position(self, position: Position) -> None:
        """Thread-safe position creation."""
        with self._lock:
            if position.symbol in self._positions:
                raise ValueError(f"Position already exists for {position.symbol}")
            self._positions[position.symbol] = position
            logger.info(f"Opened position: {position.symbol} qty={position.quantity}")

    def close_position(self, symbol: str) -> Optional[Position]:
        """Thread-safe position removal."""
        with self._lock:
            pos = self._positions.pop(symbol, None)
            if pos:
                pos.status = PositionStatus.CLOSED
                pos.closed_at = datetime.now(timezone.utc)
                logger.info(f"Closed position: {symbol}")
            return pos

    def check_stop_loss(self, symbol: str) -> bool:
        """Thread-safe stop-loss check (call within lock or after get_position)."""
        pos = self._positions.get(symbol)
        if not pos:
            return False
        return is_stop_loss_triggered(pos.current_price, pos.stop_loss)

    def check_take_profit(self, symbol: str) -> bool:
        """Thread-safe take-profit check."""
        pos = self._positions.get(symbol)
        if not pos:
            return False
        return is_take_profit_triggered(pos.current_price, pos.take_profit)

    def set_callbacks(
        self,
        on_stop_loss: Optional[Callable[[str], None]] = None,
        on_take_profit: Optional[Callable[[str], None]] = None
    ) -> None:
        """Set callbacks for stop-loss and take-profit triggers."""
        with self._lock:
            self._on_stop_loss = on_stop_loss
            self._on_take_profit = on_take_profit

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        with self._lock:
            return len(self._positions)

    @property
    def symbols(self) -> list[str]:
        """List of symbols with open positions."""
        with self._lock:
            return list(self._positions.keys())

    def to_dict(self) -> dict:
        """Serialize positions for persistence."""
        with self._lock:
            return {
                symbol: {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "entry_price": str(pos.entry_price),
                    "current_price": str(pos.current_price) if pos.current_price else None,
                    "stop_loss": str(pos.stop_loss) if pos.stop_loss else None,
                    "take_profit": str(pos.take_profit) if pos.take_profit else None,
                    "status": pos.status.value,
                }
                for symbol, pos in self._positions.items()
            }
