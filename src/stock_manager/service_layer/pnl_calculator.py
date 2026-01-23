"""
PnL Calculator

Calculates realized and unrealized profit and loss for positions.
Implements WH-003: Position PnL Calculation.
"""

import logging
from decimal import Decimal
from typing import Optional

from ..domain.worker import PositionSnapshot

logger = logging.getLogger(__name__)


class PnLCalculator:
    """PnL Calculator

    Calculates realized and unrealized PnL for positions.
    """

    def __init__(self):
        """Initialize PnL Calculator"""
        pass

    def calculate_unrealized_pnl(
        self,
        position_qty: Decimal,
        avg_price: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """Calculate unrealized PnL for an open position

        Args:
            position_qty: Position quantity (positive for long, negative for short)
            avg_price: Average entry price
            current_price: Current market price

        Returns:
            Decimal: Unrealized PnL

        Example:
            Long position: qty=100, avg_price=1000, current_price=1050
            Unrealized PnL = (1050 - 1000) * 100 = 5000

            Short position: qty=-100, avg_price=1000, current_price=950
            Unrealized PnL = (950 - 1000) * (-100) = 5000
        """
        return (current_price - avg_price) * position_qty

    def calculate_realized_pnl(
        self,
        entry_price: Decimal,
        exit_price: Decimal,
        qty: Decimal,
    ) -> Decimal:
        """Calculate realized PnL for a closed position

        Args:
            entry_price: Entry price
            exit_price: Exit price
            qty: Quantity traded

        Returns:
            Decimal: Realized PnL

        Example:
            Long trade: entry_price=1000, exit_price=1050, qty=100
            Realized PnL = (1050 - 1000) * 100 = 5000

            Short trade: entry_price=1000, exit_price=950, qty=100
            Realized PnL = (1000 - 950) * 100 = 5000
        """
        return (exit_price - entry_price) * qty

    def calculate_total_pnl(
        self,
        unrealized_pnl: Decimal,
        realized_pnl: Decimal,
    ) -> Decimal:
        """Calculate total PnL (realized + unrealized)

        Args:
            unrealized_pnl: Unrealized PnL from open positions
            realized_pnl: Realized PnL from closed positions

        Returns:
            Decimal: Total PnL
        """
        return unrealized_pnl + realized_pnl

    def calculate_win_rate(
        self,
        winning_trades: int,
        losing_trades: int,
    ) -> Decimal:
        """Calculate win rate

        Args:
            winning_trades: Number of winning trades
            losing_trades: Number of losing trades

        Returns:
            Decimal: Win rate (0-1)

        Example:
            winning_trades=7, losing_trades=3
            Win rate = 7 / (7 + 3) = 0.7 (70%)
        """
        total_trades = winning_trades + losing_trades
        if total_trades == 0:
            return Decimal("0")

        return Decimal(winning_trades) / Decimal(total_trades)

    def calculate_profit_factor(
        self,
        gross_profit: Decimal,
        gross_loss: Decimal,
    ) -> Decimal:
        """Calculate profit factor

        Args:
            gross_profit: Total gross profit from winning trades
            gross_loss: Total gross loss from losing trades (absolute value)

        Returns:
            Decimal: Profit factor

        Note:
            Profit factor > 1: Profitable
            Profit factor = 1: Breakeven
            Profit factor < 1: Losing
            Returns 999.99 when gross_loss = 0 and gross_profit > 0

        Example:
            gross_profit=5000, gross_loss=3000
            Profit factor = 5000 / 3000 = 1.67
        """
        if gross_loss == Decimal("0"):
            if gross_profit == Decimal("0"):
                return Decimal("0")
            return Decimal("999.99")

        return gross_profit / abs(gross_loss)

    def calculate_max_drawdown(
        self,
        equity_curve: list[Decimal],
    ) -> Decimal:
        """Calculate maximum drawdown from equity curve

        Args:
            equity_curve: List of equity values over time

        Returns:
            Decimal: Maximum drawdown (as positive value)

        Example:
            equity_curve = [10000, 12000, 11000, 9000, 10000]
            Peak = 12000
            Trough = 9000
            Max Drawdown = (12000 - 9000) / 12000 = 0.25 (25%)
        """
        if not equity_curve or len(equity_curve) < 2:
            return Decimal("0")

        peak = equity_curve[0]
        max_drawdown = Decimal("0")

        for equity in equity_curve:
            # Update peak
            if equity > peak:
                peak = equity

            # Calculate drawdown
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown
