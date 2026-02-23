"""Buy specialist: position sizing and buy execution.

Calculates position size based on available capital and max position
percentage, respects maximum open position limits, and updates the
PipelineEntry with buy price and quantity on success.
"""

from __future__ import annotations

import threading
from decimal import Decimal

from stock_manager.trading.pipeline.state import PipelineEntry


class BuySpecialist:
    """Handles buy order execution with position sizing constraints.

    Args:
        max_positions: Maximum number of simultaneous open positions.
        max_position_pct: Maximum fraction of available capital per position (0.0-1.0).
    """

    def __init__(
        self,
        max_positions: int = 10,
        max_position_pct: float = 0.1,
    ) -> None:
        self._max_positions = max_positions
        self._max_position_pct = max_position_pct
        self._open_positions: int = 0
        self._lock = threading.RLock()

    @property
    def open_positions(self) -> int:
        """Current number of open positions."""
        with self._lock:
            return self._open_positions

    def execute(
        self,
        entry: PipelineEntry,
        current_price: Decimal,
        available_capital: Decimal,
    ) -> bool:
        """Execute a buy order for the given pipeline entry.

        Steps:
            1. Check max_positions limit.
            2. Calculate quantity via ``calculate_quantity()``.
            3. Update ``entry.buy_price`` and ``entry.buy_quantity``.
            4. Increment open position counter.

        Args:
            entry: Pipeline entry to buy.
            current_price: Current market price per share.
            available_capital: Total available capital for trading.

        Returns:
            True if the buy was executed successfully, False otherwise.
        """
        with self._lock:
            if self._open_positions >= self._max_positions:
                return False

            quantity = self.calculate_quantity(current_price, available_capital)
            if quantity <= 0:
                return False

            entry.buy_price = current_price
            entry.buy_quantity = quantity
            entry.current_price = current_price
            self._open_positions += 1
            return True

    def calculate_quantity(
        self,
        current_price: Decimal,
        available_capital: Decimal,
    ) -> int:
        """Calculate position size respecting the max position percentage.

        The budget for a single position is ``available_capital * max_position_pct``.
        The quantity is the whole number of shares that fit within that budget.

        Args:
            current_price: Current market price per share.
            available_capital: Total available capital for trading.

        Returns:
            Number of whole shares to buy (0 if price is invalid).
        """
        if current_price <= 0:
            return 0
        position_budget = available_capital * Decimal(str(self._max_position_pct))
        return int(position_budget / current_price)

    def release_position(self) -> None:
        """Decrement the open position counter after a sell.

        Should be called when a position is closed (SOLD state).
        """
        with self._lock:
            if self._open_positions > 0:
                self._open_positions -= 1
