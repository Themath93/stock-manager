"""Unit tests for OHLCV-based indicators (Phase 0 extension).

Tests cover: atr, adx, obv, stochastic, volume_ratio,
compute_snapshot_ohlcv, parse_kis_ohlcv, and backward-compat
guarantees on compute_snapshot / IndicatorSnapshot.
"""
from __future__ import annotations

import math
import pytest

from stock_manager.pipeline.indicators import (
    OHLCVBar,
    IndicatorSnapshot,
    atr,
    adx,
    obv,
    stochastic,
    volume_ratio,
    compute_snapshot,
    compute_snapshot_ohlcv,
    parse_kis_ohlcv,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_bars(
    n: int = 50,
    start_price: float = 100.0,
    step: float = 1.0,
    base_volume: int = 100_000,
) -> list[OHLCVBar]:
    """Return *n* synthetic OHLCV bars with a gentle uptrend.

    Each bar:
        close  = start_price + i * step
        open   = close - step * 0.5
        high   = close + step * 0.5
        low    = open  - step * 0.3
        volume = base_volume + i * 500  (slowly increasing)
    """
    bars: list[OHLCVBar] = []
    for i in range(n):
        close = start_price + i * step
        open_ = close - step * 0.5
        high = close + step * 0.5
        low = open_ - step * 0.3
        volume = base_volume + i * 500
        bars.append(OHLCVBar(
            date=f"202401{i + 1:02d}",
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        ))
    return bars


def _extract(bars: list[OHLCVBar]):
    """Return (highs, lows, closes, volumes) from a bar list."""
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    return highs, lows, closes, volumes


def _unpack(bars: list[OHLCVBar]):
    """Alias for _extract that avoids the `l` variable name in callers."""
    return _extract(bars)


# ---------------------------------------------------------------------------
# TestATR
# ---------------------------------------------------------------------------


class TestATR:
    def test_basic_atr(self):
        bars = _make_bars(30)
        h, lo, c, _ = _extract(bars)
        result = atr(h, lo, c, period=14)
        assert len(result) == 30
        # First valid value is at index 13 (period - 1)
        assert result[13] is not None
        assert result[13] > 0.0

    def test_insufficient_data(self):
        bars = _make_bars(10)
        h, lo, c, _ = _extract(bars)
        result = atr(h, lo, c, period=14)
        # All None because n < period
        assert all(v is None for v in result)

    def test_known_values(self):
        # Flat market: high-low = 2.0 every bar, no gap opens
        n = 20
        closes = [100.0] * n
        highs = [101.0] * n
        lows = [99.0] * n
        result = atr(highs, lows, closes, period=14)
        # TR for every bar = 2.0; ATR should converge to 2.0
        valid = [v for v in result if v is not None]
        assert valid, "Should have at least one valid ATR value"
        # ATR should be within 10% of the constant TR=2.0
        assert abs(valid[-1] - 2.0) < 0.3

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            atr([1.0], [0.5], [0.75], period=0)

    def test_mismatched_lengths_returns_none_series(self):
        result = atr([1.0, 2.0], [0.5], [0.75, 1.0], period=1)
        assert all(v is None for v in result)


# ---------------------------------------------------------------------------
# TestADX
# ---------------------------------------------------------------------------


class TestADX:
    def test_basic_adx(self):
        bars = _make_bars(50)
        h, lo, c, _ = _extract(bars)
        result = adx(h, lo, c, period=14)
        assert len(result) == 50
        # Need period*2 bars for first valid; index 27 = period*2-1
        valid = [v for v in result if v is not None]
        assert valid, "Should produce at least one ADX value with 50 bars"
        assert all(0.0 <= v <= 100.0 for v in valid)

    def test_trending_market(self):
        # Strong linear trend: price rises 5 pts per bar
        bars = _make_bars(60, step=5.0)
        h, lo, c, _ = _extract(bars)
        result = adx(h, lo, c, period=14)
        last_valid = next((v for v in reversed(result) if v is not None), None)
        assert last_valid is not None
        # Strong directional move should produce ADX > 20
        assert last_valid > 20.0, f"Expected ADX > 20 for strong trend, got {last_valid}"

    def test_ranging_market(self):
        # Sideways: alternating tiny up/down bars
        import math as _math
        n = 60
        closes = [100.0 + _math.sin(i * 0.3) * 0.5 for i in range(n)]
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.3 for c in closes]
        result = adx(highs, lows, closes, period=14)
        valid = [v for v in result if v is not None]
        assert valid, "Should produce ADX values for 60 bars"
        # Sideways market should have low ADX (< 30 is reasonable)
        assert valid[-1] < 30.0, f"Expected low ADX for ranging market, got {valid[-1]}"

    def test_insufficient_data(self):
        bars = _make_bars(20)
        h, lo, c, _ = _extract(bars)
        # period=14 needs 28 bars minimum
        result = adx(h, lo, c, period=14)
        assert all(v is None for v in result)

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            adx([1.0], [0.5], [0.75], period=0)


# ---------------------------------------------------------------------------
# TestOBV
# ---------------------------------------------------------------------------


class TestOBV:
    def test_up_days_increase_obv(self):
        # Each bar closes higher than previous -> OBV should rise monotonically
        closes = [100.0 + i for i in range(10)]
        volumes = [1000] * 10
        result = obv(closes, volumes)
        assert result[0] == 1000.0
        for i in range(1, 10):
            assert result[i] > result[i - 1], f"OBV should increase at index {i}"

    def test_down_days_decrease_obv(self):
        # Each bar closes lower than previous -> OBV should fall monotonically
        closes = [110.0 - i for i in range(10)]
        volumes = [1000] * 10
        result = obv(closes, volumes)
        assert result[0] == 1000.0
        for i in range(1, 10):
            assert result[i] < result[i - 1], f"OBV should decrease at index {i}"

    def test_flat_days_unchanged_obv(self):
        # Flat closes -> OBV stays constant after seed
        closes = [100.0] * 10
        volumes = [1000] * 10
        result = obv(closes, volumes)
        # All should equal the initial volume
        for v in result:
            assert v == 1000.0

    def test_mismatched_lengths(self):
        result = obv([100.0, 101.0], [1000])
        assert all(v is None for v in result)

    def test_insufficient_bars(self):
        result = obv([100.0], [1000])
        assert all(v is None for v in result)


# ---------------------------------------------------------------------------
# TestStochastic
# ---------------------------------------------------------------------------


class TestStochastic:
    def test_basic_returns_both_series(self):
        bars = _make_bars(30)
        h, lo, c, _ = _extract(bars)
        k, d = stochastic(h, lo, c, k_period=14, d_period=3)
        assert len(k) == 30
        assert len(d) == 30

    def test_extreme_oversold(self):
        # Price at the lowest point of its range -> %K near 0
        n = 20
        # Prices fall to a new low on the last bar
        highs = [110.0] * n
        lows = [90.0] * n
        closes = list(range(110, 110 - n, -1))  # declining
        closes[-1] = 90.0  # last bar at the absolute low
        k, _ = stochastic(highs, lows, closes, k_period=14)
        last_k = next((v for v in reversed(k) if v is not None), None)
        assert last_k is not None
        assert last_k < 10.0, f"Expected %K near 0 when at low, got {last_k}"

    def test_extreme_overbought(self):
        # Price at the highest point of its range -> %K near 100
        n = 20
        highs = [110.0] * n
        lows = [90.0] * n
        closes = list(range(90, 90 + n))  # rising
        closes[-1] = 110.0  # last bar at the absolute high
        k, _ = stochastic(highs, lows, closes, k_period=14)
        last_k = next((v for v in reversed(k) if v is not None), None)
        assert last_k is not None
        assert last_k > 90.0, f"Expected %K near 100 when at high, got {last_k}"

    def test_d_is_smoothed_k(self):
        bars = _make_bars(40)
        h, lo, c, _ = _extract(bars)
        k, d = stochastic(h, lo, c, k_period=14, d_period=3)
        # Wherever d is valid, it should be between min and max of nearby k values
        for i in range(len(d)):
            if d[i] is not None and k[i] is not None:
                assert 0.0 <= d[i] <= 100.0

    def test_insufficient_bars(self):
        k, d = stochastic([1.0, 2.0], [0.5, 1.0], [0.8, 1.5], k_period=14)
        assert all(v is None for v in k)
        assert all(v is None for v in d)

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            stochastic([1.0], [0.5], [0.8], k_period=0)


# ---------------------------------------------------------------------------
# TestVolumeRatio
# ---------------------------------------------------------------------------


class TestVolumeRatio:
    def test_normal_volume(self):
        # All bars have same volume -> ratio should be 1.0
        volumes = [1000] * 30
        result = volume_ratio(volumes, period=20)
        valid = [v for v in result if v is not None]
        assert valid
        for v in valid:
            assert abs(v - 1.0) < 1e-9

    def test_high_volume(self):
        # Steady baseline then last bar has 2x average
        volumes = [1000] * 29 + [2000]
        result = volume_ratio(volumes, period=20)
        last = result[-1]
        assert last is not None
        # Last bar volume is 2000, avg of last 20 bars is (19*1000 + 2000)/20 = 1050
        # ratio = 2000/1050 ≈ 1.90
        assert last > 1.5, f"Expected ratio > 1.5 for high volume bar, got {last}"

    def test_insufficient_bars_returns_none(self):
        result = volume_ratio([1000, 2000], period=20)
        assert all(v is None for v in result)

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            volume_ratio([1000], period=0)


# ---------------------------------------------------------------------------
# TestComputeSnapshotOHLCV
# ---------------------------------------------------------------------------


class TestComputeSnapshotOHLCV:
    def test_populates_all_new_fields(self):
        bars = _make_bars(60)
        snap = compute_snapshot_ohlcv("TEST", bars)
        # With 60 bars all new OHLCV fields should be populated
        assert snap.atr14 is not None, "atr14 should be populated with 60 bars"
        assert snap.adx14 is not None, "adx14 should be populated with 60 bars"
        assert snap.obv_val is not None, "obv_val should be populated"
        assert snap.stoch_k is not None, "stoch_k should be populated"
        assert snap.stoch_d is not None, "stoch_d should be populated"
        assert snap.volume_ratio_val is not None, "volume_ratio_val should be populated"

    def test_backward_compat_fields(self):
        bars = _make_bars(60)
        snap = compute_snapshot_ohlcv("TEST", bars)
        # Existing close-based indicators must also be present
        assert snap.sma5 is not None
        assert snap.rsi14 is not None
        assert snap.macd_line is not None
        assert snap.bb_upper is not None

    def test_is_trending_flag_true_when_adx_above_25(self):
        # Strong trend bars -> ADX > 25 -> is_trending True
        bars = _make_bars(60, step=5.0)  # steep uptrend
        snap = compute_snapshot_ohlcv("TREND", bars)
        if snap.adx14 is not None and snap.adx14 > 25.0:
            assert snap.is_trending is True
        # If ADX not > 25, is_trending should be False
        elif snap.adx14 is not None:
            assert snap.is_trending is False

    def test_is_trending_flag_false_when_adx_below_25(self):
        # Flat / ranging market -> ADX < 25 -> is_trending False
        n = 60
        closes = [100.0 + math.sin(i * 0.5) * 0.2 for i in range(n)]
        highs = [c + 0.2 for c in closes]
        lows = [c - 0.2 for c in closes]
        bars = [
            OHLCVBar(date=f"20240{i+1:03d}", open=c, high=h, low=lo, close=c, volume=100_000)
            for i, (c, h, lo) in enumerate(zip(closes, highs, lows))
        ]
        snap = compute_snapshot_ohlcv("FLAT", bars)
        if snap.adx14 is not None and snap.adx14 <= 25.0:
            assert snap.is_trending is False

    def test_is_high_volume_flag(self):
        # Last bar has 3x average volume -> is_high_volume True
        bars = _make_bars(50)
        # Replace last bar with a high-volume one
        last = bars[-1]
        bars[-1] = OHLCVBar(
            date=last.date,
            open=last.open, high=last.high, low=last.low, close=last.close,
            volume=last.volume * 10,
        )
        snap = compute_snapshot_ohlcv("HVOL", bars)
        if snap.volume_ratio_val is not None and snap.volume_ratio_val > 1.5:
            assert snap.is_high_volume is True

    def test_empty_bars_returns_empty_snapshot(self):
        snap = compute_snapshot_ohlcv("EMPTY", [])
        assert snap.atr14 is None
        assert snap.adx14 is None
        assert snap.obv_val is None

    def test_symbol_preserved(self):
        bars = _make_bars(30)
        snap = compute_snapshot_ohlcv("005930", bars)
        assert snap.symbol == "005930"


# ---------------------------------------------------------------------------
# TestParseKisOHLCV
# ---------------------------------------------------------------------------


class TestParseKisOHLCV:
    def _make_kis_records(self, n: int = 10) -> list[dict]:
        """KIS API returns newest-first."""
        return [
            {
                "stck_bsop_date": f"2024{n - i:04d}",
                "stck_oprc": str(100 + n - i),
                "stck_hgpr": str(102 + n - i),
                "stck_lwpr": str(99 + n - i),
                "stck_clpr": str(101 + n - i),
                "acml_vol": str(100_000 + i * 1000),
            }
            for i in range(n)
        ]

    def test_parses_kis_format(self):
        records = self._make_kis_records(5)
        bars = parse_kis_ohlcv(records)
        assert len(bars) == 5
        for bar in bars:
            assert bar.open > 0
            assert bar.high >= bar.close
            assert bar.low <= bar.open
            assert bar.volume > 0

    def test_reverses_order(self):
        # KIS newest-first -> parse should produce oldest-first
        records = self._make_kis_records(5)
        bars = parse_kis_ohlcv(records)
        # After reversal, closes should be ascending (oldest = smallest)
        closes = [b.close for b in bars]
        assert closes == sorted(closes), (
            f"Expected oldest-first (ascending) closes, got {closes}"
        )

    def test_filters_zero_close(self):
        records = self._make_kis_records(3)
        records[1]["stck_clpr"] = "0"  # invalid bar
        bars = parse_kis_ohlcv(records)
        assert len(bars) == 2

    def test_filters_empty_close(self):
        records = self._make_kis_records(3)
        records[0]["stck_clpr"] = ""
        bars = parse_kis_ohlcv(records)
        assert len(bars) == 2

    def test_empty_input(self):
        bars = parse_kis_ohlcv([])
        assert bars == []

    def test_returns_ohlcv_bar_instances(self):
        records = self._make_kis_records(3)
        bars = parse_kis_ohlcv(records)
        for bar in bars:
            assert isinstance(bar, OHLCVBar)


# ---------------------------------------------------------------------------
# TestBackwardCompat
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_existing_compute_snapshot_unchanged(self):
        # compute_snapshot() must still work on close prices only
        closes = [float(100 + i) for i in range(50)]
        snap = compute_snapshot("COMPAT", closes)
        assert snap.symbol == "COMPAT"
        assert snap.sma5 is not None
        assert snap.rsi14 is not None

    def test_compute_snapshot_new_ohlcv_fields_are_none(self):
        # compute_snapshot() should NOT populate OHLCV-only fields
        closes = [float(100 + i) for i in range(50)]
        snap = compute_snapshot("COMPAT", closes)
        assert snap.atr14 is None
        assert snap.adx14 is None
        assert snap.obv_val is None
        assert snap.stoch_k is None
        assert snap.stoch_d is None
        assert snap.volume_ratio_val is None
        assert snap.is_trending is None
        assert snap.is_high_volume is None

    def test_indicator_snapshot_new_fields_default_none(self):
        # IndicatorSnapshot() with just a symbol -> all new fields None
        snap = IndicatorSnapshot(symbol="X")
        assert snap.atr14 is None
        assert snap.adx14 is None
        assert snap.obv_val is None
        assert snap.stoch_k is None
        assert snap.stoch_d is None
        assert snap.volume_ratio_val is None
        assert snap.is_trending is None
        assert snap.is_high_volume is None

    def test_indicator_snapshot_legacy_bool_defaults(self):
        # Legacy bool flags must default False (not None) for backward compat
        snap = IndicatorSnapshot(symbol="X")
        assert snap.is_overbought is False
        assert snap.is_oversold is False
        assert snap.macd_bullish is False
        assert snap.bb_squeeze is False
