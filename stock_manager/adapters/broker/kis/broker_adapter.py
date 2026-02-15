from __future__ import annotations

from typing import Any, Literal
import re

from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price
from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
    cash_order,
    get_default_inquire_balance_params,
    inquire_balance,
    order_cancel,
)
from stock_manager.adapters.broker.kis.apis.oauth.oauth import approve_websocket_key
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.adapters.broker.kis.websocket_client import (
    DEFAULT_EXECUTION_TR_ID,
    DEFAULT_QUOTE_TR_ID,
    ExecutionCallback,
    KISWebSocketClient,
    QuoteCallback,
    get_kis_websocket_url,
)

_ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
_ACCOUNT_PRODUCT_CODE_PATTERN = re.compile(r"^\d{2}$")


class KISBrokerAdapter:
    def __init__(
        self,
        *,
        config: KISConfig,
        account_number: str,
        account_product_code: str = "01",
        rest_client: KISRestClient | None = None,
        websocket_client: KISWebSocketClient | None = None,
    ) -> None:
        normalized_account = account_number.strip()
        normalized_product_code = account_product_code.strip()

        if not _ACCOUNT_NUMBER_PATTERN.fullmatch(normalized_account):
            raise ValueError("account_number must be exactly 8 digits")
        if not _ACCOUNT_PRODUCT_CODE_PATTERN.fullmatch(normalized_product_code):
            raise ValueError("account_product_code must be exactly 2 digits")

        self.config = config
        self.account_number = normalized_account
        self.account_product_code = normalized_product_code
        self.rest_client = rest_client or KISRestClient(config=config)
        self.websocket_client = websocket_client or KISWebSocketClient(
            websocket_url=get_kis_websocket_url(is_paper_trading=config.use_mock)
        )

    @property
    def websocket_connected(self) -> bool:
        return self.websocket_client.is_connected

    def authenticate(self) -> KISAccessToken:
        return self.rest_client.authenticate()

    def make_request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        return self.rest_client.make_request(
            method=method,
            path=path,
            params=params,
            json_data=json_data,
            headers=headers,
            require_auth=require_auth,
        )

    def inquire_current_price(self, stock_code: str) -> dict[str, Any]:
        return inquire_current_price(
            client=self.rest_client,
            stock_code=stock_code,
            is_paper_trading=self.config.use_mock,
        )

    def place_cash_order(
        self,
        *,
        symbol: str,
        quantity: int,
        side: Literal["buy", "sell"],
        price: int | None = None,
    ) -> dict[str, Any]:
        request_config = cash_order(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            pdno=symbol,
            ord_dv="00" if price is not None else "01",
            ord_qty=quantity,
            ord_unsl="01",
            order_type=side,
            ord_prc=price,
            is_paper_trading=self.config.use_mock,
        )

        return self.make_request(
            method="POST",
            path=request_config["url_path"],
            json_data=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )

    def cancel_order(
        self,
        *,
        original_order_number: str,
        orgn_ord_dv: str = "00",
        **kwargs: Any,
    ) -> dict[str, Any]:
        request_config = order_cancel(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            orgn_odno=original_order_number,
            orgn_ord_dv=orgn_ord_dv,
            is_paper_trading=self.config.use_mock,
            **kwargs,
        )

        return self.make_request(
            method="POST",
            path=request_config["url_path"],
            json_data=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )

    def inquire_balance(self, **params: str) -> dict[str, Any]:
        query_params = get_default_inquire_balance_params()
        query_params.update(params)
        request_config = inquire_balance(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            is_paper_trading=self.config.use_mock,
            **query_params,
        )

        return self.make_request(
            method="GET",
            path=request_config["url_path"],
            params=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )

    def get_websocket_approval_key(self) -> str:
        token = self.authenticate()
        response = approve_websocket_key(
            app_key=self.config.effective_app_key.get_secret_value(),
            app_secret=self.config.effective_app_secret.get_secret_value(),
            access_token=token.access_token,
            is_paper_trading=self.config.use_mock,
            custtype=self.config.custtype,
        )

        if str(response.get("rt_cd", "1")) != "0":
            raise KISAPIError(
                message=str(response.get("msg1", "Failed to issue websocket approval key")),
                error_code=str(response.get("msg_cd", "")) or None,
                response_data=response,
            )

        approval_key = response.get("approval_key")
        if not isinstance(approval_key, str) or not approval_key.strip():
            raise KISAPIError(
                "Invalid websocket approval key response",
                response_data=response,
            )

        return approval_key.strip()

    def connect_websocket(self) -> None:
        approval_key = self.get_websocket_approval_key()
        self.websocket_client.connect(
            approval_key=approval_key,
            custtype=self.config.custtype,
        )

    def disconnect_websocket(self) -> None:
        self.websocket_client.disconnect()

    def subscribe_quotes(
        self,
        *,
        symbols: list[str],
        callback: QuoteCallback,
        tr_id: str = DEFAULT_QUOTE_TR_ID,
    ) -> None:
        if not self.websocket_connected:
            self.connect_websocket()

        self.websocket_client.subscribe_quotes(
            symbols,
            callback=callback,
            tr_id=tr_id,
        )

    def subscribe_executions(
        self,
        *,
        callback: ExecutionCallback,
        tr_id: str = DEFAULT_EXECUTION_TR_ID,
        tr_key: str = "ALL",
    ) -> None:
        if not self.websocket_connected:
            self.connect_websocket()

        self.websocket_client.subscribe_executions(
            callback=callback,
            tr_id=tr_id,
            tr_key=tr_key,
        )

    def close(self) -> None:
        self.disconnect_websocket()
        self.rest_client.close()
