"""Tests for Domestic Stock ELW API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import elw


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = elw._get_tr_id("v1_국내주식-014", is_paper_trading=False)
        assert result == "FHKEW15010000"

    def test_get_tr_id_paper_trading_success(self) -> None:
        """Test getting TR_ID for paper trading (only v1_국내주식-014 supports it)."""
        result = elw._get_tr_id("v1_국내주식-014", is_paper_trading=True)
        assert result == "FHKEW15010000"

    def test_get_tr_id_unknown_api_id_raises_error(self) -> None:
        """Test that unknown API_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API_ID"):
            elw._get_tr_id("unknown_api_id", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError for unsupported APIs."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            elw._get_tr_id("국내주식-166", is_paper_trading=True)


class TestELWPriceAPIs:
    """Tests for ELW price APIs."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client for API testing."""
        client = MagicMock()
        client.make_request.return_value = {
            "rt_cd": "0",
            "msg_cd": "00000000",
            "msg1": "Success",
            "output": {"stck_prpr": "1000"},
        }
        return client

    def test_inquire_elw_price_success(self, mock_client: MagicMock) -> None:
        """Test inquire_elw_price makes correct API call."""
        result = elw.inquire_elw_price(mock_client, elw_code="001234")

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "inquire-elw-price" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW15010000"
        assert call_args.kwargs["params"]["fid_input_iscd"] == "001234"

    def test_inquire_elw_price_paper_trading(self, mock_client: MagicMock) -> None:
        """Test inquire_elw_price with paper trading."""
        result = elw.inquire_elw_price(mock_client, elw_code="001234", is_paper_trading=True)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW15010000"


class TestELWSearchAPIs:
    """Tests for ELW search APIs."""

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

    def test_cond_search_success(self, mock_client: MagicMock) -> None:
        """Test cond_search makes correct API call."""
        result = elw.cond_search(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "cond-search" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW15100000"


class TestELWRankingAPIs:
    """Tests for ELW ranking APIs."""

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

    def test_updown_rate_success(self, mock_client: MagicMock) -> None:
        """Test updown_rate makes correct API call."""
        result = elw.updown_rate(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "updown-rate" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02770000"

    def test_volume_rank_success(self, mock_client: MagicMock) -> None:
        """Test volume_rank makes correct API call."""
        result = elw.volume_rank(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volume-rank" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02780000"

    def test_indicator_success(self, mock_client: MagicMock) -> None:
        """Test indicator makes correct API call."""
        result = elw.indicator(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "indicator" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02790000"

    def test_sensitivity_success(self, mock_client: MagicMock) -> None:
        """Test sensitivity makes correct API call."""
        result = elw.sensitivity(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "sensitivity" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02850000"

    def test_quick_change_success(self, mock_client: MagicMock) -> None:
        """Test quick_change makes correct API call."""
        result = elw.quick_change(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "quick-change" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02870000"


class TestELWIndicatorTrendAPIs:
    """Tests for ELW indicator trend APIs."""

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

    def test_indicator_trend_ccnl_success(self, mock_client: MagicMock) -> None:
        """Test indicator_trend_ccnl makes correct API call."""
        result = elw.indicator_trend_ccnl(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "indicator-trend-ccnl" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02740100"

    def test_indicator_trend_daily_success(self, mock_client: MagicMock) -> None:
        """Test indicator_trend_daily makes correct API call."""
        result = elw.indicator_trend_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "indicator-trend-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02740200"

    def test_indicator_trend_minute_success(self, mock_client: MagicMock) -> None:
        """Test indicator_trend_minute makes correct API call."""
        result = elw.indicator_trend_minute(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "indicator-trend-minute" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02740300"


class TestELWSensitivityTrendAPIs:
    """Tests for ELW sensitivity trend APIs."""

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

    def test_sensitivity_trend_ccnl_success(self, mock_client: MagicMock) -> None:
        """Test sensitivity_trend_ccnl makes correct API call."""
        result = elw.sensitivity_trend_ccnl(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "sensitivity-trend-ccnl" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02830100"

    def test_sensitivity_trend_daily_success(self, mock_client: MagicMock) -> None:
        """Test sensitivity_trend_daily makes correct API call."""
        result = elw.sensitivity_trend_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "sensitivity-trend-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02830200"


class TestELWVolatilityTrendAPIs:
    """Tests for ELW volatility trend APIs."""

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

    def test_volatility_trend_ccnl_success(self, mock_client: MagicMock) -> None:
        """Test volatility_trend_ccnl makes correct API call."""
        result = elw.volatility_trend_ccnl(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volatility-trend-ccnl" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02840100"

    def test_volatility_trend_daily_success(self, mock_client: MagicMock) -> None:
        """Test volatility_trend_daily makes correct API call."""
        result = elw.volatility_trend_daily(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volatility-trend-daily" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02840200"

    def test_volatility_trend_minute_success(self, mock_client: MagicMock) -> None:
        """Test volatility_trend_minute makes correct API call."""
        result = elw.volatility_trend_minute(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volatility-trend-minute" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02840300"

    def test_volatility_trend_tick_success(self, mock_client: MagicMock) -> None:
        """Test volatility_trend_tick makes correct API call."""
        result = elw.volatility_trend_tick(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "volatility-trend-tick" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW02840400"


class TestELWOtherAPIs:
    """Tests for other ELW APIs."""

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

    def test_newly_listed_success(self, mock_client: MagicMock) -> None:
        """Test newly_listed makes correct API call."""
        result = elw.newly_listed(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "newly-listed" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW154800C0"

    def test_lp_trade_trend_success(self, mock_client: MagicMock) -> None:
        """Test lp_trade_trend makes correct API call."""
        result = elw.lp_trade_trend(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "lp-trade-trend" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHPEW03760000"

    def test_compare_stocks_success(self, mock_client: MagicMock) -> None:
        """Test compare_stocks makes correct API call."""
        result = elw.compare_stocks(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "compare-stocks" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW151701C0"

    def test_expiration_stocks_success(self, mock_client: MagicMock) -> None:
        """Test expiration_stocks makes correct API call."""
        result = elw.expiration_stocks(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "expiration-stocks" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW154700C0"

    def test_udrl_asset_list_success(self, mock_client: MagicMock) -> None:
        """Test udrl_asset_list makes correct API call."""
        result = elw.udrl_asset_list(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "udrl-asset-list" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW154100C0"

    def test_udrl_asset_price_success(self, mock_client: MagicMock) -> None:
        """Test udrl_asset_price makes correct API call."""
        result = elw.udrl_asset_price(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "udrl-asset-price" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "FHKEW154101C0"
