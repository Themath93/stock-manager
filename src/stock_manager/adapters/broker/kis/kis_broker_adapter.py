"""KIS OpenAPI Broker Adapter

Port/Adapter 패턴의 구현체로 BrokerPort 인터페이스를 구현합니다.
"""

import logging
from typing import Callable, List

from ...port.broker_port import (
    APIError,
    AuthenticationToken,
    BrokerPort,
    ConnectionError,
    FillEvent,
    Order,
    OrderRequest,
    QuoteEvent,
)
from .kis_config import KISConfig
from .kis_rest_client import KISRestClient
from .kis_websocket_client import KISWebSocketClient

logger = logging.getLogger(__name__)


class KISBrokerAdapter(BrokerPort):
    """한국투자증권 OpenAPI 브로커 어댑터"""

    def __init__(self, config: KISConfig):
        self.config = config
        self.rest_client = KISRestClient(config)
        self.ws_client: KISWebSocketClient | None = None
        self._approval_key: str | None = None
        self._initialized = False

    def _initialize_websocket(self) -> None:
        """WebSocket 초기화"""
        if self.ws_client is None:
            # approval_key 발급 (TODO: 실제 REST API 호출 필요)
            self._approval_key = self._get_approval_key_from_rest()
            self.ws_client = KISWebSocketClient(self.config, self._approval_key)
            self.ws_client.connect_websocket()
            self._initialized = True
            logger.info("WebSocket initialized successfully")

    def _get_approval_key_from_rest(self) -> str:
        """REST API에서 approval_key 발급

        TODO: 실제 KIS OpenAPI approval_key 발급 API 호출 필요
        """
        # 현재는 임시 값 반환
        logger.warning("Using temporary approval_key (TODO: implement real API call)")
        return "temp_approval_key"

    def authenticate(self) -> AuthenticationToken:
        """인증 토큰 발급"""
        token = self.rest_client.get_access_token()
        logger.info("Authentication successful")
        return token

    def place_order(self, order: OrderRequest) -> str:
        """주문 전송"""
        logger.info(f"Placing order: {order.side.value} {order.qty} {order.symbol}")
        broker_order_id = self.rest_client.place_order(order)
        logger.info(f"Order placed successfully: {broker_order_id}")
        return broker_order_id

    def cancel_order(self, broker_order_id: str) -> bool:
        """주문 취소"""
        logger.info(f"Cancelling order: {broker_order_id}")
        # account_id 파라미터 필요 (TODO: 개선 필요)
        # 현재는 임시 구현
        success = False
        logger.info(f"Order cancelled: {success}")
        return success

    def get_orders(self, account_id: str) -> List[Order]:
        """주문 목록 조회"""
        logger.info(f"Fetching orders for account: {account_id}")
        orders = self.rest_client.get_orders(account_id)
        logger.info(f"Found {len(orders)} orders")
        return orders

    def get_cash(self, account_id: str):
        """예수금 조회"""
        logger.info(f"Fetching cash for account: {account_id}")
        cash = self.rest_client.get_cash(account_id)
        logger.info(f"Cash balance: {cash}")
        return cash

    def subscribe_quotes(
        self,
        symbols: List[str],
        callback: Callable[[QuoteEvent], None],
    ):
        """호가 구독"""
        logger.info(f"Subscribing to quotes for {len(symbols)} symbols")

        # WebSocket이 초기화되지 않았으면 초기화
        if not self._initialized:
            self._initialize_websocket()

        if self.ws_client:
            self.ws_client.subscribe_quotes(symbols, callback)
            logger.info(f"Quote subscription successful for {len(symbols)} symbols")

    def subscribe_executions(self, callback: Callable[[FillEvent], None]):
        """체결 구독"""
        logger.info("Subscribing to executions")

        # WebSocket이 초기화되지 않았으면 초기화
        if not self._initialized:
            self._initialize_websocket()

        if self.ws_client:
            self.ws_client.subscribe_executions(callback)
            logger.info("Execution subscription successful")

    def connect_websocket(self):
        """WebSocket 연결"""
        logger.info("Connecting WebSocket...")
        if not self._initialized:
            self._initialize_websocket()
        logger.info("WebSocket connected")

    def disconnect_websocket(self):
        """WebSocket 연결 종료"""
        logger.info("Disconnecting WebSocket...")
        if self.ws_client:
            self.ws_client.disconnect_websocket()
        self._initialized = False
        logger.info("WebSocket disconnected")

    def close(self):
        """어댑터 종료"""
        logger.info("Closing broker adapter...")
        self.disconnect_websocket()
        self.rest_client.close()
        logger.info("Broker adapter closed")
