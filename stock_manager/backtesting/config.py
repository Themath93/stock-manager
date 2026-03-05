"""Backtesting configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a backtest run."""

    symbols: list[str]
    start_date: date
    end_date: date
    initial_capital: Decimal = Decimal("100000000")  # 1억 원
    commission_rate: Decimal = Decimal("0.00015")  # 0.015% (Korean stock commission)
    slippage_pct: Decimal = Decimal("0.001")  # 0.1% slippage
    max_positions: int = 10
    position_size_pct: float = 10.0  # Max 10% per position
    rebalance_interval_days: int = 5  # Re-evaluate every 5 trading days
