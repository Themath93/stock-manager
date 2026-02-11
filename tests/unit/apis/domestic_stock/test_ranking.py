"""Tests for Domestic Stock Ranking API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import ranking


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = ranking._get_tr_id("v1_국내주식-047", is_paper_trading=False)
        assert result == "FHPST01710000"

    def test_get_tr_id_unknown_api_id_raises_error(self) -> None:
        """Test that unknown API_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API_ID"):
            ranking._get_tr_id("unknown_api_id", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError (ranking APIs don't support it)."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            ranking._get_tr_id("v1_국내주식-047", is_paper_trading=True)


class TestVolumeAndMarketAPIs:
    """Tests for volume and market ranking APIs."""

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

    def test_get_volume_rank_success(self, mock_client: MagicMock) -> None:
        """Test get_volume_rank makes correct API call."""
        result = ranking.get_volume_rank(mock_client)

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "volume-rank" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01710000"

    def test_get_volume_rank_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_volume_rank raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            ranking.get_volume_rank(mock_client, is_paper_trading=True)

    def test_get_market_cap_success(self, mock_client: MagicMock) -> None:
        """Test get_market_cap makes correct API call."""
        result = ranking.get_market_cap(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "market-cap" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01740000"

    def test_get_market_value_success(self, mock_client: MagicMock) -> None:
        """Test get_market_value makes correct API call."""
        result = ranking.get_market_value(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "market-value" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01790000"

    def test_get_volume_power_success(self, mock_client: MagicMock) -> None:
        """Test get_volume_power makes correct API call."""
        result = ranking.get_volume_power(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volume-power" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01680000"


class TestFluctuationAndDisparityAPIs:
    """Tests for fluctuation and disparity ranking APIs."""

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

    def test_get_fluctuation_success(self, mock_client: MagicMock) -> None:
        """Test get_fluctuation makes correct API call."""
        result = ranking.get_fluctuation(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "fluctuation" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01700000"

    def test_get_disparity_success(self, mock_client: MagicMock) -> None:
        """Test get_disparity makes correct API call."""
        result = ranking.get_disparity(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "disparity" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01780000"

    def test_get_prefer_disparate_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_prefer_disparate_ratio makes correct API call."""
        result = ranking.get_prefer_disparate_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "prefer-disparate-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01770000"


class TestFinancialRankingAPIs:
    """Tests for financial ranking APIs."""

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

    def test_get_profit_asset_index_success(self, mock_client: MagicMock) -> None:
        """Test get_profit_asset_index makes correct API call."""
        result = ranking.get_profit_asset_index(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "profit-asset-index" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01730000"

    def test_get_finance_ratio_success(self, mock_client: MagicMock) -> None:
        """Test get_finance_ratio makes correct API call."""
        result = ranking.get_finance_ratio(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "finance-ratio" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01750000"

    def test_get_dividend_rate_success(self, mock_client: MagicMock) -> None:
        """Test get_dividend_rate makes correct API call."""
        result = ranking.get_dividend_rate(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "dividend-rate" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHKDB13470100"

    def test_get_credit_balance_success(self, mock_client: MagicMock) -> None:
        """Test get_credit_balance makes correct API call."""
        result = ranking.get_credit_balance(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "credit-balance" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST17010000"


class TestAfterHoursAPIs:
    """Tests for after-hours ranking APIs."""

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

    def test_get_after_hour_balance_success(self, mock_client: MagicMock) -> None:
        """Test get_after_hour_balance makes correct API call."""
        result = ranking.get_after_hour_balance(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "after-hour-balance" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01760000"

    def test_get_overtime_fluctuation_success(self, mock_client: MagicMock) -> None:
        """Test get_overtime_fluctuation makes correct API call."""
        result = ranking.get_overtime_fluctuation(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "overtime-fluctuation" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST02340000"

    def test_get_overtime_volume_success(self, mock_client: MagicMock) -> None:
        """Test get_overtime_volume makes correct API call."""
        result = ranking.get_overtime_volume(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "overtime-volume" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST02350000"


class TestOtherRankingAPIs:
    """Tests for other ranking APIs."""

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

    def test_get_top_interest_stock_success(self, mock_client: MagicMock) -> None:
        """Test get_top_interest_stock makes correct API call."""
        result = ranking.get_top_interest_stock(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "top-interest-stock" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01800000"

    def test_get_exp_trans_updown_success(self, mock_client: MagicMock) -> None:
        """Test get_exp_trans_updown makes correct API call."""
        result = ranking.get_exp_trans_updown(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "exp-trans-updown" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01820000"

    def test_get_traded_by_company_success(self, mock_client: MagicMock) -> None:
        """Test get_traded_by_company makes correct API call."""
        result = ranking.get_traded_by_company(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "traded-by-company" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01860000"

    def test_get_near_new_highlow_success(self, mock_client: MagicMock) -> None:
        """Test get_near_new_highlow makes correct API call."""
        result = ranking.get_near_new_highlow(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "near-new-highlow" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01870000"

    def test_get_quote_balance_success(self, mock_client: MagicMock) -> None:
        """Test get_quote_balance makes correct API call."""
        result = ranking.get_quote_balance(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "quote-balance" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01720000"

    def test_get_bulk_trans_num_success(self, mock_client: MagicMock) -> None:
        """Test get_bulk_trans_num makes correct API call."""
        result = ranking.get_bulk_trans_num(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "bulk-trans-num" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST190900C0"

    def test_get_short_sale_success(self, mock_client: MagicMock) -> None:
        """Test get_short_sale makes correct API call."""
        result = ranking.get_short_sale(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "short-sale" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST04820000"

    def test_get_hts_top_view_success(self, mock_client: MagicMock) -> None:
        """Test get_hts_top_view makes correct API call."""
        result = ranking.get_hts_top_view(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "hts-top-view" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHMCM000100C0"
