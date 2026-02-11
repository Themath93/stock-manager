"""Tests for Domestic Stock Sector API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import sector


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = sector._get_tr_id("v1_국내주식-021", is_paper_trading=False)
        assert result == "FHKUP03500100"

    def test_get_tr_id_paper_trading_success(self) -> None:
        """Test getting TR_ID for paper trading (only v1_국내주식-021 supports it)."""
        result = sector._get_tr_id("v1_국내주식-021", is_paper_trading=True)
        assert result == "FHKUP03500100"

    def test_get_tr_id_unknown_api_id_raises_error(self) -> None:
        """Test that unknown API_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API_ID"):
            sector._get_tr_id("unknown_api_id", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError for unsupported APIs."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            sector._get_tr_id("v1_국내주식-045", is_paper_trading=True)


class TestIndexChartPriceAPIs:
    """Tests for index chart price APIs."""

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

    def test_get_inquire_daily_indexchartprice_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_daily_indexchartprice makes correct API call."""
        result = sector.get_inquire_daily_indexchartprice(
            mock_client,
            fid_input_iscd="001",
            fid_period_div_code="D",
        )

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "inquire-daily-indexchartprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKUP03500100"
        assert call_args.kwargs["params"]["fid_input_iscd"] == "001"
        assert call_args.kwargs["params"]["fid_period_div_code"] == "D"

    def test_get_inquire_daily_indexchartprice_paper_trading(self, mock_client: MagicMock) -> None:
        """Test get_inquire_daily_indexchartprice with paper trading (supported)."""
        result = sector.get_inquire_daily_indexchartprice(
            mock_client,
            is_paper_trading=True,
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["headers"]["tr_id"] == "FHKUP03500100"

    def test_get_inquire_time_indexchartprice_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_time_indexchartprice makes correct API call."""
        result = sector.get_inquire_time_indexchartprice(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-time-indexchartprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKUP03500200"


class TestIndexPriceAPIs:
    """Tests for index price APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {},
        }
        return client

    def test_get_inquire_index_price_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_index_price makes correct API call."""
        result = sector.get_inquire_index_price(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-index-price" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPUP02100000"

    def test_get_inquire_index_daily_price_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_index_daily_price makes correct API call."""
        result = sector.get_inquire_index_daily_price(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-index-daily-price" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPUP02120000"

    def test_get_inquire_index_category_price_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_index_category_price makes correct API call."""
        result = sector.get_inquire_index_category_price(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-index-category-price" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPUP02140000"

    def test_get_inquire_index_tickprice_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_index_tickprice makes correct API call."""
        result = sector.get_inquire_index_tickprice(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-index-tickprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPUP02110100"

    def test_get_inquire_index_timeprice_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_index_timeprice makes correct API call."""
        result = sector.get_inquire_index_timeprice(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-index-timeprice" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPUP02110200"


class TestMarketInfoAPIs:
    """Tests for market info APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {},
        }
        return client

    def test_get_inquire_vi_status_success(self, mock_client: MagicMock) -> None:
        """Test get_inquire_vi_status makes correct API call."""
        result = sector.get_inquire_vi_status(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "inquire-vi-status" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01390000"

    def test_get_chk_holiday_success(self, mock_client: MagicMock) -> None:
        """Test get_chk_holiday makes correct API call."""
        result = sector.get_chk_holiday(
            mock_client,
            bas_dt="20240101",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "chk-holiday" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "CTCA0903R"

    def test_get_market_time_success(self, mock_client: MagicMock) -> None:
        """Test get_market_time makes correct API call."""
        result = sector.get_market_time(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "market-time" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "HHMCM000002C0"


class TestExpIndexAPIs:
    """Tests for expected index APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {},
        }
        return client

    def test_get_exp_index_trend_success(self, mock_client: MagicMock) -> None:
        """Test get_exp_index_trend makes correct API call."""
        result = sector.get_exp_index_trend(
            mock_client,
            fid_input_iscd="001",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "exp-index-trend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST01840000"

    def test_get_exp_total_index_success(self, mock_client: MagicMock) -> None:
        """Test get_exp_total_index makes correct API call."""
        result = sector.get_exp_total_index(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "exp-total-index" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKUP11750000"


class TestNewsAndInterestAPIs:
    """Tests for news and interest rate APIs."""

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

    def test_get_news_title_success(self, mock_client: MagicMock) -> None:
        """Test get_news_title makes correct API call."""
        result = sector.get_news_title(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "news-title" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKST01011800"

    def test_get_news_title_with_stock_code(self, mock_client: MagicMock) -> None:
        """Test get_news_title with specific stock code."""
        result = sector.get_news_title(
            mock_client,
            fid_input_iscd="005930",
        )

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["params"]["fid_input_iscd"] == "005930"

    def test_get_comp_interest_success(self, mock_client: MagicMock) -> None:
        """Test get_comp_interest makes correct API call."""
        result = sector.get_comp_interest(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "comp-interest" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPST07020000"
