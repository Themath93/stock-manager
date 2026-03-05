"""Backtest report generation."""

from __future__ import annotations

import json
from dataclasses import asdict

from .metrics import PerformanceMetrics
from .portfolio import Trade


def generate_json_report(metrics: PerformanceMetrics, trades: list[Trade]) -> str:
    """Generate JSON report from backtest results."""
    trade_records = []
    for t in trades:
        trade_records.append(
            {
                "symbol": t.symbol,
                "quantity": t.quantity,
                "entry_price": str(t.entry_price),
                "exit_price": str(t.exit_price),
                "entry_date": str(t.entry_date),
                "exit_date": str(t.exit_date),
                "pnl": str(t.pnl),
                "return_pct": round(t.return_pct, 2),
            }
        )

    report = {
        "metrics": asdict(metrics),
        "trades": trade_records,
        "trade_count": len(trade_records),
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


def generate_summary(metrics: PerformanceMetrics) -> str:
    """Generate human-readable summary."""
    lines = [
        "=== Backtest Results ===",
        f"Total Return: {metrics.total_return_pct:.2f}%",
        f"Annualized Return: {metrics.annualized_return_pct:.2f}%",
        f"Max Drawdown: {metrics.max_drawdown_pct:.2f}%",
        f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
        f"Win Rate: {metrics.win_rate:.1f}%",
        f"Profit Factor: {metrics.profit_factor:.2f}",
        f"Total Trades: {metrics.total_trades}",
        f"Avg Trade Return: {metrics.avg_trade_return_pct:.2f}%",
        f"Max Consecutive Losses: {metrics.max_consecutive_losses}",
    ]
    return "\n".join(lines)
