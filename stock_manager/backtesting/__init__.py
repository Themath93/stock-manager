"""Backtesting engine for the stock-manager trading bot.

Replays historical OHLCV data through the persona consensus pipeline
to evaluate trading system performance.
"""

from .config import BacktestConfig
from .data_loader import HistoricalBar, HistoricalDataLoader
from .engine import BacktestEngine, BacktestResult
from .metrics import PerformanceMetrics, compute_metrics
from .portfolio import Position, SimulatedPortfolio, Trade
from .report import generate_json_report, generate_summary
from .snapshot_builder import build_snapshot_from_bars

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "HistoricalBar",
    "HistoricalDataLoader",
    "PerformanceMetrics",
    "Position",
    "SimulatedPortfolio",
    "Trade",
    "build_snapshot_from_bars",
    "compute_metrics",
    "generate_json_report",
    "generate_summary",
]
