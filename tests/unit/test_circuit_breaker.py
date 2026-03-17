"""Specification tests for CircuitBreakerManager.

Each test documents an expected behavior of the circuit breaker risk control.
"""

from decimal import Decimal

from stock_manager.trading.risk.circuit_breaker import CircuitBreakerManager


class TestCircuitBreakerManager:
    """CircuitBreakerManager behavior specifications."""

    def test_initial_state_is_not_tripped(self):
        """Circuit breaker starts in non-tripped state."""
        cb = CircuitBreakerManager()
        assert cb.is_tripped() is False

    def test_trips_after_consecutive_losses(self):
        """N consecutive losses trip the circuit breaker."""
        cb = CircuitBreakerManager(max_consecutive_losses=3)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-50"))
        assert cb.is_tripped() is False  # 2 losses, not yet tripped
        cb.record_trade_result(Decimal("-75"))
        assert cb.is_tripped() is True  # 3rd loss → tripped

    def test_profitable_trade_resets_loss_counter(self):
        """A profitable trade resets the consecutive loss counter."""
        cb = CircuitBreakerManager(max_consecutive_losses=3)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-50"))
        # 2 consecutive losses, then a win resets counter
        cb.record_trade_result(Decimal("200"))
        assert cb.is_tripped() is False
        # Need 3 fresh consecutive losses to trip
        cb.record_trade_result(Decimal("-10"))
        cb.record_trade_result(Decimal("-10"))
        assert cb.is_tripped() is False  # only 2 since reset

    def test_trips_on_daily_drawdown_threshold(self):
        """Daily drawdown exceeding threshold trips the circuit breaker."""
        cb = CircuitBreakerManager(max_daily_drawdown_pct=0.05)
        cb.reset_daily(portfolio_value=Decimal("10000"))
        # Lose 5% of portfolio → should trip
        cb.record_trade_result(Decimal("-500"))
        assert cb.is_tripped() is True

    def test_drawdown_below_threshold_does_not_trip(self):
        """Daily drawdown below threshold keeps circuit breaker clear."""
        cb = CircuitBreakerManager(max_daily_drawdown_pct=0.05)
        cb.reset_daily(portfolio_value=Decimal("10000"))
        # Lose 4% of portfolio → should NOT trip
        cb.record_trade_result(Decimal("-400"))
        assert cb.is_tripped() is False

    def test_reset_daily_clears_all_state(self):
        """reset_daily() clears counters, trip state, and sets portfolio value."""
        cb = CircuitBreakerManager(max_consecutive_losses=2)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-100"))
        assert cb.is_tripped() is True

        cb.reset_daily(portfolio_value=Decimal("20000"))
        assert cb.is_tripped() is False

    def test_reset_daily_without_portfolio_value(self):
        """reset_daily() without portfolio_value still clears trip state."""
        cb = CircuitBreakerManager(max_consecutive_losses=2)
        cb.record_trade_result(Decimal("-100"))
        cb.record_trade_result(Decimal("-100"))
        assert cb.is_tripped() is True

        cb.reset_daily()
        assert cb.is_tripped() is False
