"""Build MarketSnapshot from historical data for persona evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from stock_manager.trading.personas.models import MarketSnapshot

from .data_loader import HistoricalBar


def build_snapshot_from_bars(
    symbol: str,
    bars: list[HistoricalBar],
    current_bar_index: int,
) -> MarketSnapshot:
    """Build a MarketSnapshot from historical bars at a given point in time.

    Uses bars up to current_bar_index to compute moving averages, RSI, etc.
    This provides a realistic snapshot as if we were trading on that date.
    """
    if not bars or current_bar_index < 0 or current_bar_index >= len(bars):
        return MarketSnapshot()

    current = bars[current_bar_index]
    lookback = bars[max(0, current_bar_index - 199) : current_bar_index + 1]

    closes = [float(b.close) for b in lookback]
    volumes = [b.volume for b in lookback]

    # Simple moving averages
    sma_20 = sum(closes[-20:]) / min(20, len(closes)) if closes else 0.0
    sma_50 = sum(closes[-50:]) / min(50, len(closes)) if closes else 0.0
    sma_200 = sum(closes) / len(closes) if closes else 0.0

    # RSI-14 (simplified)
    rsi = _compute_rsi(closes, 14)

    # Average volume 20d
    avg_vol = (
        sum(volumes[-20:]) // max(min(20, len(volumes)), 1) if volumes else 0
    )

    # 52-week high/low (approx 250 trading days)
    lookback_52w = bars[max(0, current_bar_index - 249) : current_bar_index + 1]
    highs_52w = [b.high for b in lookback_52w]
    lows_52w = [b.low for b in lookback_52w]

    prev_close = (
        bars[current_bar_index - 1].close if current_bar_index > 0 else current.open
    )

    return MarketSnapshot(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        current_price=current.close,
        open_price=current.open,
        high_price=current.high,
        low_price=current.low,
        prev_close=prev_close,
        volume=current.volume,
        avg_volume_20d=avg_vol,
        sma_20=sma_20,
        sma_50=sma_50,
        sma_200=sma_200,
        rsi_14=rsi,
        price_52w_high=max(highs_52w) if highs_52w else Decimal("0"),
        price_52w_low=min(lows_52w) if lows_52w else Decimal("0"),
    )


def _compute_rsi(closes: list[float], period: int = 14) -> float:
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral default

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    if len(gains) < period:
        return 50.0

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)
