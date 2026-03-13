from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
import re

from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price
from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
    cash_order,
    get_default_inquire_balance_params,
    inquire_balance,
    inquire_psbl_rvsecncl,
    order_cancel,
)
from stock_manager.adapters.broker.kis.apis.oauth.oauth import approve_websocket_key
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.adapters.broker.kis.websocket_client import (
    DEFAULT_QUOTE_TR_ID,
    ExecutionCallback,
    KISWebSocketClient,
    QuoteCallback,
    get_default_execution_notice_tr_id,
    get_kis_websocket_url,
)
from stock_manager.trading.guardrails import BrokerTruthSnapshot

_ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
_ACCOUNT_PRODUCT_CODE_PATTERN = re.compile(r"^\d{2}$")


class KISBrokerAdapter:
    """KIS 브로커 어댑터 — KISRestClient 및 KISWebSocketClient에 대한 퍼사드.

    이 클래스는 REST 및 웹소켓 클라이언트를 통합하여 주문 제출, 잔고 조회,
    실시간 시세 구독 등 KIS API의 핵심 기능을 단일 인터페이스로 제공한다.
    클라이언트 인스턴스는 생성자 주입(dependency injection)으로 전달받으며,
    제공되지 않을 경우 내부에서 기본 인스턴스를 생성한다.

    Attributes:
        config: KIS 설정 인스턴스.
        account_number: 8자리 계좌번호.
        account_product_code: 2자리 계좌상품코드.
        rest_client: REST API 클라이언트 인스턴스.
        websocket_client: 웹소켓 클라이언트 인스턴스.
    """

    def __init__(
        self,
        *,
        config: KISConfig,
        account_number: str,
        account_product_code: str = "01",
        rest_client: KISRestClient | None = None,
        websocket_client: KISWebSocketClient | None = None,
    ) -> None:
        """KISBrokerAdapter를 초기화한다.

        Args:
            config: KIS 설정 인스턴스.
            account_number: 8자리 계좌번호 (숫자만).
            account_product_code: 2자리 계좌상품코드 (기본값: "01").
            rest_client: 주입할 KISRestClient 인스턴스. None이면 내부에서 생성.
            websocket_client: 주입할 KISWebSocketClient 인스턴스. None이면 내부에서 생성.

        Raises:
            ValueError: account_number가 8자리 숫자가 아닌 경우.
            ValueError: account_product_code가 2자리 숫자가 아닌 경우.
        """
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
            websocket_url=get_kis_websocket_url(is_paper_trading=config.use_mock),
            is_paper_trading=config.use_mock,
        )

    @property
    def websocket_connected(self) -> bool:
        """웹소켓 연결 상태를 반환한다.

        Returns:
            웹소켓이 현재 연결되어 있으면 True, 그렇지 않으면 False.
        """
        return self.websocket_client.is_connected

    def authenticate(self, force_refresh: bool = False) -> KISAccessToken:
        """KIS API에 인증하여 액세스 토큰을 반환한다.

        내부 REST 클라이언트의 authenticate()를 위임 호출한다.
        토큰이 이미 유효한 경우 캐시된 토큰을 반환한다.

        Args:
            force_refresh: True면 메모리/디스크 캐시를 무시하고 새 토큰을 발급받는다.

        Returns:
            KISAccessToken 인스턴스.

        Raises:
            KISAuthenticationError: 인증에 실패한 경우.
            KISAPIError: API 요청이 실패한 경우.
        """
        return self.rest_client.authenticate(force_refresh=force_refresh)

    def make_request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
        retry_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """KIS API에 HTTP 요청을 위임한다.

        내부 REST 클라이언트의 make_request()를 그대로 위임 호출한다.

        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE).
            path: API 엔드포인트 경로 (예: "/uapi/domestic-stock/v1/quotations/inquire-price").
            params: URL 쿼리 파라미터.
            json_data: POST/PUT 요청의 JSON 본문.
            headers: 추가 HTTP 헤더 (인증 헤더와 병합됨).
            require_auth: 인증 헤더 포함 여부 (기본값: True).

        Returns:
            파싱된 JSON 응답 데이터.

        Raises:
            KISAuthenticationError: 인증이 필요하지만 인증되지 않은 경우.
            KISAPIError: API 요청이 실패한 경우.
            KISRateLimitError: API 요청 횟수 한도를 초과한 경우.
        """
        return self.rest_client.make_request(
            method=method,
            path=path,
            params=params,
            json_data=json_data,
            headers=headers,
            require_auth=require_auth,
            retry_enabled=retry_enabled,
        )

    def inquire_current_price(self, stock_code: str) -> dict[str, Any]:
        """국내 주식 현재가를 조회한다.

        Args:
            stock_code: 종목코드 (예: "005930").

        Returns:
            현재가 정보가 담긴 JSON 응답 데이터.

        Raises:
            KISAuthenticationError: 인증되지 않은 경우.
            KISAPIError: API 요청이 실패한 경우.
        """
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
        """현금 주문(매수/매도)을 제출한다.

        price가 제공되면 지정가 주문(ord_dv="00"), 제공되지 않으면 시장가 주문(ord_dv="01")으로 처리된다.

        Args:
            symbol: 종목코드 (예: "005930").
            quantity: 주문 수량.
            side: 주문 방향 ("buy" 또는 "sell").
            price: 주문 단가. None이면 시장가 주문.

        Returns:
            주문 결과가 담긴 JSON 응답 데이터.

        Raises:
            KISAuthenticationError: 인증되지 않은 경우.
            KISAPIError: 주문 요청이 실패한 경우.
        """
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
            retry_enabled=False,
        )

    def cancel_order(
        self,
        *,
        original_order_number: str,
        orgn_ord_dv: str = "00",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """기존 주문을 취소한다.

        Args:
            original_order_number: 취소할 원주문번호.
            orgn_ord_dv: 원주문 구분코드 (기본값: "00").
            **kwargs: order_cancel() 함수에 전달할 추가 파라미터.

        Returns:
            주문 취소 결과가 담긴 JSON 응답 데이터.

        Raises:
            KISAuthenticationError: 인증되지 않은 경우.
            KISAPIError: 취소 요청이 실패한 경우.
        """
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
            retry_enabled=False,
        )

    def inquire_balance(self, **params: str) -> dict[str, Any]:
        """계좌 잔고를 조회한다.

        기본 파라미터를 자동으로 설정하며, 추가 파라미터를 전달하여 덮어쓸 수 있다.

        Args:
            **params: inquire_balance() 기본 파라미터를 덮어쓸 추가 쿼리 파라미터.

        Returns:
            잔고 정보가 담긴 JSON 응답 데이터.

        Raises:
            KISAuthenticationError: 인증되지 않은 경우.
            KISAPIError: 조회 요청이 실패한 경우.
        """
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

    def inquire_open_orders(self, **params: str) -> dict[str, Any]:
        """조회 가능한 정정/취소 주문 목록을 반환한다."""
        if self.config.use_mock:
            return {"rt_cd": "0", "output": [], "output1": []}

        request_config = inquire_psbl_rvsecncl(
            cano=self.account_number,
            acnt_prdt_cd=self.account_product_code,
            **params,
        )
        return self.make_request(
            method="GET",
            path=request_config["url_path"],
            params=request_config["params"],
            headers={"tr_id": request_config["tr_id"]},
        )

    def fetch_account_truth(self) -> BrokerTruthSnapshot:
        """현재 계좌 잔고/포지션/미체결 주문을 한 번에 정규화해서 반환한다."""
        balance_response = self.inquire_balance()
        open_orders_response = self.inquire_open_orders()
        output2 = balance_response.get("output2", [])
        cash_summary = output2[0] if isinstance(output2, list) and output2 else {}
        positions = balance_response.get("output1", [])
        if not isinstance(positions, list):
            positions = []

        raw_open_orders = (
            open_orders_response.get("output")
            if isinstance(open_orders_response.get("output"), list)
            else open_orders_response.get("output1", [])
        )
        if not isinstance(raw_open_orders, list):
            raw_open_orders = []

        normalized_open_orders: list[dict[str, Any]] = []
        for item in raw_open_orders:
            if not isinstance(item, dict):
                continue
            normalized_open_orders.append(
                {
                    "broker_order_id": (
                        str(item.get("odno") or item.get("ODNO") or item.get("orgn_odno") or "")
                    ).strip()
                    or None,
                    "symbol": str(item.get("pdno") or item.get("PDNO") or "").strip().upper(),
                    "side": str(
                        item.get("sll_buy_dvsn_cd")
                        or item.get("sll_bk_dvsn")
                        or item.get("side")
                        or ""
                    ).strip(),
                    "quantity": item.get("ord_qty") or item.get("ORD_QTY") or item.get("qty"),
                    "remaining_quantity": (
                        item.get("ord_remn_qty")
                        or item.get("rmn_qty")
                        or item.get("remaining_qty")
                    ),
                    "status": str(
                        item.get("ord_stts")
                        or item.get("ord_sttus")
                        or item.get("status")
                        or ""
                    ).strip()
                    or None,
                    "raw": item,
                }
            )

        return BrokerTruthSnapshot(
            cash=cash_summary if isinstance(cash_summary, dict) else {},
            positions=tuple(item for item in positions if isinstance(item, dict)),
            open_orders=tuple(normalized_open_orders),
            fetched_at=datetime.now(timezone.utc),
            snapshot_ok=True,
        )

    def get_websocket_approval_key(self) -> str:
        """웹소켓 접속 승인키를 발급받아 반환한다.

        KIS API에 인증 후 웹소켓 연결에 필요한 승인키를 요청한다.

        Returns:
            웹소켓 접속 승인키 문자열.

        Raises:
            KISAuthenticationError: 인증에 실패한 경우.
            KISAPIError: 승인키 발급 요청이 실패하거나 응답이 유효하지 않은 경우.
        """
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
        """웹소켓 서버에 연결한다.

        승인키를 자동으로 발급받아 웹소켓 클라이언트를 연결한다.

        Raises:
            KISAuthenticationError: 인증에 실패한 경우.
            KISAPIError: 승인키 발급 또는 웹소켓 연결에 실패한 경우.
        """
        approval_key = self.get_websocket_approval_key()
        self.websocket_client.connect(
            approval_key=approval_key,
            custtype=self.config.custtype,
        )

    def disconnect_websocket(self) -> None:
        """웹소켓 연결을 종료한다.

        현재 연결된 웹소켓 클라이언트의 연결을 끊는다.
        이미 연결이 없는 경우에도 안전하게 호출할 수 있다.
        """
        self.websocket_client.disconnect()

    def subscribe_quotes(
        self,
        *,
        symbols: list[str],
        callback: QuoteCallback,
        tr_id: str = DEFAULT_QUOTE_TR_ID,
    ) -> None:
        """종목 실시간 호가를 구독한다.

        웹소켓이 연결되어 있지 않으면 자동으로 연결한 후 구독을 시작한다.

        Args:
            symbols: 구독할 종목코드 목록 (예: ["005930", "000660"]).
            callback: 호가 데이터 수신 시 호출할 콜백 함수.
            tr_id: 호가 조회 TR ID (기본값: DEFAULT_QUOTE_TR_ID).

        Raises:
            KISAuthenticationError: 웹소켓 연결 중 인증에 실패한 경우.
            KISAPIError: 웹소켓 연결 또는 구독 요청이 실패한 경우.
        """
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
        tr_id: str | None = None,
        tr_key: str = "ALL",
    ) -> None:
        """실시간 체결 내역을 구독한다.

        웹소켓이 연결되어 있지 않으면 자동으로 연결한 후 구독을 시작한다.

        Args:
            callback: 체결 데이터 수신 시 호출할 콜백 함수.
            tr_id: 체결 조회 TR ID. None이면 실전/모의 모드에 맞는 체결통보
                기본 TR ID를 사용한다.
            tr_key: 구독 대상 키 (기본값: "ALL").

        Raises:
            KISAuthenticationError: 웹소켓 연결 중 인증에 실패한 경우.
            KISAPIError: 웹소켓 연결 또는 구독 요청이 실패한 경우.
        """
        if not self.websocket_connected:
            self.connect_websocket()

        resolved_tr_id = tr_id or get_default_execution_notice_tr_id(
            is_paper_trading=self.config.use_mock
        )
        self.websocket_client.subscribe_executions(
            callback=callback,
            tr_id=resolved_tr_id,
            tr_key=tr_key,
        )

    def close(self) -> None:
        """어댑터가 보유한 모든 리소스를 해제한다.

        웹소켓 연결을 종료하고 REST 클라이언트의 HTTP 연결을 닫는다.
        """
        self.disconnect_websocket()
        self.rest_client.close()
