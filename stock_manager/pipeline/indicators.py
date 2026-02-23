"""
Technical indicator calculation engine for stock-manager.

Pure-Python implementation with zero third-party dependencies.
All functions operate on plain Python lists of floats, making them
compatible with data from the KIS API inquire_period_price endpoint.

Indicators implemented:
- SMA (Simple Moving Average): 5, 10, 20, 60, 120, 200-day
- EMA (Exponential Moving Average): standard EMA and Wilder EMA
- RSI (Relative Strength Index): 14-day, Wilder smoothing
- MACD: (12, 26, 9) with signal line and histogram
- Bollinger Bands: (20, 2σ) with %B and bandwidth

Data pipeline:
- Input:  list of closing prices (float), ordered oldest → newest
- Output: list of float | None (None = insufficient data for the period)

KIS API note:
    inquire_period_price returns up to 100 bars per request.
    Fetch 3 pages (300 bars) to ensure SMA-200 has valid data.
    Field mapping: output[i]['stck_clpr'] → close price

Benchmarks (pure Python, 250 bars, 10 symbols):
    All indicators combined: ~6ms total
    Per symbol:              ~0.6ms
    Memory for 10 symbols:  ~600 KB
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple


# ─── Type aliases ─────────────────────────────────────────────────────────────

PriceSeries = list[float]
"""Closing prices ordered oldest → newest."""

IndicatorSeries = list[float | None]
"""Indicator values; None indicates insufficient data for that bar."""


@dataclass(frozen=True)
class OHLCVBar:
    """Single OHLCV bar (Open, High, Low, Close, Volume).

    Attributes:
        date:   Trading date string (e.g. "20240115").
        open:   Opening price.
        high:   High price.
        low:    Low price.
        close:  Closing price.
        volume: Accumulated trading volume.
    """

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


OHLCVSeries = list[OHLCVBar]
"""OHLCV bars ordered oldest → newest."""


# ─── Minimum data requirements (bars needed for first valid value) ─────────────

MIN_BARS: dict[str, int] = {
    "sma5": 5,
    "sma10": 10,
    "sma20": 20,
    "sma60": 60,
    "sma120": 120,
    "sma200": 200,
    "ema12": 12,
    "ema26": 26,
    "rsi14": 15,  # period + 1
    "macd": 34,  # slow(26) + signal(9) - 1
    "bb20": 20,
}


# ─── Result dataclasses ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class MACDResult:
    """MACD calculation result.

    Attributes:
        macd:      MACD line = EMA(fast) - EMA(slow)
        signal:    Signal line = EMA(signal_period) of MACD
        histogram: MACD - Signal (positive = bullish momentum)
    """

    macd: IndicatorSeries
    signal: IndicatorSeries
    histogram: IndicatorSeries


@dataclass(frozen=True)
class BollingerBandsResult:
    """Bollinger Bands calculation result.

    Attributes:
        upper:     Upper band = middle + num_std * σ
        middle:    Middle band = SMA(period)
        lower:     Lower band = middle - num_std * σ
        pct_b:     %B = (price - lower) / (upper - lower)
                   0 = at lower band, 1 = at upper band
        bandwidth: Band width = (upper - lower) / middle * 100  [%]
    """

    upper: IndicatorSeries
    middle: IndicatorSeries
    lower: IndicatorSeries
    pct_b: IndicatorSeries
    bandwidth: IndicatorSeries


@dataclass(frozen=True)
class MovingAveragesResult:
    """All SMA/EMA results for a price series.

    Attributes:
        sma5, sma10, sma20, sma60, sma120, sma200: Simple MAs
        ema12, ema26: Exponential MAs (used by MACD)
    """

    sma5: IndicatorSeries
    sma10: IndicatorSeries
    sma20: IndicatorSeries
    sma60: IndicatorSeries
    sma120: IndicatorSeries
    sma200: IndicatorSeries
    ema12: IndicatorSeries
    ema26: IndicatorSeries


class CrossoverEvent(NamedTuple):
    """A moving average crossover event.

    Attributes:
        index:    Bar index where the crossover occurred.
        type:     "golden_cross" (fast > slow) or "dead_cross" (fast < slow).
        price:    Closing price at crossover bar.
        fast_ma:  Fast MA value at crossover.
        slow_ma:  Slow MA value at crossover.
    """

    index: int
    type: str
    price: float
    fast_ma: float
    slow_ma: float


@dataclass
class IndicatorSnapshot:
    """Latest indicator values for a single symbol (most recent bar).

    Used as the output of IndicatorCache and compute_snapshot().
    All float fields are None if insufficient price data is available.

    Attributes:
        symbol:       Stock symbol (e.g. "005930").
        as_of:        Timestamp when snapshot was computed.
        sma5..sma200: Simple moving averages.
        ema12, ema26: Exponential moving averages.
        rsi14:        RSI value (0–100). >70 = overbought, <30 = oversold.
        macd_line:    MACD line value.
        macd_signal:  MACD signal line value.
        macd_hist:    MACD histogram (MACD - Signal). Positive = bullish.
        bb_upper:     Bollinger upper band.
        bb_middle:    Bollinger middle band (SMA-20).
        bb_lower:     Bollinger lower band.
        bb_pct_b:     %B position within bands (0=lower, 1=upper).
        bb_bandwidth: Band width as % of middle (low = squeeze condition).
        is_overbought: RSI > 70.
        is_oversold:   RSI < 30.
        macd_bullish:  MACD histogram > 0.
        bb_squeeze:    Bandwidth < 2.0% (low volatility, breakout likely).
    """

    symbol: str
    as_of: datetime = field(default_factory=datetime.now)

    # Moving averages
    sma5: float | None = None
    sma10: float | None = None
    sma20: float | None = None
    sma60: float | None = None
    sma120: float | None = None
    sma200: float | None = None
    ema12: float | None = None
    ema26: float | None = None

    # RSI
    rsi14: float | None = None

    # MACD
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None

    # Bollinger Bands
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_pct_b: float | None = None
    bb_bandwidth: float | None = None

    # Derived signals (pre-computed for fast strategy evaluation)
    is_overbought: bool = False
    is_oversold: bool = False
    macd_bullish: bool = False
    bb_squeeze: bool = False

    # OHLCV-based indicators (Phase 0 extension, all optional for backward compat)
    atr14: float | None = None
    adx14: float | None = None
    obv_val: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    volume_ratio_val: float | None = None
    is_trending: bool | None = None        # True when ADX > 25
    is_high_volume: bool | None = None     # True when volume_ratio > 1.5


# ─── Core calculation functions ───────────────────────────────────────────────


def sma(prices: PriceSeries, period: int) -> IndicatorSeries:
    """Simple Moving Average.

    Computes the arithmetic mean of `period` consecutive closing prices.

    Args:
        prices: Closing prices ordered oldest → newest.
        period: Lookback window (e.g. 20 for SMA-20).

    Returns:
        List of length len(prices). Values before index (period-1)
        are None due to insufficient data.

    Raises:
        ValueError: If period <= 0.

    Examples:
        >>> sma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        [None, None, 2.0, 3.0, 4.0]
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(prices)
    result: IndicatorSeries = [None] * n
    for i in range(period - 1, n):
        result[i] = sum(prices[i - period + 1 : i + 1]) / period
    return result


def ema(prices: PriceSeries, period: int) -> IndicatorSeries:
    """Exponential Moving Average (standard, alpha = 2 / (period + 1)).

    Weights recent prices more heavily than older prices.
    The initial EMA is seeded with the SMA of the first `period` bars,
    matching the convention used by TradingView and Bloomberg.

    Args:
        prices: Closing prices ordered oldest → newest.
        period: EMA period.

    Returns:
        List of length len(prices). Values before index (period-1)
        are None.

    Raises:
        ValueError: If period <= 0.

    Notes:
        alpha = 2/(period+1).  For period=12: alpha=0.1538.
        Wilder's EMA uses alpha=1/period (slower); see rsi() internals.

    Examples:
        >>> vals = ema([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3)
        >>> vals[2]  # first valid = SMA seed = (1+2+3)/3
        2.0
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(prices)
    if n < period:
        return [None] * n

    result: IndicatorSeries = [None] * n
    k = 2.0 / (period + 1)

    # Seed: SMA of first `period` values
    seed = sum(prices[:period]) / period
    result[period - 1] = seed

    for i in range(period, n):
        prev = result[i - 1]
        if prev is not None:
            result[i] = prices[i] * k + prev * (1.0 - k)

    return result


def rsi(prices: PriceSeries, period: int = 14) -> IndicatorSeries:
    """RSI using Wilder's smoothing method (industry standard).

    Wilder's RSI differs from a simple RSI in its smoothing:
    - Wilder uses alpha = 1/period  (e.g. 1/14 = 0.0714 for RSI-14)
    - Standard EMA uses alpha = 2/(period+1) = 0.1333 for period=14
    - Wilder's reacts more slowly, reducing false signals

    Algorithm:
        1. Compute daily price changes (delta = close[i] - close[i-1]).
        2. Split into gains (delta > 0) and losses (|delta| when delta < 0).
        3. Seed avg_gain / avg_loss with SMA of first `period` values.
        4. Wilder smoothing: avg = prev * (1 - 1/period) + current * (1/period)
        5. RSI = 100 - 100 / (1 + avg_gain / avg_loss)

    Minimum data required: period + 1 bars.

    Args:
        prices: Closing prices ordered oldest → newest.
        period: RSI period (default 14).

    Returns:
        List of length len(prices). Valid from index `period` onward.
        All values are in [0, 100].

    Raises:
        ValueError: If period <= 0.

    Examples:
        >>> values = rsi(close_prices, 14)
        >>> latest = values[-1]
        >>> if latest is not None:
        ...     signal = "overbought" if latest > 70 else "oversold" if latest < 30 else "neutral"
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(prices)
    if n < period + 1:
        return [None] * n

    result: IndicatorSeries = [None] * n

    # Price deltas (deltas[i] = prices[i+1] - prices[i])
    deltas = [prices[i] - prices[i - 1] for i in range(1, n)]
    gains = [max(d, 0.0) for d in deltas]
    losses = [abs(min(d, 0.0)) for d in deltas]

    # Wilder seed: SMA of first `period` gains/losses
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _calc_rsi(ag: float, al: float) -> float:
        if al == 0.0:
            return 100.0
        if ag == 0.0:
            return 0.0
        return 100.0 - (100.0 / (1.0 + ag / al))

    result[period] = _calc_rsi(avg_gain, avg_loss)

    # Wilder's alpha = 1/period (NOT 2/(period+1))
    alpha = 1.0 / period

    for i in range(period + 1, n):
        delta_idx = i - 1  # deltas[delta_idx] = prices[i] - prices[i-1]
        avg_gain = avg_gain * (1.0 - alpha) + gains[delta_idx] * alpha
        avg_loss = avg_loss * (1.0 - alpha) + losses[delta_idx] * alpha
        result[i] = _calc_rsi(avg_gain, avg_loss)

    return result


def macd(
    prices: PriceSeries,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDResult:
    """MACD (Moving Average Convergence/Divergence).

    Components:
        MACD Line   = EMA(fast_period) - EMA(slow_period)
        Signal Line = EMA(signal_period) of MACD Line
        Histogram   = MACD Line - Signal Line

    Minimum data required: slow_period + signal_period - 1 = 34 bars
    (with defaults fast=12, slow=26, signal=9).

    Args:
        prices:        Closing prices ordered oldest → newest.
        fast_period:   Fast EMA period (default 12).
        slow_period:   Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).

    Returns:
        MACDResult with macd, signal, histogram series.

    Trading signals:
        Buy:  histogram crosses negative → positive (MACD crosses above Signal)
        Sell: histogram crosses positive → negative (MACD crosses below Signal)

    Examples:
        >>> result = macd(close_prices)
        >>> if result.histogram[-1] is not None and result.histogram[-1] > 0:
        ...     print("Bullish MACD momentum")
    """
    n = len(prices)
    ema_fast = ema(prices, fast_period)
    ema_slow = ema(prices, slow_period)

    # MACD Line: valid wherever both EMAs are valid (from index slow_period-1)
    macd_line: IndicatorSeries = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]

    # Collect contiguous valid MACD values for signal EMA calculation
    macd_start: int | None = None
    valid_macd_vals: list[float] = []
    for i in range(n):
        if macd_line[i] is not None:
            if macd_start is None:
                macd_start = i
            valid_macd_vals.append(macd_line[i])  # type: ignore[arg-type]

    signal_line: IndicatorSeries = [None] * n
    histogram: IndicatorSeries = [None] * n

    if macd_start is not None and len(valid_macd_vals) >= signal_period:
        sig_vals = ema(valid_macd_vals, signal_period)
        for j, sig_val in enumerate(sig_vals):
            global_idx = macd_start + j
            if sig_val is not None and global_idx < n:
                signal_line[global_idx] = sig_val
                if macd_line[global_idx] is not None:
                    histogram[global_idx] = macd_line[global_idx] - sig_val  # type: ignore[operator]

    return MACDResult(macd=macd_line, signal=signal_line, histogram=histogram)


def bollinger_bands(
    prices: PriceSeries,
    period: int = 20,
    num_std: float = 2.0,
) -> BollingerBandsResult:
    """Bollinger Bands with %B and Bandwidth.

    Formula:
        Middle Band = SMA(period)
        Upper Band  = Middle + num_std * σ
        Lower Band  = Middle - num_std * σ
        %B          = (price - lower) / (upper - lower)
        Bandwidth   = (upper - lower) / middle * 100  [%]

    Uses POPULATION standard deviation (ddof=0), matching TradingView
    and Bloomberg. Pandas uses ddof=1 by default — this would give
    slightly wider bands.

    Args:
        prices:  Closing prices ordered oldest → newest.
        period:  Moving average period (default 20).
        num_std: Standard deviation multiplier (default 2.0).

    Returns:
        BollingerBandsResult with all band series.

    Raises:
        ValueError: If period <= 0.

    Interpretation:
        %B < 0:       Price below lower band (potential reversal up)
        %B > 1:       Price above upper band (potential reversal down)
        Bandwidth < 2%: Squeeze — low volatility, breakout likely

    Statistical property:
        With 2σ bands, ~95.4% of prices should fall within the bands
        (assuming normal distribution). Observed 4–5% outside is normal.

    Examples:
        >>> bb = bollinger_bands(close_prices)
        >>> if bb.pct_b[-1] is not None and bb.pct_b[-1] < 0:
        ...     print("Price below lower band — potential reversal")
        >>> if bb.bandwidth[-1] is not None and bb.bandwidth[-1] < 2.0:
        ...     print("Bollinger squeeze — watch for breakout")
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(prices)
    upper_vals: IndicatorSeries = [None] * n
    middle_vals: IndicatorSeries = [None] * n
    lower_vals: IndicatorSeries = [None] * n
    pct_b_vals: IndicatorSeries = [None] * n
    bwidth_vals: IndicatorSeries = [None] * n

    for i in range(period - 1, n):
        window = prices[i - period + 1 : i + 1]
        mid = sum(window) / period

        # Population std (ddof=0)
        variance = sum((x - mid) ** 2 for x in window) / period
        std = math.sqrt(variance)

        up = mid + num_std * std
        low = mid - num_std * std

        middle_vals[i] = mid
        upper_vals[i] = up
        lower_vals[i] = low

        band_width = up - low
        if band_width > 0.0:
            pct_b_vals[i] = (prices[i] - low) / band_width
        bwidth_vals[i] = (band_width / mid * 100.0) if mid > 0.0 else None

    return BollingerBandsResult(
        upper=upper_vals,
        middle=middle_vals,
        lower=lower_vals,
        pct_b=pct_b_vals,
        bandwidth=bwidth_vals,
    )


def moving_averages(prices: PriceSeries) -> MovingAveragesResult:
    """Compute all standard SMA and EMA series in one call.

    SMA periods: 5, 10, 20, 60, 120, 200
    EMA periods: 12, 26

    Args:
        prices: Closing prices ordered oldest → newest.
                At least 200 bars recommended for SMA-200.

    Returns:
        MovingAveragesResult with all series.

    Notes:
        With 250 bars: SMA-200 has 51 valid values (bars 199–249).
        With 300 bars: SMA-200 has 101 valid values.
    """
    return MovingAveragesResult(
        sma5=sma(prices, 5),
        sma10=sma(prices, 10),
        sma20=sma(prices, 20),
        sma60=sma(prices, 60),
        sma120=sma(prices, 120),
        sma200=sma(prices, 200),
        ema12=ema(prices, 12),
        ema26=ema(prices, 26),
    )


def detect_crossovers(
    prices: PriceSeries,
    fast_period: int,
    slow_period: int,
    use_ema: bool = False,
) -> list[CrossoverEvent]:
    """Detect Golden Cross and Dead Cross events.

    A Golden Cross occurs when the fast MA crosses above the slow MA,
    indicating bullish momentum. A Dead Cross is the reverse.

    Args:
        prices:      Closing prices ordered oldest → newest.
        fast_period: Fast MA period (e.g. 5 or 20).
        slow_period: Slow MA period (e.g. 20 or 60).
        use_ema:     Use EMA instead of SMA (default False).

    Returns:
        List of CrossoverEvent ordered by occurrence index.

    Common configurations:
        SMA-5  / SMA-20:  Short-term momentum signal
        SMA-20 / SMA-60:  Medium-term trend confirmation
        SMA-50 / SMA-200: Classic golden/death cross (long-term)

    Examples:
        >>> events = detect_crossovers(closes, 5, 20)
        >>> if events and events[-1].type == "golden_cross":
        ...     print(f"Golden cross at bar {events[-1].index}")
    """
    calc = ema if use_ema else sma
    fast_ma = calc(prices, fast_period)
    slow_ma = calc(prices, slow_period)

    events: list[CrossoverEvent] = []
    prev_diff: float | None = None

    for i in range(len(prices)):
        f, s = fast_ma[i], slow_ma[i]
        if f is None or s is None:
            continue
        diff = f - s
        if prev_diff is not None:
            if prev_diff <= 0.0 and diff > 0.0:
                events.append(CrossoverEvent(i, "golden_cross", prices[i], f, s))
            elif prev_diff >= 0.0 and diff < 0.0:
                events.append(CrossoverEvent(i, "dead_cross", prices[i], f, s))
        prev_diff = diff

    return events


# ─── OHLCV-based indicators ──────────────────────────────────────────────────


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> IndicatorSeries:
    """Average True Range using Wilder's smoothing.

    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    ATR = Wilder's smoothed average of TR over `period` bars.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(closes)
    if n < 2 or len(highs) != n or len(lows) != n:
        return [None] * n

    result: IndicatorSeries = [None] * n
    # True Range series
    tr_vals: list[float] = [highs[0] - lows[0]]  # First bar: high - low
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_vals.append(max(hl, hc, lc))

    if n < period:
        return result

    # Seed: SMA of first `period` TRs
    atr_val = sum(tr_vals[:period]) / period
    result[period - 1] = atr_val

    # Wilder smoothing: ATR = prev * (period-1)/period + TR/period
    for i in range(period, n):
        atr_val = (atr_val * (period - 1) + tr_vals[i]) / period
        result[i] = atr_val

    return result


def adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> IndicatorSeries:
    """Average Directional Index (ADX).

    Measures trend strength regardless of direction.
    ADX > 25 = trending, ADX < 20 = ranging.
    Uses Wilder's smoothing for DI+, DI-, and ADX.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(closes)
    if n < period * 2 or len(highs) != n or len(lows) != n:
        return [None] * n

    result: IndicatorSeries = [None] * n

    # Directional Movement
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    # True Range for ATR
    tr_vals: list[float] = [highs[0] - lows[0]]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_vals.append(max(hl, hc, lc))

    # Wilder smoothed TR, +DM, -DM (seed with SMA)
    smoothed_tr = sum(tr_vals[:period]) / period
    smoothed_plus = sum(plus_dm[:period]) / period
    smoothed_minus = sum(minus_dm[:period]) / period

    dx_vals: list[float] = []
    for i in range(period, n):
        smoothed_tr = (smoothed_tr * (period - 1) + tr_vals[i]) / period
        smoothed_plus = (smoothed_plus * (period - 1) + plus_dm[i]) / period
        smoothed_minus = (smoothed_minus * (period - 1) + minus_dm[i]) / period

        if smoothed_tr == 0:
            dx_vals.append(0.0)
            continue

        plus_di = 100.0 * smoothed_plus / smoothed_tr
        minus_di = 100.0 * smoothed_minus / smoothed_tr
        di_sum = plus_di + minus_di

        if di_sum == 0:
            dx_vals.append(0.0)
        else:
            dx_vals.append(100.0 * abs(plus_di - minus_di) / di_sum)

    # ADX = Wilder smoothed DX over `period`
    if len(dx_vals) < period:
        return result

    adx_val = sum(dx_vals[:period]) / period
    adx_start = period + period  # Need period DX values, first DX at index `period`
    if adx_start - 1 < n:
        result[adx_start - 1] = adx_val

    for i in range(period, len(dx_vals)):
        adx_val = (adx_val * (period - 1) + dx_vals[i]) / period
        global_idx = period + i
        if global_idx < n:
            result[global_idx] = adx_val

    return result


def obv(closes: list[float], volumes: list[int]) -> IndicatorSeries:
    """On-Balance Volume.

    Cumulative volume indicator: add volume on up days, subtract on down days.
    """
    n = len(closes)
    if n < 2 or len(volumes) != n:
        return [None] * n

    result: IndicatorSeries = [None] * n
    result[0] = float(volumes[0])

    for i in range(1, n):
        prev_obv = result[i - 1]
        if prev_obv is None:
            prev_obv = 0.0
        if closes[i] > closes[i - 1]:
            result[i] = prev_obv + float(volumes[i])
        elif closes[i] < closes[i - 1]:
            result[i] = prev_obv - float(volumes[i])
        else:
            result[i] = prev_obv

    return result


def stochastic(
    highs: list[float], lows: list[float], closes: list[float],
    k_period: int = 14, d_period: int = 3,
) -> tuple[IndicatorSeries, IndicatorSeries]:
    """Stochastic Oscillator (%K and %D).

    %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA(%K, d_period)

    Returns (k_series, d_series).
    """
    if k_period <= 0 or d_period <= 0:
        raise ValueError(f"periods must be positive, got k={k_period}, d={d_period}")
    n = len(closes)
    if n < k_period or len(highs) != n or len(lows) != n:
        return [None] * n, [None] * n

    k_series: IndicatorSeries = [None] * n

    for i in range(k_period - 1, n):
        window_highs = highs[i - k_period + 1: i + 1]
        window_lows = lows[i - k_period + 1: i + 1]
        highest = max(window_highs)
        lowest = min(window_lows)

        if highest == lowest:
            k_series[i] = 50.0  # Neutral when range is zero
        else:
            k_series[i] = (closes[i] - lowest) / (highest - lowest) * 100.0

    # %D = SMA of %K
    d_series: IndicatorSeries = [None] * n
    valid_k = [(i, v) for i, v in enumerate(k_series) if v is not None]

    for j in range(d_period - 1, len(valid_k)):
        idx = valid_k[j][0]
        avg = sum(valid_k[j - d_period + 1 + m][1] for m in range(d_period)) / d_period  # type: ignore[operator]
        d_series[idx] = avg

    return k_series, d_series


def volume_ratio(volumes: list[int], period: int = 20) -> IndicatorSeries:
    """Volume Ratio (current volume / average volume).

    Values > 1.5 indicate high volume. Values < 0.5 indicate low volume.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(volumes)
    result: IndicatorSeries = [None] * n

    for i in range(period - 1, n):
        window = volumes[i - period + 1: i + 1]
        avg = sum(window) / period
        if avg > 0:
            result[i] = float(volumes[i]) / avg
        else:
            result[i] = 0.0

    return result


# ─── High-level snapshot builder ─────────────────────────────────────────────


def compute_snapshot(symbol: str, prices: PriceSeries) -> IndicatorSnapshot:
    """Compute all indicators and return the latest-bar snapshot.

    This is the primary entry point for the trading engine. All
    indicators are computed from the full price series, but only the
    most recent bar's values are returned in the snapshot.

    Args:
        symbol: Stock symbol (e.g. "005930").
        prices: Closing prices ordered oldest → newest.
                - Minimum 34 bars for MACD (most demanding).
                - 200+ bars recommended for SMA-200.
                - 250–300 bars ideal (3 pages of KIS API results).

    Returns:
        IndicatorSnapshot with all indicator values for the last bar.
        Fields are None when insufficient data is available.

    Performance:
        ~0.6ms per symbol for 250 bars (pure Python, no dependencies).

    Examples:
        >>> snapshot = compute_snapshot("005930", close_prices)
        >>> if snapshot.is_oversold and snapshot.macd_bullish:
        ...     print("Potential buy: RSI oversold + MACD bullish")
        >>> if snapshot.bb_squeeze:
        ...     print("Bollinger squeeze — watch for breakout direction")
    """
    snap = IndicatorSnapshot(symbol=symbol)

    if not prices:
        return snap

    # SMA / EMA
    mas = moving_averages(prices)
    snap.sma5 = mas.sma5[-1]
    snap.sma10 = mas.sma10[-1]
    snap.sma20 = mas.sma20[-1]
    snap.sma60 = mas.sma60[-1]
    snap.sma120 = mas.sma120[-1]
    snap.sma200 = mas.sma200[-1]
    snap.ema12 = mas.ema12[-1]
    snap.ema26 = mas.ema26[-1]

    # RSI
    rsi_series = rsi(prices, 14)
    snap.rsi14 = rsi_series[-1]
    if snap.rsi14 is not None:
        snap.is_overbought = snap.rsi14 > 70.0
        snap.is_oversold = snap.rsi14 < 30.0

    # MACD
    macd_result = macd(prices)
    snap.macd_line = macd_result.macd[-1]
    snap.macd_signal = macd_result.signal[-1]
    snap.macd_hist = macd_result.histogram[-1]
    if snap.macd_hist is not None:
        snap.macd_bullish = snap.macd_hist > 0.0

    # Bollinger Bands
    bb = bollinger_bands(prices)
    snap.bb_upper = bb.upper[-1]
    snap.bb_middle = bb.middle[-1]
    snap.bb_lower = bb.lower[-1]
    snap.bb_pct_b = bb.pct_b[-1]
    snap.bb_bandwidth = bb.bandwidth[-1]
    if snap.bb_bandwidth is not None:
        snap.bb_squeeze = snap.bb_bandwidth < 2.0

    return snap


def compute_snapshot_ohlcv(symbol: str, ohlcv: OHLCVSeries) -> IndicatorSnapshot:
    """Compute all indicators including OHLCV-based ones.

    Internally calls compute_snapshot() for close-based indicators,
    then extends with ATR, ADX, OBV, Stochastic, volume_ratio.

    Args:
        symbol: Stock symbol.
        ohlcv: OHLCV data ordered oldest -> newest.

    Returns:
        IndicatorSnapshot with ALL fields populated (existing + new).
    """
    if not ohlcv:
        return IndicatorSnapshot(symbol=symbol)

    # Extract series from OHLCV
    closes = [bar.close for bar in ohlcv]
    highs = [bar.high for bar in ohlcv]
    lows_list = [bar.low for bar in ohlcv]
    volumes_list = [bar.volume for bar in ohlcv]

    # Base snapshot from closes (reuses existing compute_snapshot)
    snap = compute_snapshot(symbol, closes)

    # ATR
    atr_series = atr(highs, lows_list, closes, 14)
    snap.atr14 = atr_series[-1]

    # ADX
    adx_series = adx(highs, lows_list, closes, 14)
    snap.adx14 = adx_series[-1]
    if snap.adx14 is not None:
        snap.is_trending = snap.adx14 > 25.0

    # OBV
    obv_series = obv(closes, volumes_list)
    snap.obv_val = obv_series[-1]

    # Stochastic
    k_s, d_s = stochastic(highs, lows_list, closes)
    snap.stoch_k = k_s[-1]
    snap.stoch_d = d_s[-1]

    # Volume ratio
    vr_series = volume_ratio(volumes_list)
    snap.volume_ratio_val = vr_series[-1]
    if snap.volume_ratio_val is not None:
        snap.is_high_volume = snap.volume_ratio_val > 1.5

    return snap


# ─── KIS API data adapter ─────────────────────────────────────────────────────


def parse_kis_period_price(output: list[dict]) -> PriceSeries:
    """Convert KIS inquire_period_price output to a PriceSeries.

    The KIS API returns data newest-first. This function reverses
    the list so prices are in oldest-first order, which is required
    by all indicator functions.

    Args:
        output: The 'output' list from inquire_period_price response.
                Each dict must contain 'stck_clpr' (closing price as str).

    Returns:
        List of closing prices as float, ordered oldest → newest.

    Notes:
        For SMA-200, you need 200+ bars. KIS returns up to 100 bars per
        request. Fetch at least 3 pages by adjusting fid_input_date_1
        and fid_input_date_2, then concatenate the output lists before
        calling this function.

    Examples:
        >>> # Single page (up to 100 bars)
        >>> result = inquire_period_price(client, "005930",
        ...     fid_input_date_1="20240101", fid_input_date_2="20241231")
        >>> prices = parse_kis_period_price(result["output"])
        >>> snapshot = compute_snapshot("005930", prices)

        >>> # Multi-page fetch for 250+ bars
        >>> all_output = page1["output"] + page2["output"] + page3["output"]
        >>> prices = parse_kis_period_price(all_output)
    """
    # Filter out entries with empty or zero closing prices
    valid = [
        item
        for item in output
        if item.get("stck_clpr") and item["stck_clpr"].strip() not in ("", "0")
    ]
    # KIS API returns newest-first → reverse to oldest-first
    return [float(item["stck_clpr"]) for item in reversed(valid)]


def parse_kis_ohlcv(output: list[dict]) -> OHLCVSeries:
    """Convert KIS inquire_period_price output to OHLCVSeries.

    KIS API returns newest-first. Reversed to oldest-first order.
    Maps: stck_bsop_date->date, stck_oprc->open, stck_hgpr->high,
          stck_lwpr->low, stck_clpr->close, acml_vol->volume.
    """
    valid = [
        item for item in output
        if item.get("stck_clpr") and item["stck_clpr"].strip() not in ("", "0")
    ]
    return [
        OHLCVBar(
            date=item.get("stck_bsop_date", ""),
            open=float(item.get("stck_oprc", "0")),
            high=float(item.get("stck_hgpr", "0")),
            low=float(item.get("stck_lwpr", "0")),
            close=float(item.get("stck_clpr", "0")),
            volume=int(item.get("acml_vol", "0")),
        )
        for item in reversed(valid)
    ]


# ─── Thread-safe indicator cache ─────────────────────────────────────────────


class IndicatorCache:
    """Thread-safe in-memory cache for indicator snapshots.

    Stores the latest IndicatorSnapshot per symbol, updated by the
    data pipeline on each price refresh cycle (default: every 60s).

    Usage:
        # Application startup
        cache = IndicatorCache()

        # In price update loop (one writer thread)
        prices = parse_kis_period_price(api_result["output"])
        snapshot = compute_snapshot("005930", prices)
        cache.update("005930", snapshot)

        # In strategy evaluation (multiple reader threads safe)
        snap = cache.get("005930")
        if snap and snap.is_oversold and snap.macd_bullish:
            # Emit buy signal
            ...

    Thread safety:
        Uses RLock. Safe for single-writer + multiple-reader pattern.
        All public methods are atomic with respect to each other.
    """

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._data: dict[str, IndicatorSnapshot] = {}

    def update(self, symbol: str, snapshot: IndicatorSnapshot) -> None:
        """Store or replace the snapshot for a symbol."""
        with self._lock:
            self._data[symbol] = snapshot

    def get(self, symbol: str) -> IndicatorSnapshot | None:
        """Return the cached snapshot, or None if not yet computed."""
        with self._lock:
            return self._data.get(symbol)

    def get_all(self) -> dict[str, IndicatorSnapshot]:
        """Return a shallow copy of all snapshots."""
        with self._lock:
            return dict(self._data)

    def symbols(self) -> list[str]:
        """Return sorted list of symbols with cached snapshots."""
        with self._lock:
            return sorted(self._data.keys())

    def clear(self, symbol: str | None = None) -> None:
        """Clear one symbol's snapshot, or all snapshots if symbol is None."""
        with self._lock:
            if symbol is None:
                self._data.clear()
            else:
                self._data.pop(symbol, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __repr__(self) -> str:
        with self._lock:
            return f"IndicatorCache({len(self._data)} symbols: {self.symbols()})"
