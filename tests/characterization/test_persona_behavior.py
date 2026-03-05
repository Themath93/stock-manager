"""Characterization tests for persona logic bug fixes."""
import pytest
from decimal import Decimal
from stock_manager.trading.personas.models import MarketSnapshot, PersonaCategory


def _make_snapshot(**kwargs) -> MarketSnapshot:
    """Create a MarketSnapshot with sensible defaults and overrides."""
    defaults = {
        "symbol": "005930",
        "name": "Samsung",
        "market": "KRX",
        "current_price": Decimal("50000"),
        "per": 10.0,
        "pbr": 1.0,
        "eps": Decimal("5000"),
        "dividend_yield": 2.0,
        "roe": 15.0,
        "current_ratio": 1.5,
        "debt_to_equity": 0.5,
        "operating_margin": 20.0,
        "net_margin": 12.0,
        "sma_20": 49000.0,
        "sma_50": 48000.0,
        "sma_200": 47000.0,
        "rsi_14": 45.0,
        "macd_signal": 0.5,
        "bollinger_position": 0.5,
        "adx_14": 25.0,
        "atr_14": 500.0,
        "price_52w_high": Decimal("60000"),
        "price_52w_low": Decimal("40000"),
        "earnings_growth_yoy": 15.0,
        "revenue_growth_yoy": 10.0,
    }
    defaults.update(kwargs)
    return MarketSnapshot(**defaults)


class TestDalioVkospiNone:
    """Task 0.7b: Dalio rejects when VKOSPI unavailable."""

    def test_vkospi_none_returns_false(self):
        """When vkospi is None, _check_sector_correlation must return False."""
        from stock_manager.trading.personas.dalio_persona import DalioPersona
        snapshot = _make_snapshot(vkospi=None)
        assert DalioPersona._check_sector_correlation(snapshot) is False

    def test_vkospi_low_returns_true(self):
        """When vkospi is low (< 70), sector correlation check passes."""
        from stock_manager.trading.personas.dalio_persona import DalioPersona
        snapshot = _make_snapshot(vkospi=18.5)
        assert DalioPersona._check_sector_correlation(snapshot) is True

    def test_vkospi_high_returns_false(self):
        """When vkospi is high (>= 70), sector correlation check fails."""
        from stock_manager.trading.personas.dalio_persona import DalioPersona
        snapshot = _make_snapshot(vkospi=80.0)
        assert DalioPersona._check_sector_correlation(snapshot) is False


class TestLynchPeFallback:
    """Task 0.8b: Lynch uses 12.0 KOSPI P/E fallback."""

    def test_kospi_per_none_uses_12(self):
        """When kospi_per is None, Lynch should use 12.0 as market P/E."""
        # Stock with P/E = 11 should pass "below market avg" with fallback 12.0
        from stock_manager.trading.personas.lynch_persona import LynchPersona
        snapshot = _make_snapshot(per=11.0, kospi_per=None, earnings_growth_yoy=25.0)
        persona = LynchPersona()
        assert persona._check_pe_below_avg(snapshot) is True

    def test_kospi_per_none_pe_above_12_fails(self):
        """P/E = 13.0 should fail when market P/E fallback is 12.0."""
        from stock_manager.trading.personas.lynch_persona import LynchPersona
        snapshot = _make_snapshot(per=13.0, kospi_per=None)
        persona = LynchPersona()
        assert persona._check_pe_below_avg(snapshot) is False

    def test_kospi_per_provided_uses_actual(self):
        """When kospi_per is provided, use actual value."""
        from stock_manager.trading.personas.lynch_persona import LynchPersona
        snapshot = _make_snapshot(per=11.0, kospi_per=14.0)
        persona = LynchPersona()
        assert persona._check_pe_below_avg(snapshot) is True
