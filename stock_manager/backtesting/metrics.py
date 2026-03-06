"""Performance metrics calculation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PerformanceMetrics:
    """Computed performance metrics for a backtest run."""

    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return_pct: float
    max_consecutive_losses: int


def compute_metrics(
    equity_curve: list[tuple[date, Decimal]],
    trades: list,  # Trade objects
    trading_days: int = 252,
) -> PerformanceMetrics:
    """Compute performance metrics from equity curve and trades."""
    if not equity_curve or len(equity_curve) < 2:
        return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    initial = float(equity_curve[0][1])
    final = float(equity_curve[-1][1])

    if initial <= 0:
        return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    total_return = (final - initial) / initial * 100

    # Annualized return
    days = (equity_curve[-1][0] - equity_curve[0][0]).days
    years = max(days / 365.25, 0.01)
    ann_return = ((final / initial) ** (1 / years) - 1) * 100 if final > 0 else 0

    # Max drawdown
    peak = float(equity_curve[0][1])
    max_dd = 0.0
    for _, val in equity_curve:
        v = float(val)
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Daily returns for Sharpe
    daily_returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = float(equity_curve[i - 1][1])
        curr = float(equity_curve[i][1])
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    sharpe = 0.0
    if daily_returns:
        avg_r = sum(daily_returns) / len(daily_returns)
        std_r = math.sqrt(
            sum((r - avg_r) ** 2 for r in daily_returns)
            / max(len(daily_returns) - 1, 1)
        )
        if std_r > 0:
            sharpe = round((avg_r / std_r) * math.sqrt(trading_days), 2)

    # Trade stats
    total_trades = len(trades)
    wins = sum(1 for t in trades if float(t.pnl) > 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    gross_profit = sum(float(t.pnl) for t in trades if float(t.pnl) > 0)
    gross_loss = abs(sum(float(t.pnl) for t in trades if float(t.pnl) < 0))
    profit_factor = (
        (gross_profit / gross_loss)
        if gross_loss > 0
        else float("inf") if gross_profit > 0 else 0
    )

    avg_return = (
        sum(t.return_pct for t in trades) / total_trades if total_trades > 0 else 0
    )

    # Max consecutive losses
    max_consec = 0
    consec = 0
    for t in trades:
        if float(t.pnl) < 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    return PerformanceMetrics(
        total_return_pct=round(total_return, 2),
        annualized_return_pct=round(ann_return, 2),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=sharpe,
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        total_trades=total_trades,
        avg_trade_return_pct=round(avg_return, 2),
        max_consecutive_losses=max_consec,
    )
