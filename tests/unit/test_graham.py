"""Unit tests for Graham strategy."""
from decimal import Decimal
from unittest.mock import Mock, patch
from stock_manager.trading.strategies.graham import (
    calculate_ncav_per_share,
    calculate_margin_of_safety,
    DefensiveGrahamScore,
    GrahamScreener
)


class TestGrahamNCAV:
    """Test Graham Net-Net Working Capital calculation."""

    def test_ncav_calculation(self):
        """Test basic NCAV calculation."""
        balance_sheet = {
            "output": {
                "cras_cash": "1000000000",    # 10억 cash
                "cras_scrt": "500000000",      # 5억 securities
                "cras_rcbl": "300000000",      # 3억 receivables
                "cras_invt": "200000000",      # 2억 inventory
                "tlbt": "500000000",           # 5억 liabilities
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # Expected calculation:
        # Cash: 1000M * 1.0 = 1000M
        # Securities: 500M * 1.0 = 500M
        # Receivables: 300M * 0.8 = 240M
        # Inventory: 200M * 0.7 = 140M
        # Total adjusted: 1880M
        # Less liabilities: 1880M - 500M = 1380M
        # Apply discount: 1380M * 0.66 = 910.8M
        # Per share: 910.8M / 1M = 910.8
        assert ncav > Decimal("900")
        assert ncav < Decimal("920")

    def test_ncav_with_zero_inventory(self):
        """Test NCAV calculation with no inventory."""
        balance_sheet = {
            "output": {
                "cras_cash": "1000000000",
                "cras_scrt": "0",
                "cras_rcbl": "0",
                "cras_invt": "0",
                "tlbt": "200000000",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # (1000M - 200M) * 0.66 / 1M = 528
        assert ncav == Decimal("528")

    def test_ncav_with_high_liabilities(self):
        """Test NCAV with liabilities exceeding assets."""
        balance_sheet = {
            "output": {
                "cras_cash": "100000000",
                "cras_scrt": "0",
                "cras_rcbl": "0",
                "cras_invt": "0",
                "tlbt": "500000000",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # (100M - 500M) * 0.66 / 1M = -264
        assert ncav < Decimal("0")

    def test_ncav_with_zero_shares(self):
        """Test NCAV calculation with zero shares."""
        balance_sheet = {
            "output": {
                "cras_cash": "1000000000",
                "cras_scrt": "0",
                "cras_rcbl": "0",
                "cras_invt": "0",
                "tlbt": "0",
            }
        }
        shares = 0

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        assert ncav == Decimal("0")

    def test_ncav_applies_discount_correctly(self):
        """Test that 66% discount factor is applied."""
        balance_sheet = {
            "output": {
                "cras_cash": "1000000000",
                "cras_scrt": "0",
                "cras_rcbl": "0",
                "cras_invt": "0",
                "tlbt": "0",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # 1000M * 0.66 / 1M = 660
        assert ncav == Decimal("660")

    def test_ncav_receivables_discount(self):
        """Test that receivables are discounted 20%."""
        balance_sheet = {
            "output": {
                "cras_cash": "0",
                "cras_scrt": "0",
                "cras_rcbl": "1000000000",  # 1B receivables
                "cras_invt": "0",
                "tlbt": "0",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # 1000M * 0.8 * 0.66 / 1M = 528
        assert ncav == Decimal("528")

    def test_ncav_inventory_discount(self):
        """Test that inventory is discounted 30%."""
        balance_sheet = {
            "output": {
                "cras_cash": "0",
                "cras_scrt": "0",
                "cras_rcbl": "0",
                "cras_invt": "1000000000",  # 1B inventory
                "tlbt": "0",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # 1000M * 0.7 * 0.66 / 1M = 462
        assert ncav == Decimal("462")

    def test_ncav_handles_missing_fields(self):
        """Test NCAV handles missing balance sheet fields."""
        balance_sheet = {
            "output": {
                "cras_cash": "1000000000",
                # Missing other fields
                "tlbt": "100000000",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # Should handle missing fields as 0
        # (1000M - 100M) * 0.66 / 1M = 594
        assert ncav == Decimal("594")

    def test_ncav_with_alternative_field_names(self):
        """Test NCAV with alternative field names."""
        balance_sheet = {
            "output": {
                "cras": "1000000000",  # Alternative for cras_cash
                "rcbl": "300000000",   # Alternative for cras_rcbl
                "invt": "200000000",   # Alternative for cras_invt
                "tlbt": "500000000",
            }
        }
        shares = 1000000

        ncav = calculate_ncav_per_share(balance_sheet, shares)

        # (1000M + 300M*0.8 + 200M*0.7 - 500M) * 0.66 / 1M
        # (1000M + 240M + 140M - 500M) * 0.66 / 1M = 580.8
        assert ncav > Decimal("575")
        assert ncav < Decimal("585")


class TestMarginOfSafety:
    """Test margin of safety calculation."""

    def test_margin_of_safety_positive(self):
        """Test positive margin of safety."""
        ncav = Decimal("1000")
        price = Decimal("700")

        margin = calculate_margin_of_safety(ncav, price)

        # (1000 - 700) / 1000 = 0.30
        assert margin == Decimal("0.3")

    def test_margin_of_safety_negative(self):
        """Test negative margin (price above NCAV)."""
        ncav = Decimal("1000")
        price = Decimal("1200")

        margin = calculate_margin_of_safety(ncav, price)

        # (1000 - 1200) / 1000 = -0.20
        assert margin == Decimal("-0.2")

    def test_margin_of_safety_zero(self):
        """Test zero margin (price equals NCAV)."""
        ncav = Decimal("1000")
        price = Decimal("1000")

        margin = calculate_margin_of_safety(ncav, price)

        assert margin == Decimal("0")

    def test_margin_of_safety_with_zero_ncav(self):
        """Test margin with zero NCAV."""
        ncav = Decimal("0")
        price = Decimal("1000")

        margin = calculate_margin_of_safety(ncav, price)

        assert margin == Decimal("-1")

    def test_margin_of_safety_with_negative_ncav(self):
        """Test margin with negative NCAV."""
        ncav = Decimal("-500")
        price = Decimal("1000")

        margin = calculate_margin_of_safety(ncav, price)

        assert margin == Decimal("-1")

    def test_margin_of_safety_high_discount(self):
        """Test high margin of safety (deep discount)."""
        ncav = Decimal("2000")
        price = Decimal("500")

        margin = calculate_margin_of_safety(ncav, price)

        # (2000 - 500) / 2000 = 0.75
        assert margin == Decimal("0.75")


class TestDefensiveGrahamScore:
    """Test DefensiveGrahamScore model."""

    def test_passes_all_when_all_criteria_met(self):
        """Test that score passes when all 7 criteria are met."""
        score = DefensiveGrahamScore(
            symbol="005930",
            market_cap=Decimal("3000000000000"),
            meets_size=True,
            current_ratio=Decimal("2.5"),
            debt_to_current_assets=Decimal("0.3"),
            meets_financial=True,
            years_positive_earnings=12,
            meets_stability=True,
            years_dividends=25,
            meets_dividends=True,
            eps_growth_10yr=Decimal("40"),
            meets_growth=True,
            pe_ratio=Decimal("12"),
            meets_pe=True,
            pb_ratio=Decimal("1.2"),
            pe_times_pb=Decimal("14.4"),
            meets_pb=True
        )

        assert score.passes_all is True
        assert score.criteria_passed == 7

    def test_fails_when_one_criterion_fails(self):
        """Test that score fails when any criterion fails."""
        score = DefensiveGrahamScore(
            symbol="005930",
            market_cap=Decimal("3000000000000"),
            meets_size=True,
            current_ratio=Decimal("2.5"),
            debt_to_current_assets=Decimal("0.3"),
            meets_financial=True,
            years_positive_earnings=12,
            meets_stability=True,
            years_dividends=25,
            meets_dividends=True,
            eps_growth_10yr=Decimal("40"),
            meets_growth=True,
            pe_ratio=Decimal("12"),
            meets_pe=True,
            pb_ratio=Decimal("2.0"),  # Fails P/B criterion
            pe_times_pb=Decimal("24.0"),
            meets_pb=False
        )

        assert score.passes_all is False
        assert score.criteria_passed == 6

    def test_criteria_passed_count(self):
        """Test that criteria_passed counts correctly."""
        score = DefensiveGrahamScore(
            symbol="005930",
            market_cap=Decimal("1000000000000"),
            meets_size=True,
            current_ratio=Decimal("1.5"),
            debt_to_current_assets=Decimal("0.6"),
            meets_financial=False,
            years_positive_earnings=8,
            meets_stability=False,
            years_dividends=25,
            meets_dividends=True,
            eps_growth_10yr=Decimal("40"),
            meets_growth=True,
            pe_ratio=Decimal("12"),
            meets_pe=True,
            pb_ratio=Decimal("1.2"),
            pe_times_pb=Decimal("14.4"),
            meets_pb=True
        )

        assert score.criteria_passed == 5

    def test_no_criteria_passed(self):
        """Test score with no criteria passed."""
        score = DefensiveGrahamScore(
            symbol="005930",
            market_cap=Decimal("100000000000"),
            meets_size=False,
            current_ratio=Decimal("1.0"),
            debt_to_current_assets=Decimal("0.8"),
            meets_financial=False,
            years_positive_earnings=5,
            meets_stability=False,
            years_dividends=5,
            meets_dividends=False,
            eps_growth_10yr=Decimal("10"),
            meets_growth=False,
            pe_ratio=Decimal("20"),
            meets_pe=False,
            pb_ratio=Decimal("3.0"),
            pe_times_pb=Decimal("60.0"),
            meets_pb=False
        )

        assert score.passes_all is False
        assert score.criteria_passed == 0


class TestGrahamScreener:
    """Test GrahamScreener integration."""

    def test_screener_initialization_kospi(self):
        """Test screener initialization for KOSPI."""
        client = Mock()
        screener = GrahamScreener(client, market="KOSPI")

        assert screener.market == "KOSPI"
        assert screener.min_market_cap == Decimal("2400000000000")

    def test_screener_initialization_kosdaq(self):
        """Test screener initialization for KOSDAQ."""
        client = Mock()
        screener = GrahamScreener(client, market="KOSDAQ")

        assert screener.market == "KOSDAQ"
        assert screener.min_market_cap == Decimal("500000000000")

    @patch('stock_manager.adapters.broker.kis.apis.domestic_stock.basic.inquire_current_price')
    @patch('stock_manager.adapters.broker.kis.apis.domestic_stock.info.get_balance_sheet')
    @patch('stock_manager.adapters.broker.kis.apis.domestic_stock.info.get_financial_ratio')
    def test_evaluate_success(self, mock_ratio, mock_balance, mock_price):
        """Test successful stock evaluation."""
        client = Mock()
        screener = GrahamScreener(client, market="KOSPI")

        # Mock API responses
        mock_price.return_value = {
            "rt_cd": "0",
            "output": {
                "hts_avls": "3000000000000",
                "per": "12.0",
                "pbr": "1.2"
            }
        }
        mock_balance.return_value = {"rt_cd": "0"}
        mock_ratio.return_value = {
            "rt_cd": "0",
            "output": {
                "crrt": "2.5",
                "lblt_rate": "40.0",
                "eps_grw_rt": "40.0",
                "posv_earn_yrs": "12",
                "dvdn_yrs": "25"
            }
        }

        score = screener.evaluate("005930")

        assert score is not None
        assert score.symbol == "005930"
        assert score.meets_size is True
        assert score.meets_pe is True
        assert score.meets_pb is True

    @patch('stock_manager.adapters.broker.kis.apis.domestic_stock.basic.inquire_current_price')
    def test_evaluate_api_error(self, mock_price):
        """Test evaluation with API error."""
        client = Mock()
        screener = GrahamScreener(client, market="KOSPI")

        # Mock API error
        mock_price.return_value = {"rt_cd": "1", "msg1": "API Error"}

        score = screener.evaluate("005930")

        assert score is None

    @patch('stock_manager.adapters.broker.kis.apis.domestic_stock.basic.inquire_current_price')
    def test_evaluate_exception(self, mock_price):
        """Test evaluation with exception."""
        client = Mock()
        screener = GrahamScreener(client, market="KOSPI")

        # Mock exception
        mock_price.side_effect = Exception("Connection error")

        score = screener.evaluate("005930")

        assert score is None
