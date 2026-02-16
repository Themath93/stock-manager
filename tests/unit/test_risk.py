"""Unit tests for risk management functions."""

from decimal import Decimal
from stock_manager.trading.risk import (
    calculate_kelly_position_size,
    RiskManager,
    RiskLimits,
)


class TestKellyPositionSize:
    """Unit tests for Kelly position sizing pure function."""

    def test_basic_position_size(self):
        """Test basic Kelly position size calculation."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        # Risk amount = 1,000,000 * 0.02 = 20,000
        # Position value = 20,000 / 0.05 = 400,000
        # Max value = 1,000,000 * 0.10 = 100,000 (capped)
        # Shares = 100,000 / 50,000 = 2
        assert result == 2

    def test_position_size_capped_by_max(self):
        """Test position size is capped at max portfolio percentage."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.10"),  # High risk
            stop_loss_pct=Decimal("0.02"),  # Tight stop
            max_position_size_pct=Decimal("0.10"),  # 10% max
        )
        # Without cap: risk=100k, position=5M/0.02=5M, shares=100
        # With cap: max_value=100k, shares=100k/50k=2
        assert result == 2

    def test_position_size_zero_portfolio(self):
        """Test position size returns 0 for zero portfolio value."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("0"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        assert result == 0

    def test_position_size_negative_portfolio(self):
        """Test position size returns 0 for negative portfolio value."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("-1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        assert result == 0

    def test_position_size_small_portfolio(self):
        """Test position size with small portfolio."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("100000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        # Risk amount = 100,000 * 0.02 = 2,000
        # Position value = 2,000 / 0.05 = 40,000
        # Shares = 40,000 / 50,000 = 0 (truncated)
        assert result == 0

    def test_position_size_wider_stop_loss(self):
        """Test position size with wider stop loss."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.10"),  # Wider stop
            max_position_size_pct=Decimal("0.20"),
        )
        # Risk amount = 1,000,000 * 0.02 = 20,000
        # Position value = 20,000 / 0.10 = 200,000
        # Shares = 200,000 / 50,000 = 4
        assert result == 4

    def test_position_size_higher_risk_per_trade(self):
        """Test position size with higher risk per trade."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.05"),  # 5% risk
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.20"),
        )
        # Risk amount = 1,000,000 * 0.05 = 50,000
        # Position value = 50,000 / 0.05 = 1,000,000
        # Without cap: shares = 1,000,000 / 50,000 = 20
        # With cap: max_value = 200,000, shares = 4
        assert result == 4

    def test_position_size_fractional_result(self):
        """Test position size truncates fractional shares."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("75000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        # Risk amount = 1,000,000 * 0.02 = 20,000
        # Position value = 20,000 / 0.05 = 400,000
        # Max value = 1,000,000 * 0.10 = 100,000 (capped)
        # Shares = 100,000 / 75,000 = 1.33... -> 1
        assert result == 1

    def test_position_size_exact_max_position(self):
        """Test position size exactly at max position limit."""
        result = calculate_kelly_position_size(
            portfolio_value=Decimal("1000000"),
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.01"),
            stop_loss_pct=Decimal("0.05"),
            max_position_size_pct=Decimal("0.10"),
        )
        # Risk amount = 1,000,000 * 0.01 = 10,000
        # Position value = 10,000 / 0.05 = 200,000
        # Max value = 100,000 (capped)
        # Shares = 100,000 / 50,000 = 2
        assert result == 2


class TestRiskManagerIntegration:
    """Integration tests for RiskManager using pure function."""

    def test_calculate_position_size_uses_pure_function(self):
        """Test RiskManager delegates to pure function."""
        manager = RiskManager(limits=RiskLimits(), portfolio_value=Decimal("1000000"))
        result = manager.calculate_position_size(
            price=Decimal("50000"),
            risk_per_trade_pct=Decimal("0.02"),
            stop_loss_pct=Decimal("0.05"),
        )
        # Should match pure function result (capped at 10% = 2 shares)
        assert result == 2

    def test_calculate_position_size_default_stop_loss(self):
        """Test RiskManager uses default stop loss from limits."""
        limits = RiskLimits(default_stop_loss_pct=Decimal("0.05"))
        manager = RiskManager(limits=limits, portfolio_value=Decimal("1000000"))
        result = manager.calculate_position_size(
            price=Decimal("50000"), risk_per_trade_pct=Decimal("0.02")
        )
        # Capped at 10% max position size = 2 shares
        assert result == 2


class TestRiskManagerValidateOrder:
    def test_validate_order_allows_sell(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))
        result = manager.validate_order("005930", 1, Decimal("70000"), "sell")

        assert result.approved is True
        assert result.reason == "Sell order approved"
        assert result.adjusted_quantity is None

    def test_validate_order_rejects_when_position_limit_reached(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))
        manager.update_portfolio(
            portfolio_value=Decimal("1000000"), current_exposure=Decimal("0"), position_count=5
        )

        result = manager.validate_order("005930", 1, Decimal("70000"), "buy")

        assert result.approved is False
        assert result.reason == "Maximum positions (5) reached"

    def test_validate_order_rejects_when_portfolio_value_is_not_set(self):
        manager = RiskManager(portfolio_value=Decimal("0"))
        result = manager.validate_order("005930", 1, Decimal("70000"), "buy")

        assert result.approved is False
        assert result.reason == "Portfolio value not set"

    def test_validate_order_adjusts_order_for_position_limit(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))

        result = manager.validate_order("005930", 500, Decimal("1000"), "buy")

        assert result.approved is True
        assert result.adjusted_quantity == 100
        assert result.reason == "Quantity adjusted from 500 to 100"

    def test_validate_order_rejects_position_adjusted_to_zero(self):
        manager = RiskManager(
            limits=RiskLimits(max_position_size_pct=Decimal("0.001")),
            portfolio_value=Decimal("100"),
        )

        result = manager.validate_order("005930", 1, Decimal("100000"), "buy")

        assert result.approved is False
        assert "Order exceeds max position size" in result.reason

    def test_validate_order_adjusts_order_for_exposure_limit(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))
        manager.update_portfolio(
            portfolio_value=Decimal("1000000"), current_exposure=Decimal("750000"), position_count=0
        )

        result = manager.validate_order("005930", 1000, Decimal("100"), "buy")

        assert result.approved is True
        assert result.adjusted_quantity == 500
        assert result.reason == "Quantity adjusted to 500 due to exposure limit"

    def test_validate_order_rejects_when_exposure_capacity_is_zero(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))
        manager.update_portfolio(
            portfolio_value=Decimal("1000000"), current_exposure=Decimal("800000"), position_count=0
        )

        result = manager.validate_order("005930", 1, Decimal("1000"), "buy")

        assert result.approved is False
        assert "Portfolio exposure limit" in result.reason

    def test_validate_order_suggests_default_stop_loss_and_take_profit(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))

        result = manager.validate_order("005930", 1, Decimal("1000"), "buy")

        assert result.approved is True
        assert result.suggested_stop_loss == Decimal("950")
        assert result.suggested_take_profit == Decimal("1100")

    def test_validate_order_adjusts_too_tight_stop_loss(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))

        result = manager.validate_order(
            "005930", 1, Decimal("1000"), "buy", stop_loss=Decimal("990")
        )

        assert result.approved is True
        assert result.suggested_stop_loss == Decimal("980")
        assert "Stop-loss too tight" in result.reason

    def test_validate_order_adjusts_too_wide_stop_loss(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))

        result = manager.validate_order(
            "005930", 1, Decimal("1000"), "buy", stop_loss=Decimal("700")
        )

        assert result.approved is True
        assert result.suggested_stop_loss == Decimal("900")
        assert "Stop-loss too wide" in result.reason

    def test_validate_order_adjusts_too_low_take_profit(self):
        manager = RiskManager(portfolio_value=Decimal("1000000"))

        result = manager.validate_order(
            "005930", 1, Decimal("1000"), "buy", take_profit=Decimal("1020")
        )

        assert result.approved is True
        assert result.suggested_take_profit == Decimal("1050")
