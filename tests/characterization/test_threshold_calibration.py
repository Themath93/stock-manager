"""Characterization tests for Phase 1 Korean market threshold calibrations."""
from decimal import Decimal
from stock_manager.trading.personas.models import MarketSnapshot


def _make_snapshot(**kwargs) -> MarketSnapshot:
    """Create a MarketSnapshot with sensible defaults."""
    from datetime import datetime, timezone
    defaults = {
        "symbol": "005930", "name": "Samsung", "market": "KRX",
        "current_price": Decimal("50000"), "timestamp": datetime.now(timezone.utc),
        "per": 10.0, "pbr": 0.9, "eps": Decimal("5000"),
        "dividend_yield": 3.5, "roe": 16.0,
        "current_ratio": 1.6, "debt_to_equity": 0.8,
        "operating_margin": 20.0, "net_margin": 13.0,
        "free_cash_flow": Decimal("100000000000"),
        "sma_20": 49000.0, "sma_50": 48000.0, "sma_200": 47000.0,
        "rsi_14": 45.0, "macd_signal": 0.5, "bollinger_position": 0.5,
        "adx_14": 22.0, "atr_14": 500.0,
        "price_52w_high": Decimal("60000"), "price_52w_low": Decimal("40000"),
        "years_positive_earnings": 1, "years_dividends_paid": 1,
        "earnings_growth_yoy": 18.0, "revenue_growth_yoy": 16.0,
        "market_cap": Decimal("3000000000000"),
    }
    defaults.update(kwargs)
    return MarketSnapshot(**defaults)


class TestGrahamCalibration:
    def test_pe_12_passes(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(per=11.0)
        assert GrahamPersona._check_pe(s) is True

    def test_pe_13_fails(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(per=13.0)
        assert GrahamPersona._check_pe(s) is False

    def test_pb_09_passes(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(pbr=0.9)
        assert GrahamPersona._check_pb(s) is True

    def test_pb_12_fails(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(pbr=1.2)
        assert GrahamPersona._check_pb(s) is False

    def test_current_ratio_16_passes(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(current_ratio=1.6)
        assert GrahamPersona._check_financial(s) is True

    def test_stability_1yr_passes(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(years_positive_earnings=1)
        assert GrahamPersona._check_stability(s) is True

    def test_dividends_1yr_passes(self):
        from stock_manager.trading.personas.graham_persona import GrahamPersona
        s = _make_snapshot(years_dividends_paid=1)
        assert GrahamPersona._check_dividends(s) is True


class TestDalioCalibration:
    def test_rsi_73_not_overbought(self):
        from stock_manager.trading.personas.dalio_persona import _RSI_OVERBOUGHT
        assert _RSI_OVERBOUGHT == 75.0

    def test_adx_22_is_trending(self):
        from stock_manager.trading.personas.dalio_persona import _ADX_TRENDING
        assert _ADX_TRENDING == 20.0

    def test_risk_reward_min(self):
        from stock_manager.trading.personas.dalio_persona import _RISK_REWARD_MIN
        assert _RISK_REWARD_MIN == 1.5


class TestBuffettCalibration:
    def test_net_margin_13_passes(self):
        from stock_manager.trading.personas.buffett_persona import BuffettPersona
        s = _make_snapshot(net_margin=13.0)
        assert BuffettPersona._check_net_margin(s) is True

    def test_years_earnings_1_passes(self):
        from stock_manager.trading.personas.buffett_persona import BuffettPersona
        s = _make_snapshot(years_positive_earnings=1)
        assert BuffettPersona._check_earnings_stability(s) is True

    def test_de_08_passes(self):
        from stock_manager.trading.personas.buffett_persona import BuffettPersona
        s = _make_snapshot(debt_to_equity=0.8)
        assert BuffettPersona._check_low_leverage(s) is True


class TestFisherCalibration:
    def test_de_04_passes(self):
        from stock_manager.trading.personas.fisher_persona import _DEBT_EQUITY_MAX
        assert _DEBT_EQUITY_MAX == 0.5

    def test_roe_16_passes(self):
        from stock_manager.trading.personas.fisher_persona import _ROE_MIN
        assert _ROE_MIN == 15.0


class TestTempletonCalibration:
    def test_pe_max_8(self):
        from stock_manager.trading.personas.templeton_persona import _PE_MAX
        assert _PE_MAX == 8.0

    def test_pb_max_07(self):
        from stock_manager.trading.personas.templeton_persona import _PB_MAX
        assert _PB_MAX == 0.7

    def test_dividend_yield_min_3(self):
        from stock_manager.trading.personas.templeton_persona import _DIVIDEND_YIELD_MIN
        assert _DIVIDEND_YIELD_MIN == 3.0


class TestLynchCalibration:
    def test_earnings_growth_18_passes(self):
        from stock_manager.trading.personas.lynch_persona import LynchPersona
        s = _make_snapshot(earnings_growth_yoy=18.0)
        assert LynchPersona._check_earnings_growth_range(s) is True

    def test_earnings_growth_45_fails(self):
        from stock_manager.trading.personas.lynch_persona import LynchPersona
        s = _make_snapshot(earnings_growth_yoy=45.0)
        assert LynchPersona._check_earnings_growth_range(s) is False


class TestSimonsCalibration:
    def test_rsi_oversold_35(self):
        from stock_manager.trading.personas.simons_persona import _RSI_OVERSOLD
        assert _RSI_OVERSOLD == 35.0

    def test_bollinger_extreme_008(self):
        from stock_manager.trading.personas.simons_persona import _BOLLINGER_EXTREME
        assert _BOLLINGER_EXTREME == 0.08

    def test_volume_anomaly_15(self):
        from stock_manager.trading.personas.simons_persona import _VOLUME_ANOMALY_FACTOR
        assert _VOLUME_ANOMALY_FACTOR == 1.5

    def test_mean_reversion_15(self):
        from stock_manager.trading.personas.simons_persona import _MEAN_REVERSION_STD
        assert _MEAN_REVERSION_STD == 1.5
