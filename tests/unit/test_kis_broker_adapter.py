from unittest.mock import MagicMock, patch

import pytest

from stock_manager.adapters.broker.kis.broker_adapter import KISBrokerAdapter
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.adapters.broker.kis.websocket_client import KISWebSocketClient


@pytest.fixture
def mock_rest_client() -> MagicMock:
    client = MagicMock(spec=KISRestClient)
    client.authenticate.return_value = KISAccessToken(access_token="access-token")
    client.make_request.return_value = {"rt_cd": "0"}
    return client


@pytest.fixture
def mock_websocket_client() -> MagicMock:
    client = MagicMock(spec=KISWebSocketClient)
    client.is_connected = False
    return client


@pytest.fixture
def broker_adapter(
    kis_config: KISConfig,
    mock_rest_client: MagicMock,
    mock_websocket_client: MagicMock,
) -> KISBrokerAdapter:
    return KISBrokerAdapter(
        config=kis_config,
        account_number="12345678",
        account_product_code="01",
        rest_client=mock_rest_client,
        websocket_client=mock_websocket_client,
    )


def test_init_raises_for_invalid_account_number(kis_config: KISConfig) -> None:
    with pytest.raises(ValueError, match="8 digits"):
        KISBrokerAdapter(config=kis_config, account_number="1234")


def test_init_raises_for_invalid_account_product_code(kis_config: KISConfig) -> None:
    with pytest.raises(ValueError, match="2 digits"):
        KISBrokerAdapter(
            config=kis_config,
            account_number="12345678",
            account_product_code="1",
        )


def test_place_cash_order_calls_make_request(
    broker_adapter: KISBrokerAdapter,
    mock_rest_client: MagicMock,
) -> None:
    broker_adapter.place_cash_order(
        symbol="005930",
        quantity=2,
        side="buy",
        price=70000,
    )

    call_kwargs = mock_rest_client.make_request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["path"] == "/uapi/domestic-stock/v1/trading/order-cash"
    assert call_kwargs["json_data"]["CANO"] == "12345678"
    assert call_kwargs["json_data"]["ACNT_PRDT_CD"] == "01"
    assert call_kwargs["json_data"]["PDNO"] == "005930"
    assert call_kwargs["json_data"]["ORD_DVSN"] == "00"
    assert call_kwargs["json_data"]["ORD_UNPR"] == "70000"
    assert call_kwargs["headers"]["tr_id"] == "VTTC0012U"


def test_cancel_order_calls_make_request(
    broker_adapter: KISBrokerAdapter,
    mock_rest_client: MagicMock,
) -> None:
    broker_adapter.cancel_order(original_order_number="12345")

    call_kwargs = mock_rest_client.make_request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["path"] == "/uapi/domestic-stock/v1/trading/order-rvsecncl"
    assert call_kwargs["json_data"]["ORGN_ODNO"] == "12345"
    assert call_kwargs["headers"]["tr_id"] == "VTTC0013U"


def test_inquire_balance_calls_make_request(
    broker_adapter: KISBrokerAdapter,
    mock_rest_client: MagicMock,
) -> None:
    broker_adapter.inquire_balance(INQR_DVSN="00")

    call_kwargs = mock_rest_client.make_request.call_args.kwargs
    assert call_kwargs["method"] == "GET"
    assert call_kwargs["path"] == "/uapi/domestic-stock/v1/trading/inquire-balance"
    assert call_kwargs["params"]["CANO"] == "12345678"
    assert call_kwargs["params"]["ACNT_PRDT_CD"] == "01"
    assert call_kwargs["params"]["INQR_DVSN"] == "00"
    assert call_kwargs["headers"]["tr_id"] == "VTTC8434R"


def test_get_websocket_approval_key_success(
    broker_adapter: KISBrokerAdapter,
    kis_config: KISConfig,
) -> None:
    with patch(
        "stock_manager.adapters.broker.kis.broker_adapter.approve_websocket_key",
        return_value={"rt_cd": "0", "approval_key": "approved-key"},
    ) as mock_approve:
        key = broker_adapter.get_websocket_approval_key()

    assert key == "approved-key"
    mock_approve.assert_called_once_with(
        app_key=kis_config.effective_app_key.get_secret_value(),
        app_secret=kis_config.effective_app_secret.get_secret_value(),
        access_token="access-token",
        is_paper_trading=True,
        custtype=kis_config.custtype,
    )


def test_get_websocket_approval_key_error_response_raises(
    broker_adapter: KISBrokerAdapter,
) -> None:
    with patch(
        "stock_manager.adapters.broker.kis.broker_adapter.approve_websocket_key",
        return_value={"rt_cd": "1", "msg1": "denied", "msg_cd": "E001"},
    ):
        with pytest.raises(KISAPIError, match="denied"):
            broker_adapter.get_websocket_approval_key()


def test_connect_websocket_uses_approval_key(
    broker_adapter: KISBrokerAdapter,
    mock_websocket_client: MagicMock,
) -> None:
    with patch.object(
        broker_adapter,
        "get_websocket_approval_key",
        return_value="approved-key",
    ) as mock_get_key:
        broker_adapter.connect_websocket()

    mock_get_key.assert_called_once()
    mock_websocket_client.connect.assert_called_once_with(
        approval_key="approved-key",
        custtype="P",
    )


def test_subscribe_quotes_connects_before_subscribe(
    broker_adapter: KISBrokerAdapter,
    mock_websocket_client: MagicMock,
) -> None:
    with patch.object(broker_adapter, "connect_websocket") as mock_connect:
        broker_adapter.subscribe_quotes(symbols=["005930"], callback=MagicMock())

    mock_connect.assert_called_once()
    mock_websocket_client.subscribe_quotes.assert_called_once()


def test_subscribe_executions_connects_before_subscribe(
    broker_adapter: KISBrokerAdapter,
    mock_websocket_client: MagicMock,
) -> None:
    with patch.object(broker_adapter, "connect_websocket") as mock_connect:
        broker_adapter.subscribe_executions(callback=MagicMock())

    mock_connect.assert_called_once()
    mock_websocket_client.subscribe_executions.assert_called_once()


def test_close_disconnects_websocket_and_rest_client(
    broker_adapter: KISBrokerAdapter,
    mock_rest_client: MagicMock,
    mock_websocket_client: MagicMock,
) -> None:
    broker_adapter.close()

    mock_websocket_client.disconnect.assert_called_once()
    mock_rest_client.close.assert_called_once()
