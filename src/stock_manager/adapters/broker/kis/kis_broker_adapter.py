"""KIS OpenAPI Broker Adapter

Port/Adapter 패턴의 구현체로 BrokerPort 인터페이스를 구현합니다.
"""

import logging
from typing import Callable, List, Optional

from ..port.broker_port import (
    APIError,
    AuthenticationError,
    AuthenticationToken,
    BrokerPort,
    FillEvent,
    Order,
    OrderRequest,
    QuoteEvent,
)
from .kis_config import KISConfig
from .kis_rest_client import KISRestClient
from .kis_websocket_client import KISWebSocketClient
from ....utils.security import mask_account_id

logger = logging.getLogger(__name__)


class KISBrokerAdapter(BrokerPort):
    """한국투자증권 OpenAPI 브로커 어댑터"""

    # TASK-002: SPEC-BACKEND-API-001-P3 Milestone 1 - Add account_id parameter
    def __init__(self, config: KISConfig, account_id: str):
        """Initialize KISBrokerAdapter with config and account_id.

        Args:
            config: KIS configuration
            account_id: 10-digit account ID for trading

        Raises:
            ValueError: If account_id is None or empty
        """
        if not account_id:
            raise ValueError("account_id is required and cannot be None or empty")

        self.config = config
        self.account_id = account_id
        self.rest_client = KISRestClient(config)
        self.ws_client: Optional[KISWebSocketClient] = None
        self._approval_key: Optional[str] = None
        self._initialized = False

        logger.info(f"KISBrokerAdapter initialized with account_id: {mask_account_id(account_id)}")

    # TAG-002: SPEC-BACKEND-API-001 ED-002 WebSocket 초기화
    def _initialize_websocket(self) -> None:
        """WebSocket 초기화"""
        if self.ws_client is None:
            # approval_key 발급
            self._approval_key = self._get_approval_key_from_rest()
            self.ws_client = KISWebSocketClient(self.config, self._approval_key)
            self.ws_client.connect_websocket()
            self._initialized = True
            logger.info("WebSocket initialized successfully")

    # TAG-001: SPEC-BACKEND-API-001 NEW-001 WebSocket approval_key 발급
    def _get_approval_key_from_rest(self) -> str:
        """REST API에서 approval_key 발급

        KIS OpenAPI /oauth2/Approval 엔드포인트를 호출하여
        WebSocket 연결에 필요한 approval_key를 발급받습니다.

        Returns:
            str: 발급된 approval_key

        Raises:
            AuthenticationError: 발급 실패 시
        """
        try:
            approval_key = self.rest_client.get_approval_key()
            logger.info(f"Approval key received: {approval_key[:8]}...")
            return approval_key
        except AuthenticationError as e:
            logger.error(f"Failed to get approval key: {e}")
            raise

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

    # TASK-003: SPEC-BACKEND-API-001-P3 Milestone 1 - Implement cancel_order
    def cancel_order(self, broker_order_id: str) -> bool:
        """주문 취소

        Args:
            broker_order_id: 취소할 주문 ID

        Returns:
            bool: 취소 성공 여부

        Raises:
            APIError: 취소 실패 시
        """
        logger.info(f"Cancelling order: {broker_order_id} for account: {mask_account_id(self.account_id)}")
        try:
            success = self.rest_client.cancel_order(broker_order_id, self.account_id)
            logger.info(f"Order cancelled: {broker_order_id}, success: {success}")
            return success
        except Exception as e:
            logger.error(f"Failed to cancel order {broker_order_id}: {e}")
            raise APIError(f"Cancel order failed: {e}")

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

    def get_stock_balance(self, account_id: str) -> list[dict]:
        """주식잔고 조회"""
        logger.info(f"Fetching stock balance for account: {account_id}")
        balance = self.rest_client.get_stock_balance(account_id)
        logger.info(f"Stock balance found: {len(balance)} positions")
        return balance

    # TAG-003: SPEC-BACKEND-API-001 ED-003 호가 구독
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

    # TAG-004: SPEC-BACKEND-API-001 ED-003 체결 구독
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
