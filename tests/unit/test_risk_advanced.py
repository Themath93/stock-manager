"""Tests for advanced risk management components."""
from decimal import Decimal
from datetime import date
import threading
import pytest

from stock_manager.trading.risk.circuit_breaker import CircuitBreakerManager
from stock_manager.trading.risk.sector_exposure import (
    Position, SectorExposureSnapshot, compute_sector_exposure,
)
from stock_manager.trading.risk.volatility_sizing import compute_volatility_position_size
from stock_manager.trading.risk.metrics_cache import DailyRiskMetricsCache


class TestCircuitBreaker:
    def test_not_tripped_initially(self):
        cb = CircuitBreakerManager()
        assert cb.is_tripped() is False

    def test_trips_after_3_consecutive_losses(self):
        cb = CircuitBreakerManager(max_consecutive_losses=3)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-200"))
        assert cb.is_tripped() is False
        cb.record_trade_result(Decimal("-50"))
        assert cb.is_tripped() is True

    def test_win_resets_consecutive_losses(self):
        cb = CircuitBreakerManager(max_consecutive_losses=3)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-200"))
        cb.record_trade_result(Decimal("50"))  # Win resets
        cb.record_trade_result(Decimal("-100"))
        assert cb.is_tripped() is False

    def test_daily_reset(self):
        cb = CircuitBreakerManager()
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-100"))
        assert cb.is_tripped() is True
        cb.reset_daily(Decimal("10000000"))
        assert cb.is_tripped() is False

    def test_thread_safety(self):
        cb = CircuitBreakerManager(max_consecutive_losses=100)
        def record_losses():
            for _ in range(50):
                cb.record_trade_result(Decimal("-1"))
        threads = [threading.Thread(target=record_losses) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert cb._consecutive_losses == 200  # Exact count proves no race


class TestSectorExposure:
    def test_compute_exposure(self):
        positions = [
            Position(symbol="005930", sector="IT", market_value=Decimal("5000000")),
            Position(symbol="000660", sector="IT", market_value=Decimal("3000000")),
            Position(symbol="035420", sector="Services", market_value=Decimal("2000000")),
        ]
        snap = compute_sector_exposure(positions)
        assert snap.total_value == Decimal("10000000")
        assert snap.get_pct("IT") == 80.0
        assert snap.get_pct("Services") == 20.0
        assert snap.exceeds_limit("IT", 50.0) is True
        assert snap.exceeds_limit("Services", 50.0) is False

    def test_empty_positions(self):
        snap = compute_sector_exposure([])
        assert snap.total_value == Decimal("0")
        assert snap.get_pct("IT") == 0.0


class TestVolatilitySizing:
    def test_basic_sizing(self):
        shares = compute_volatility_position_size(
            available_capital=Decimal("10000000"),
            current_price=Decimal("50000"),
            atr_14=1000.0,
        )
        assert shares > 0
        assert shares <= 20  # Max 10% of 10M / 50K = 20 shares

    def test_high_volatility_smaller_position(self):
        low_vol = compute_volatility_position_size(
            Decimal("10000000"), Decimal("50000"), atr_14=3000.0,
        )
        high_vol = compute_volatility_position_size(
            Decimal("10000000"), Decimal("50000"), atr_14=10000.0,
        )
        assert low_vol > high_vol

    def test_zero_inputs_returns_zero(self):
        assert compute_volatility_position_size(Decimal("0"), Decimal("50000"), 1000.0) == 0
        assert compute_volatility_position_size(Decimal("10000000"), Decimal("0"), 1000.0) == 0
        assert compute_volatility_position_size(Decimal("10000000"), Decimal("50000"), 0.0) == 0


class TestDailyMetricsCache:
    def test_compute_once(self):
        cache = DailyRiskMetricsCache()
        call_count = 0
        def compute():
            nonlocal call_count
            call_count += 1
            return 42
        assert cache.get_or_compute("test", compute) == 42
        assert cache.get_or_compute("test", compute) == 42
        assert call_count == 1  # Only computed once

    def test_invalidate_key(self):
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("a", lambda: 1)
        cache.get_or_compute("b", lambda: 2)
        cache.invalidate("a")
        assert cache.get_or_compute("a", lambda: 10) == 10
        assert cache.get_or_compute("b", lambda: 20) == 2  # Still cached

    def test_is_stale(self):
        cache = DailyRiskMetricsCache()
        assert cache.is_stale is True
        cache.get_or_compute("x", lambda: 1)
        assert cache.is_stale is False
