import json
import time
from decimal import Decimal
from typing import Any

import pytest

from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.adapters.broker.kis.websocket_client import (
    KISWebSocketClient,
    get_kis_websocket_url,
)


class _DummyWebSocketApp:
    def __init__(
        self,
        _url: str,
        *,
        on_open: Any,
        on_message: Any,
        on_error: Any,
        on_close: Any,
        header: list[str],
    ) -> None:
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.header = header
        self.sock = object()
        self.sent_payloads: list[dict[str, Any]] = []
        self.closed = False

    def send(self, payload: str) -> None:
        self.sent_payloads.append(json.loads(payload))

    def close(self) -> None:
        self.closed = True

    def run_forever(self) -> None:
        self.on_open(self)


class _DummyFactory:
    def __init__(self) -> None:
        self.instances: list[_DummyWebSocketApp] = []

    def __call__(
        self,
        url: str,
        *,
        on_open: Any,
        on_message: Any,
        on_error: Any,
        on_close: Any,
        header: list[str],
    ) -> _DummyWebSocketApp:
        app = _DummyWebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            header=header,
        )
        self.instances.append(app)
        return app


class _SilentWebSocketApp(_DummyWebSocketApp):
    def run_forever(self) -> None:
        return


class _SilentFactory(_DummyFactory):
    def __call__(
        self,
        url: str,
        *,
        on_open: Any,
        on_message: Any,
        on_error: Any,
        on_close: Any,
        header: list[str],
    ) -> _SilentWebSocketApp:
        app = _SilentWebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            header=header,
        )
        self.instances.append(app)
        return app


def test_get_kis_websocket_url() -> None:
    assert get_kis_websocket_url(is_paper_trading=True) == "ws://ops.koreainvestment.com:31000"
    assert get_kis_websocket_url(is_paper_trading=False) == "ws://ops.koreainvestment.com:21000"


def test_connect_replays_stored_subscriptions() -> None:
    factory = _DummyFactory()
    client = KISWebSocketClient(websocket_url="ws://test", websocket_app_factory=factory)

    client.subscribe_quotes(["005930", "  "])
    client.subscribe_executions()
    client.connect(approval_key="approval-key", timeout_sec=1.0)

    app = factory.instances[0]
    assert client.is_connected is True

    deadline = time.time() + 1.0
    while time.time() < deadline and len(app.sent_payloads) < 2:
        time.sleep(0.01)

    assert len(app.sent_payloads) == 2

    first = app.sent_payloads[0]
    assert first["header"]["approval_key"] == "approval-key"
    assert first["body"]["tr_key"] == "005930"

    second = app.sent_payloads[1]
    assert second["body"]["tr_key"] == "ALL"


def test_subscribe_quotes_when_connected_sends_immediately() -> None:
    factory = _DummyFactory()
    client = KISWebSocketClient(websocket_url="ws://test", websocket_app_factory=factory)
    client.connect(approval_key="approval-key", timeout_sec=1.0)

    app = factory.instances[0]
    client.subscribe_quotes(["005930", "000660"])

    tr_keys = [payload["body"]["tr_key"] for payload in app.sent_payloads]
    assert tr_keys == ["005930", "000660"]


def test_connect_timeout_raises_kis_api_error() -> None:
    client = KISWebSocketClient(websocket_url="ws://test", websocket_app_factory=_SilentFactory())

    with pytest.raises(KISAPIError, match="timed out"):
        client.connect(approval_key="approval-key", timeout_sec=0.1)


def test_on_message_dispatches_quote_event() -> None:
    factory = _DummyFactory()
    client = KISWebSocketClient(websocket_url="ws://test", websocket_app_factory=factory)

    received: list[Any] = []
    client.register_quote_callback(received.append)

    message = {
        "header": {"tr_id": "H0STASP0"},
        "output": {
            "mksc_shrn_iscd": "005930",
            "bidp1": "74900",
            "askp1": "75000",
            "bidq1": "100",
            "askq1": "120",
        },
    }
    client._on_message(None, json.dumps(message))

    assert len(received) == 1
    event = received[0]
    assert event.symbol == "005930"
    assert event.bid_price == Decimal("74900")
    assert event.ask_price == Decimal("75000")
    assert event.bid_quantity == Decimal("100")
    assert event.ask_quantity == Decimal("120")


def test_on_message_dispatches_execution_event() -> None:
    factory = _DummyFactory()
    client = KISWebSocketClient(websocket_url="ws://test", websocket_app_factory=factory)

    received: list[Any] = []
    client.register_execution_callback(received.append)

    message = {
        "header": {"tr_id": "H0STCNT0"},
        "output": {
            "pdno": "005930",
            "odno": "12345",
            "sll_bk_dvsn": "2",
            "cntg_pr": "75100",
            "cntg_qty": "3",
        },
    }
    client._on_message(None, json.dumps(message))

    assert len(received) == 1
    event = received[0]
    assert event.symbol == "005930"
    assert event.order_id == "12345"
    assert event.side == "buy"
    assert event.price == Decimal("75100")
    assert event.quantity == Decimal("3")


def test_on_close_schedules_reconnect() -> None:
    factory = _DummyFactory()
    client = KISWebSocketClient(
        websocket_url="ws://test",
        websocket_app_factory=factory,
        reconnect_max_attempts=1,
        reconnect_base_delay_sec=0.01,
    )
    client.connect(approval_key="approval-key", timeout_sec=1.0)

    first_instance_count = len(factory.instances)
    client._on_close(None, None, None)

    deadline = time.time() + 1.0
    while time.time() < deadline and len(factory.instances) == first_instance_count:
        time.sleep(0.01)

    assert len(factory.instances) > first_instance_count
