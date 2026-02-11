"""Tests for Domestic Stock Analysis API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import analysis


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = analysis._get_tr_id("v1_국내주식-044", is_paper_trading=False)
        assert result == "FHPPG04650101"

    def test_get_tr_id_unknown_api_id_raises_error(self) -> None:
        """Test that unknown API_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API_ID"):
            analysis._get_tr_id("unknown_api_id", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError (analysis APIs don't support it)."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            analysis._get_tr_id("v1_국내주식-044", is_paper_trading=True)


class TestProgramTradingAPIs:
    """Tests for program trading APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_program_trade_by_stock_success(self, mock_client: MagicMock) -> None:
        """Test get_program_trade_by_stock makes correct API call."""
        result = analysis.get_program_trade_by_stock(mock_client)

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "program-trade-by-stock" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPPG04650101"

    def test_get_program_trade_by_stock_daily_success(self, mock_client: MagicMock) -> None:
        """Test get_program_trade_by_stock_daily makes correct API call."""
        result = analysis.get_program_trade_by_stock_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "program-trade-by-stock-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPPG04650201"

    def test_get_comp_program_trade_today_success(self, mock_client: MagicMock) -> None:
        """Test get_comp_program_trade_today makes correct API call."""
        result = analysis.get_comp_program_trade_today(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "comp-program-trade-today" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPPG04600101"

    def test_get_comp_program_trade_daily_success(self, mock_client: MagicMock) -> None:
        """Test get_comp_program_trade_daily makes correct API call."""
        result = analysis.get_comp_program_trade_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "comp-program-trade-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPPG04600001"

    def test_get_investor_program_trade_today_success(self, mock_client: MagicMock) -> None:
        """Test get_investor_program_trade_today makes correct API call."""
        result = analysis.get_investor_program_trade_today(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "investor-program-trade-today" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHPPG046600C1"


class TestInvestorTrendAPIs:
    """Tests for investor trend APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_investor_trend_estimate_success(self, mock_client: MagicMock) -> None:
        """Test get_investor_trend_estimate makes correct API call."""
        result = analysis.get_investor_trend_estimate(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "investor-trend-estimate" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHPTJ04160200"

    def test_get_inquire_investor_time_by_market_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_investor_time_by_market makes correct API call."""
        result = analysis.get_inquire_investor_time_by_market(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-investor-time-by-market" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPTJ04030000"

    def test_get_inquire_investor_daily_by_market_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_investor_daily_by_market makes correct API call."""
        result = analysis.get_inquire_investor_daily_by_market(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-investor-daily-by-market" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPTJ04040000"

    def test_get_investor_trade_by_stock_daily_success(self, mock_client: MagicMock) -> None:
        """Test get_investor_trade_by_stock_daily makes correct API call."""
        result = analysis.get_investor_trade_by_stock_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "investor-trade-by-stock-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPTJ04160001"


class TestForeignInstitutionAPIs:
    """Tests for foreign institution trading APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_foreign_institution_total_success(self, mock_client: MagicMock) -> None:
        """Test get_foreign_institution_total makes correct API call."""
        result = analysis.get_foreign_institution_total(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "foreign-institution-total" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPTJ04400000"

    def test_get_foreign_member_trade_estimate_success(self, mock_client: MagicMock) -> None:
        """Test get_foreign_member_trade_estimate makes correct API call."""
        result = analysis.get_foreign_member_trade_estimate(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "frgnmem-trade-estimate" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST644100C0"

    def test_get_foreign_member_trade_trend_success(self, mock_client: MagicMock) -> None:
        """Test get_foreign_member_trade_trend makes correct API call."""
        result = analysis.get_foreign_member_trade_trend(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "frgnmem-trade-trend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04320000"

    def test_get_foreign_member_purchase_trend_success(self, mock_client: MagicMock) -> None:
        """Test get_foreign_member_purchase_trend makes correct API call."""
        result = analysis.get_foreign_member_purchase_trend(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "frgnmem-pchs-trend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST644400C0"


class TestSearchAPIs:
    """Tests for search APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_psearch_title_success(self, mock_client: MagicMock) -> None:
        """Test get_psearch_title makes correct API call."""
        result = analysis.get_psearch_title(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "psearch-title" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKST03900300"

    def test_get_psearch_result_success(self, mock_client: MagicMock) -> None:
        """Test get_psearch_result makes correct API call."""
        result = analysis.get_psearch_result(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "psearch-result" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKST03900400"


class TestCreditAndShortSaleAPIs:
    """Tests for credit and short sale APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_daily_credit_balance_success(self, mock_client: MagicMock) -> None:
        """Test get_daily_credit_balance makes correct API call."""
        result = analysis.get_daily_credit_balance(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "daily-credit-balance" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04760000"

    def test_get_daily_short_sale_success(self, mock_client: MagicMock) -> None:
        """Test get_daily_short_sale makes correct API call."""
        result = analysis.get_daily_short_sale(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "daily-short-sale" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04830000"

    def test_get_daily_loan_transactions_success(self, mock_client: MagicMock) -> None:
        """Test get_daily_loan_transactions makes correct API call."""
        result = analysis.get_daily_loan_transactions(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "daily-loan-trans" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHPST074500C0"


class TestMarketDataAPIs:
    """Tests for market data APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_inquire_daily_trade_volume_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_daily_trade_volume makes correct API call."""
        result = analysis.get_inquire_daily_trade_volume(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-daily-trade-volume" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST03010800"

    def test_get_exp_price_trend_success(self, mock_client: MagicMock) -> None:
        """Test get_exp_price_trend makes correct API call."""
        result = analysis.get_exp_price_trend(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "exp-price-trend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01810000"

    def test_get_overtime_exp_trans_fluct_success(self, mock_client: MagicMock) -> None:
        """Test get_overtime_exp_trans_fluct makes correct API call."""
        result = analysis.get_overtime_exp_trans_fluct(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "overtime-exp-trans-fluct" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST11860000"

    def test_get_capture_uplow_price_success(self, mock_client: MagicMock) -> None:
        """Test get_capture_uplow_price makes correct API call."""
        result = analysis.get_capture_uplow_price(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "capture-uplowprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST130000C0"

    def test_get_tradprt_byamt_success(self, mock_client: MagicMock) -> None:
        """Test get_tradprt_byamt makes correct API call."""
        result = analysis.get_tradprt_byamt(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "tradprt-byamt" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST111900C0"

    def test_get_mktfunds_success(self, mock_client: MagicMock) -> None:
        """Test get_mktfunds makes correct API call."""
        result = analysis.get_mktfunds(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "mktfunds" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST649100C0"

    def test_get_pbar_tratio_success(self, mock_client: MagicMock) -> None:
        """Test get_pbar_tratio makes correct API call."""
        result = analysis.get_pbar_tratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "pbar-tratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01130000"

    def test_get_inquire_member_daily_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_member_daily makes correct API call."""
        result = analysis.get_inquire_member_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-member-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04540000"


class TestInterestStockAPIs:
    """Tests for interest stock APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": [],
        }
        return client

    def test_get_intstock_stocklist_by_group_success(self, mock_client: MagicMock) -> None:
        """Test get_intstock_stocklist_by_group makes correct API call."""
        result = analysis.get_intstock_stocklist_by_group(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "intstock-stocklist-by-group" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKCM113004C6"

    def test_get_intstock_grouplist_success(self, mock_client: MagicMock) -> None:
        """Test get_intstock_grouplist makes correct API call."""
        result = analysis.get_intstock_grouplist(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "intstock-grouplist" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKCM113004C7"

    def test_get_intstock_multprice_success(self, mock_client: MagicMock) -> None:
        """Test get_intstock_multprice makes correct API call."""
        result = analysis.get_intstock_multprice(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "intstock-multprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST11300006"
