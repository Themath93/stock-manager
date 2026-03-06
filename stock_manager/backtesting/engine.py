"""Core backtest engine."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from .config import BacktestConfig
from .data_loader import HistoricalDataLoader
from .metrics import PerformanceMetrics, compute_metrics
from .portfolio import SimulatedPortfolio
from .snapshot_builder import build_snapshot_from_bars

logger = logging.getLogger(__name__)


class BacktestResult:
    """Result of a backtest run."""

    def __init__(
        self,
        config: BacktestConfig,
        portfolio: SimulatedPortfolio,
        metrics: PerformanceMetrics,
    ) -> None:
        self.config = config
        self.portfolio = portfolio
        self.metrics = metrics


class BacktestEngine:
    """Runs backtests by replaying historical data through personas.

    Usage:
        loader = HistoricalDataLoader()
        loader.load_from_records("005930", records)
        engine = BacktestEngine(loader, personas)
        result = engine.run(config)
    """

    def __init__(
        self, data_loader: HistoricalDataLoader, personas: list | None = None
    ) -> None:
        self._loader = data_loader
        self._personas = personas or []

    def run(self, config: BacktestConfig) -> BacktestResult:
        """Run backtest with given configuration."""
        portfolio = SimulatedPortfolio(config.initial_capital, config.commission_rate)

        # Get all trading dates across all symbols
        all_dates: set[date] = set()
        symbol_bars: dict[str, list] = {}
        for symbol in config.symbols:
            bars = self._loader.get_bars(symbol, config.start_date, config.end_date)
            if bars:
                symbol_bars[symbol] = bars
                for b in bars:
                    all_dates.add(b.date)

        if not all_dates:
            metrics = compute_metrics([], [])
            return BacktestResult(config, portfolio, metrics)

        sorted_dates = sorted(all_dates)
        day_count = 0

        for current_date in sorted_dates:
            day_count += 1
            current_prices: dict[str, Decimal] = {}

            # Get current prices
            for symbol, bars in symbol_bars.items():
                bar = next((b for b in bars if b.date == current_date), None)
                if bar:
                    current_prices[symbol] = bar.close

            # Check exits for existing positions
            for symbol in list(portfolio.positions.keys()):
                if symbol in current_prices:
                    pos = portfolio.positions[symbol]
                    price = current_prices[symbol]
                    # Simple exit: 7% stop-loss or 15% take-profit
                    change_pct = float(
                        (price - pos.entry_price) / pos.entry_price * 100
                    )
                    if change_pct <= -7.0 or change_pct >= 15.0:
                        portfolio.sell(symbol, price, current_date)

            # Evaluate new entries on rebalance days
            if day_count % config.rebalance_interval_days == 0:
                for symbol, bars in symbol_bars.items():
                    if symbol in portfolio.positions:
                        continue
                    if portfolio.position_count >= config.max_positions:
                        break

                    # Find current bar index
                    bar_idx = next(
                        (i for i, b in enumerate(bars) if b.date == current_date),
                        None,
                    )
                    if bar_idx is None or bar_idx < 20:
                        continue

                    # Build snapshot and evaluate
                    snapshot = build_snapshot_from_bars(symbol, bars, bar_idx)
                    buy_votes = 0
                    for persona in self._personas:
                        try:
                            vote = persona.screen_rule(snapshot)
                            if vote.action.value == "buy":
                                buy_votes += 1
                        except Exception:
                            pass

                    # Simple threshold: majority buy
                    if (
                        len(self._personas) > 0
                        and buy_votes > len(self._personas) // 2
                    ):
                        price = current_prices[symbol]
                        max_value = portfolio.cash * Decimal(
                            str(config.position_size_pct / 100)
                        )
                        quantity = int(max_value / price) if price > 0 else 0
                        if quantity > 0:
                            portfolio.buy(symbol, quantity, price, current_date)

            portfolio.record_equity(current_date, current_prices)

        metrics = compute_metrics(portfolio.equity_curve, portfolio.trades)
        return BacktestResult(config, portfolio, metrics)
