from __future__ import annotations

from unittest.mock import MagicMock

from stock_manager.trading.executor import OrderExecutor


def test_buy_uses_client_make_request(monkeypatch) -> None:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg1": "정상처리",
        "output": {"ODNO": "0000012345"},
    }

    request_config = {
        "tr_id": "TTTC0012U",
        "url_path": "/uapi/domestic-stock/v1/trading/order-cash",
        "params": {
            "CANO": "12345678",
            "ACNT_PRDT_CD": "01",
            "PDNO": "005930",
            "ORD_DVSN": "00",
            "ORD_QTY": "10",
            "ORD_UNPR": "70000",
            "EXCG_ID_DVSN_CD": "KRX",
        },
    }

    monkeypatch.setattr(
        "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order",
        lambda **_: request_config,
    )

    executor = OrderExecutor(
        client=client,
        account_number="12345678",
        account_product_code="01",
        is_paper_trading=False,
    )
    result = executor.buy("005930", 10, 70000, idempotency_key="idem-1")

    assert result.success is True
    assert result.broker_order_id == "0000012345"
    client.make_request.assert_called_once_with(
        method="POST",
        path="/uapi/domestic-stock/v1/trading/order-cash",
        json_data=request_config["params"],
        headers={"tr_id": "TTTC0012U"},
    )


def test_extracts_broker_order_id_from_lowercase_key(monkeypatch) -> None:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg1": "정상처리",
        "output": {"odno": "lowercase-odno"},
    }

    monkeypatch.setattr(
        "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order",
        lambda **_: {
            "tr_id": "TTTC0012U",
            "url_path": "/uapi/domestic-stock/v1/trading/order-cash",
            "params": {},
        },
    )

    executor = OrderExecutor(
        client=client,
        account_number="12345678",
        account_product_code="01",
        is_paper_trading=False,
    )
    result = executor.buy("005930", 1, 70000, idempotency_key="idem-2")

    assert result.success is True
    assert result.broker_order_id == "lowercase-odno"


def test_returns_failure_message_on_broker_error(monkeypatch) -> None:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "1",
        "msg1": "주문 실패",
    }

    monkeypatch.setattr(
        "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order",
        lambda **_: {
            "tr_id": "TTTC0012U",
            "url_path": "/uapi/domestic-stock/v1/trading/order-cash",
            "params": {},
        },
    )

    executor = OrderExecutor(
        client=client,
        account_number="12345678",
        account_product_code="01",
        is_paper_trading=False,
    )
    result = executor.buy("005930", 1, 70000, idempotency_key="idem-3")

    assert result.success is False
    assert result.message == "주문 실패"


def test_duplicate_idempotency_key_blocks_second_submission(monkeypatch) -> None:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg1": "정상처리",
        "output": {"ODNO": "first-order"},
    }

    monkeypatch.setattr(
        "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order",
        lambda **_: {
            "tr_id": "TTTC0012U",
            "url_path": "/uapi/domestic-stock/v1/trading/order-cash",
            "params": {},
        },
    )

    executor = OrderExecutor(
        client=client,
        account_number="12345678",
        account_product_code="01",
        is_paper_trading=False,
    )

    first = executor.buy("005930", 1, 70000, idempotency_key="dup-key")
    second = executor.buy("005930", 1, 70000, idempotency_key="dup-key")

    assert first.success is True
    assert second.success is False
    assert "Duplicate order" in second.message
    assert client.make_request.call_count == 1
