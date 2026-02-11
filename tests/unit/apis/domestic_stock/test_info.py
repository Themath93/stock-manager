"""Tests for Domestic Stock Info API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import info


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = info._get_tr_id("v1_국내주식-029", is_paper_trading=False)
        assert result == "CTPF1604R"

    def test_get_tr_id_unknown_api_id_raises_error(self) -> None:
        """Test that unknown API_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API_ID"):
            info._get_tr_id("unknown_api_id", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError (info APIs don't support it)."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            info._get_tr_id("v1_국내주식-029", is_paper_trading=True)


class TestSearchInfoAPIs:
    """Tests for product/stock info APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {"data": "test"},
        }
        return client

    def test_get_search_info_success(self, mock_client: MagicMock) -> None:
        """Test get_search_info makes correct API call."""
        result = info.get_search_info(mock_client, param1="value1")

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "search-info" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "CTPF1604R"

    def test_get_search_info_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_search_info raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            info.get_search_info(mock_client, is_paper_trading=True)

    def test_get_search_stock_info_success(self, mock_client: MagicMock) -> None:
        """Test get_search_stock_info makes correct API call."""
        result = info.get_search_stock_info(mock_client)

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "search-stock-info" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "CTPF1002R"


class TestFinancialStatementAPIs:
    """Tests for financial statement APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {"balance": "test"},
        }
        return client

    def test_get_balance_sheet_success(self, mock_client: MagicMock) -> None:
        """Test get_balance_sheet makes correct API call."""
        result = info.get_balance_sheet(mock_client, fid_input_iscd="005930")

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "balance-sheet" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430100"

    def test_get_income_statement_success(self, mock_client: MagicMock) -> None:
        """Test get_income_statement makes correct API call."""
        result = info.get_income_statement(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "income-statement" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430200"

    def test_get_financial_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_financial_ratio makes correct API call."""
        result = info.get_financial_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "financial-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430300"

    def test_get_profit_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_profit_ratio makes correct API call."""
        result = info.get_profit_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "profit-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430400"

    def test_get_other_major_ratios_success(self, mock_client: MagicMock) -> None:
        """Test get_other_major_ratios makes correct API call."""
        result = info.get_other_major_ratios(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "other-major-ratios" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430500"

    def test_get_stability_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_stability_ratio makes correct API call."""
        result = info.get_stability_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "stability-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430600"

    def test_get_growth_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_growth_ratio makes correct API call."""
        result = info.get_growth_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "growth-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST66430800"


class TestCreditLendingAPIs:
    """Tests for credit and lending APIs."""

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

    def test_get_credit_by_company_success(self, mock_client: MagicMock) -> None:
        """Test get_credit_by_company makes correct API call."""
        result = info.get_credit_by_company(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "credit-by-company" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04770000"

    def test_get_lendable_by_company_success(self, mock_client: MagicMock) -> None:
        """Test get_lendable_by_company makes correct API call."""
        result = info.get_lendable_by_company(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "lendable-by-company" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "CTSC2702R"


class TestKSDInfoAPIs:
    """Tests for KSD info (corporate actions) APIs."""

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

    def test_get_paidin_capin_success(self, mock_client: MagicMock) -> None:
        """Test get_paidin_capin makes correct API call."""
        result = info.get_paidin_capin(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "paidin-capin" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669100C0"

    def test_get_bonus_issue_success(self, mock_client: MagicMock) -> None:
        """Test get_bonus_issue makes correct API call."""
        result = info.get_bonus_issue(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "bonus-issue" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669101C0"

    def test_get_dividend_success(self, mock_client: MagicMock) -> None:
        """Test get_dividend makes correct API call."""
        result = info.get_dividend(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "dividend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669102C0"

    def test_get_purreq_success(self, mock_client: MagicMock) -> None:
        """Test get_purreq makes correct API call."""
        result = info.get_purreq(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "purreq" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669103C0"

    def test_get_merger_split_success(self, mock_client: MagicMock) -> None:
        """Test get_merger_split makes correct API call."""
        result = info.get_merger_split(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "merger-split" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669104C0"

    def test_get_rev_split_success(self, mock_client: MagicMock) -> None:
        """Test get_rev_split makes correct API call."""
        result = info.get_rev_split(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "rev-split" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669105C0"

    def test_get_cap_dcrs_success(self, mock_client: MagicMock) -> None:
        """Test get_cap_dcrs makes correct API call."""
        result = info.get_cap_dcrs(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "cap-dcrs" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669106C0"

    def test_get_list_info_success(self, mock_client: MagicMock) -> None:
        """Test get_list_info makes correct API call."""
        result = info.get_list_info(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "list-info" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669107C0"

    def test_get_pub_offer_success(self, mock_client: MagicMock) -> None:
        """Test get_pub_offer makes correct API call."""
        result = info.get_pub_offer(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "pub-offer" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669108C0"

    def test_get_forfeit_success(self, mock_client: MagicMock) -> None:
        """Test get_forfeit makes correct API call."""
        result = info.get_forfeit(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "forfeit" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669109C0"

    def test_get_mand_deposit_success(self, mock_client: MagicMock) -> None:
        """Test get_mand_deposit makes correct API call."""
        result = info.get_mand_deposit(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "mand-deposit" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669110C0"

    def test_get_sharehld_meet_success(self, mock_client: MagicMock) -> None:
        """Test get_sharehld_meet makes correct API call."""
        result = info.get_sharehld_meet(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "sharehld-meet" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB669111C0"


class TestInvestmentOpinionAPIs:
    """Tests for investment opinion APIs."""

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

    def test_get_estimate_perform_success(self, mock_client: MagicMock) -> None:
        """Test get_estimate_perform makes correct API call."""
        result = info.get_estimate_perform(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "estimate-perform" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKST668300C0"

    def test_get_invest_opinion_success(self, mock_client: MagicMock) -> None:
        """Test get_invest_opinion makes correct API call."""
        result = info.get_invest_opinion(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "invest-opinion" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST663300C0"

    def test_get_invest_opbysec_success(self, mock_client: MagicMock) -> None:
        """Test get_invest_opbysec makes correct API call."""
        result = info.get_invest_opbysec(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "invest-opbysec" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST663400C0"
