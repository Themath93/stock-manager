"""Tests for Domestic Stock Realtime API Functions.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest

from stock_manager.adapters.broker.kis.apis.domestic_stock import realtime


class TestGetTrId:
    """Tests for _get_tr_id helper function."""

    def test_get_tr_id_real_trading_success(self) -> None:
        """Test getting TR_ID for real trading."""
        result = realtime._get_tr_id("H0NXANC0", is_paper_trading=False)
        assert result == "H0NXANC0"

    def test_get_tr_id_paper_trading_success(self) -> None:
        """Test getting TR_ID for paper trading (for supported APIs)."""
        result = realtime._get_tr_id("H0STCNT0", is_paper_trading=True)
        assert result == "H0STCNT0"

    def test_get_tr_id_paper_trading_different_id(self) -> None:
        """Test getting TR_ID for paper trading with different paper ID."""
        result = realtime._get_tr_id("H0STCNI0", is_paper_trading=True)
        assert result == "H0STCNI9"

    def test_get_tr_id_unknown_tr_id_raises_error(self) -> None:
        """Test that unknown TR_ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown TR_ID key"):
            realtime._get_tr_id("UNKNOWN_TR_ID", is_paper_trading=False)

    def test_get_tr_id_paper_trading_not_supported_raises_error(self) -> None:
        """Test that paper trading raises ValueError for unsupported APIs."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime._get_tr_id("H0NXANC0", is_paper_trading=True)


class TestNXTRealtimeAPIs:
    """Tests for NXT real-time APIs."""

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

    def test_get_H0NXANC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXANC0 makes correct API call."""
        result = realtime.get_H0NXANC0(mock_client)

        assert result["rt_cd"] == "0"
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert "H0NXANC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXANC0"

    def test_get_H0NXANC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXANC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXANC0(mock_client, is_paper_trading=True)

    def test_get_H0NXCNT0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXCNT0 makes correct API call."""
        result = realtime.get_H0NXCNT0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0NXCNT0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXCNT0"

    def test_get_H0NXCNT0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXCNT0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXCNT0(mock_client, is_paper_trading=True)

    def test_get_H0NXPGM0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXPGM0 makes correct API call."""
        result = realtime.get_H0NXPGM0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0NXPGM0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXPGM0"

    def test_get_H0NXPGM0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXPGM0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXPGM0(mock_client, is_paper_trading=True)

    def test_get_H0NXASP0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXASP0 makes correct API call."""
        result = realtime.get_H0NXASP0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0NXASP0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXASP0"

    def test_get_H0NXASP0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXASP0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXASP0(mock_client, is_paper_trading=True)

    def test_get_H0NXMBC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXMBC0 makes correct API call."""
        result = realtime.get_H0NXMBC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0NXMBC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXMBC0"

    def test_get_H0NXMBC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXMBC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXMBC0(mock_client, is_paper_trading=True)

    def test_get_H0NXMKO0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0NXMKO0 makes correct API call."""
        result = realtime.get_H0NXMKO0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0NXMKO0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0NXMKO0"

    def test_get_H0NXMKO0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0NXMKO0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0NXMKO0(mock_client, is_paper_trading=True)


class TestIntegratedRealtimeAPIs:
    """Tests for integrated real-time APIs."""

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

    def test_get_H0UNANC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNANC0 makes correct API call."""
        result = realtime.get_H0UNANC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNANC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNANC0"

    def test_get_H0UNANC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNANC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNANC0(mock_client, is_paper_trading=True)

    def test_get_H0UNCNT0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNCNT0 makes correct API call."""
        result = realtime.get_H0UNCNT0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNCNT0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNCNT0"

    def test_get_H0UNCNT0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNCNT0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNCNT0(mock_client, is_paper_trading=True)

    def test_get_H0UNPGM0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNPGM0 makes correct API call."""
        result = realtime.get_H0UNPGM0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNPGM0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNPGM0"

    def test_get_H0UNPGM0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNPGM0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNPGM0(mock_client, is_paper_trading=True)

    def test_get_H0UNASP0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNASP0 makes correct API call."""
        result = realtime.get_H0UNASP0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNASP0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNASP0"

    def test_get_H0UNASP0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNASP0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNASP0(mock_client, is_paper_trading=True)

    def test_get_H0UNMBC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNMBC0 makes correct API call."""
        result = realtime.get_H0UNMBC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNMBC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNMBC0"

    def test_get_H0UNMBC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNMBC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNMBC0(mock_client, is_paper_trading=True)

    def test_get_H0UNMKO0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UNMKO0 makes correct API call."""
        result = realtime.get_H0UNMKO0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UNMKO0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UNMKO0"

    def test_get_H0UNMKO0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UNMKO0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UNMKO0(mock_client, is_paper_trading=True)


class TestKRXRealtimeAPIs:
    """Tests for KRX real-time APIs."""

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

    def test_get_H0STCNT0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STCNT0 makes correct API call."""
        result = realtime.get_H0STCNT0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STCNT0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STCNT0"

    def test_get_H0STCNT0_paper_trading(self, mock_client: MagicMock) -> None:
        """Test get_H0STCNT0 with paper trading (supported)."""
        result = realtime.get_H0STCNT0(mock_client, is_paper_trading=True)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["headers"]["tr_id"] == "H0STCNT0"

    def test_get_H0STASP0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STASP0 makes correct API call."""
        result = realtime.get_H0STASP0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STASP0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STASP0"

    def test_get_H0STASP0_paper_trading(self, mock_client: MagicMock) -> None:
        """Test get_H0STASP0 with paper trading (supported)."""
        result = realtime.get_H0STASP0(mock_client, is_paper_trading=True)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["headers"]["tr_id"] == "H0STASP0"

    def test_get_H0STCNI0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STCNI0 makes correct API call."""
        result = realtime.get_H0STCNI0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STCNI0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STCNI0"

    def test_get_H0STCNI0_paper_trading(self, mock_client: MagicMock) -> None:
        """Test get_H0STCNI0 with paper trading (uses different ID)."""
        result = realtime.get_H0STCNI0(mock_client, is_paper_trading=True)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["headers"]["tr_id"] == "H0STCNI9"


class TestAfterHoursRealtimeAPIs:
    """Tests for after-hours real-time APIs."""

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

    def test_get_H0STOAC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STOAC0 makes correct API call."""
        result = realtime.get_H0STOAC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STOAC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STOAC0"

    def test_get_H0STOAC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STOAC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STOAC0(mock_client, is_paper_trading=True)

    def test_get_H0STOAA0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STOAA0 makes correct API call."""
        result = realtime.get_H0STOAA0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STOAA0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STOAA0"

    def test_get_H0STOAA0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STOAA0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STOAA0(mock_client, is_paper_trading=True)

    def test_get_H0STOUP0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STOUP0 makes correct API call."""
        result = realtime.get_H0STOUP0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STOUP0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STOUP0"

    def test_get_H0STOUP0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STOUP0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STOUP0(mock_client, is_paper_trading=True)


class TestIndexRealtimeAPIs:
    """Tests for index real-time APIs."""

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

    def test_get_H0UPCNT0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UPCNT0 makes correct API call."""
        result = realtime.get_H0UPCNT0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UPCNT0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UPCNT0"

    def test_get_H0UPCNT0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UPCNT0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UPCNT0(mock_client, is_paper_trading=True)

    def test_get_H0UPANC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UPANC0 makes correct API call."""
        result = realtime.get_H0UPANC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UPANC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UPANC0"

    def test_get_H0UPANC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UPANC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UPANC0(mock_client, is_paper_trading=True)

    def test_get_H0UPPGM0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0UPPGM0 makes correct API call."""
        result = realtime.get_H0UPPGM0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0UPPGM0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0UPPGM0"

    def test_get_H0UPPGM0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0UPPGM0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0UPPGM0(mock_client, is_paper_trading=True)


class TestOtherKRXRealtimeAPIs:
    """Tests for other KRX real-time APIs."""

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

    def test_get_H0STANC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STANC0 makes correct API call."""
        result = realtime.get_H0STANC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STANC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STANC0"

    def test_get_H0STANC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STANC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STANC0(mock_client, is_paper_trading=True)

    def test_get_H0STMBC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STMBC0 makes correct API call."""
        result = realtime.get_H0STMBC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STMBC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STMBC0"

    def test_get_H0STMBC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STMBC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STMBC0(mock_client, is_paper_trading=True)

    def test_get_H0STPGM0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STPGM0 makes correct API call."""
        result = realtime.get_H0STPGM0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STPGM0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STPGM0"

    def test_get_H0STPGM0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STPGM0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STPGM0(mock_client, is_paper_trading=True)

    def test_get_H0STMKO0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STMKO0 makes correct API call."""
        result = realtime.get_H0STMKO0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STMKO0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STMKO0"

    def test_get_H0STMKO0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STMKO0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STMKO0(mock_client, is_paper_trading=True)


class TestETFandELWRealtimeAPIs:
    """Tests for ETF and ELW real-time APIs."""

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

    def test_get_H0STNAV0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0STNAV0 makes correct API call."""
        result = realtime.get_H0STNAV0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0STNAV0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0STNAV0"

    def test_get_H0STNAV0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0STNAV0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0STNAV0(mock_client, is_paper_trading=True)

    def test_get_H0EWCNT0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0EWCNT0 makes correct API call."""
        result = realtime.get_H0EWCNT0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0EWCNT0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0EWCNT0"

    def test_get_H0EWCNT0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0EWCNT0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0EWCNT0(mock_client, is_paper_trading=True)

    def test_get_H0EWASP0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0EWASP0 makes correct API call."""
        result = realtime.get_H0EWASP0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0EWASP0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0EWASP0"

    def test_get_H0EWASP0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0EWASP0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0EWASP0(mock_client, is_paper_trading=True)

    def test_get_H0EWANC0_success(self, mock_client: MagicMock) -> None:
        """Test get_H0EWANC0 makes correct API call."""
        result = realtime.get_H0EWANC0(mock_client)

        assert result["rt_cd"] == "0"
        call_args = mock_client.make_request.call_args
        assert "H0EWANC0" in call_args.kwargs["path"]
        assert call_args.kwargs["headers"]["tr_id"] == "H0EWANC0"

    def test_get_H0EWANC0_paper_trading_raises_error(self, mock_client: MagicMock) -> None:
        """Test get_H0EWANC0 raises error for paper trading."""
        with pytest.raises(ValueError, match="Paper trading is not supported"):
            realtime.get_H0EWANC0(mock_client, is_paper_trading=True)
