"""Position monitor: exit signal detection for open positions.

Checks stop loss, take profit, trailing stop, and time-based exit
conditions.  Updates entry price and unrealized P&L on each check.
The trailing stop ratchets up monotonically (never decreases).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from stock_manager.trading.pipeline.state import PipelineEntry


class PositionMonitor:
    """Monitors open positions for exit signals.

    Supports four exit conditions checked in priority order:
        1. Stop loss (hard percentage floor).
        2. Take profit (target percentage ceiling).
        3. Trailing stop (ratcheting percentage from peak).
        4. Max holding period (time-based).

    Args:
        stop_loss_pct: Percentage drop from buy price to trigger stop loss (default 7%).
        take_profit_pct: Percentage gain from buy price to trigger take profit (default 20%).
        trailing_stop_pct: Percentage drop from trailing high to trigger exit (default 5%).
        max_holding_days: Maximum days to hold a position (default 90).
    """

    def __init__(
        self,
        stop_loss_pct: float = 0.07,
        take_profit_pct: float = 0.20,
        trailing_stop_pct: float = 0.05,
        max_holding_days: int = 90,
    ) -> None:
        self._stop_loss_pct = Decimal(str(stop_loss_pct))
        self._take_profit_pct = Decimal(str(take_profit_pct))
        self._trailing_stop_pct = Decimal(str(trailing_stop_pct))
        self._max_holding_days = max_holding_days

    def check(self, entry: PipelineEntry, current_price: Decimal) -> str | None:
        """Check an open position for exit signals.

        Evaluates exit conditions in priority order and returns the first
        triggered reason.  Also updates ``entry.current_price``,
        ``entry.unrealized_pnl``, and ``entry.trailing_stop`` on each call.

        The trailing stop is monotonically non-decreasing: it ratchets
        upward as the price rises but never moves down.

        Args:
            entry: Pipeline entry with an open position.
            current_price: Latest market price for the symbol.

        Returns:
            Exit reason string ("STOP_LOSS", "TAKE_PROFIT",
            "TRAILING_STOP", "MAX_HOLDING") or None if no exit signal.
        """
        if entry.buy_price is None or entry.buy_quantity is None:
            return None

        buy_price = entry.buy_price

        # Update current price and unrealized P&L
        entry.current_price = current_price
        entry.unrealized_pnl = (current_price - buy_price) * entry.buy_quantity

        # 1. Stop loss
        stop_loss_price = buy_price * (1 - self._stop_loss_pct)
        if current_price <= stop_loss_price:
            return "STOP_LOSS"

        # 2. Take profit
        take_profit_price = buy_price * (1 + self._take_profit_pct)
        if current_price >= take_profit_price:
            return "TAKE_PROFIT"

        # 3. Trailing stop: ratchet up, never down
        new_trailing = current_price * (1 - self._trailing_stop_pct)
        if entry.trailing_stop is None:
            entry.trailing_stop = new_trailing
        else:
            entry.trailing_stop = max(entry.trailing_stop, new_trailing)

        if current_price <= entry.trailing_stop:
            return "TRAILING_STOP"

        # 4. Time-based exit
        holding_days = (datetime.now() - entry.entered_at).days
        if holding_days >= self._max_holding_days:
            return "MAX_HOLDING"

        return None
