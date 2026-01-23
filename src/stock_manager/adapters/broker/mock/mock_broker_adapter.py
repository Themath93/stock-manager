"""Mock Broker Adapter for Testing

테스트용 Mock 브로커 어댑터로 BrokerPort 인터페이스를 인-메모리로 구현합니다.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, List

from ..port.broker_port import (
    APIError,
    AuthenticationToken,
    BrokerPort,
    ConnectionError,
    FillEvent,
    Order,
    OrderRequest,
    OrderSide,
    OrderType,
    QuoteEvent,
)

logger = logging.getLogger(__name__)


class MockBrokerAdapter(BrokerPort):
    """Mock 브로커 어댑터 (테스트용)"""

    def __init__(self):
        self._orders: list[Order] = []
        self._cash: Decimal = Decimal("100000000")  # 초기 예수금 1억 원
        self._quote_callbacks: list[Callable[[QuoteEvent], None]] = []
        self._execution_callbacks: list[Callable[[FillEvent], None]] = []
        self._connected = False
        self._authenticated = False

    def authenticate(self) -> AuthenticationToken:
        """인증 토큰 발급 (Mock)"""
        logger.info("Mock authentication successful")
        self._authenticated = True
        return AuthenticationToken(
            access_token="mock_token_12345",
            token_type="Bearer",
            expires_in=86400,
            expires_at=datetime.now(),
        )

    def place_order(self, order: OrderRequest) -> str:
        """주문 전송 (Mock)"""
        logger.info(f"Mock placing order: {order.side.value} {order.qty} {order.symbol}")

        if not self._authenticated:
            raise APIError("Not authenticated")

        # 주문 생성
        mock_order = Order(
            broker_order_id=f"MOCK_{len(self._orders)}",
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            qty=order.qty,
            price=order.price,
            status="SENT",
            created_at=datetime.now(),
        )
        self._orders.append(mock_order)

        # 즉시 체결 (Mock)
        self._simulate_fill(mock_order)

        return mock_order.broker_order_id

    def _simulate_fill(self, order: Order):
        """주문 즉시 체결 시뮬레이션 (Mock)"""
        fill = FillEvent(
            broker_order_id=order.broker_order_id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=order.price or Decimal("50000"),  # 기본 가격
            filled_at=datetime.now(),
        )

        for callback in self._execution_callbacks:
            try:
                callback(fill)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")

    def cancel_order(self, broker_order_id: str) -> bool:
        """주문 취소 (Mock)"""
        logger.info(f"Mock cancelling order: {broker_order_id}")

        for order in self._orders:
            if order.broker_order_id == broker_order_id:
                order.status = "CANCELED"
                return True

        return False

    def get_orders(self, account_id: str) -> List[Order]:
        """주문 목록 조회 (Mock)"""
        logger.info(f"Mock fetching orders for account: {account_id}")
        return self._orders

    def get_cash(self, account_id: str) -> Decimal:
        """예수금 조회 (Mock)"""
        logger.info(f"Mock fetching cash for account: {account_id}")
        return self._cash

    def subscribe_quotes(self, symbols: List[str], callback: Callable[[QuoteEvent], None]):
        """호가 구독 (Mock)"""
        logger.info(f"Mock subscribing to quotes for {len(symbols)} symbols")
        self._quote_callbacks.append(callback)

        # 호가 이벤트 시뮬레이션 (Mock)
        for symbol in symbols:
            self._simulate_quote(symbol)

    def _simulate_quote(self, symbol: str):
        """호가 시뮬레이션 (Mock)"""
        quote = QuoteEvent(
            symbol=symbol,
            bid_price=Decimal("50000"),
            ask_price=Decimal("50050"),
            bid_qty=Decimal(1000),
            ask_qty=Decimal(500),
            timestamp=datetime.now(),
        )

        for callback in self._quote_callbacks:
            try:
                callback(quote)
            except Exception as e:
                logger.error(f"Quote callback error: {e}")

    def subscribe_executions(self, callback: Callable[[FillEvent], None]):
        """체결 구독 (Mock)"""
        logger.info("Mock subscribing to executions")
        self._execution_callbacks.append(callback)

    def connect_websocket(self):
        """WebSocket 연결 (Mock)"""
        logger.info("Mock WebSocket connection")
        self._connected = True

    def disconnect_websocket(self):
        """WebSocket 연결 종료 (Mock)"""
        logger.info("Mock WebSocket disconnection")
        self._connected = False

    def reset(self):
        """Mock 상태 초기화 (테스트용)"""
        logger.info("Mock broker adapter reset")
        self._orders.clear()
        self._cash = Decimal("100000000")
        self._quote_callbacks.clear()
        self._execution_callbacks.clear()
        self._connected = False
        self._authenticated = False
