"""Unit tests for MockBrokerAdapter"""

from decimal import Decimal

import pytest

from stock_manager.adapters.broker.mock import MockBrokerAdapter
from stock_manager.adapters.broker.port import (
    APIError,
    AuthenticationError,
    AuthenticationToken,
    FillEvent,
    OrderRequest,
    OrderSide,
    OrderType,
    QuoteEvent,
)


class TestMockBrokerAdapter:
    """MockBrokerAdapter 테스트"""

    @pytest.fixture
    def broker(self):
        """테스트용 MockBrokerAdapter"""
        broker = MockBrokerAdapter()
        # 인증 자동 실행 (대부분 테스트에서 필요)
        broker.authenticate()
        return broker

    def test_authenticate_returns_token(self, broker):
        """인증 성공 토큰 확인"""
        token = broker.authenticate()

        assert isinstance(token, AuthenticationToken)
        assert token.access_token == "mock_token_12345"
        assert token.token_type == "Bearer"
        assert token.expires_in == 86400
        assert broker._authenticated is True

    def test_place_order_returns_order_id(self, broker):
        """주문 전송 성공 주문 ID 확인"""
        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("50000"),
            idempotency_key="test_key",
        )

        order_id = broker.place_order(order)

        assert order_id.startswith("MOCK_")
        assert len(broker._orders) == 1

    def test_place_order_raises_error_when_not_authenticated(self, broker):
        """인증되지 않을 때 주문 에러"""
        # 인증 상태 초기화 (authenticate() 후)
        broker._authenticated = False

        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("10"),
            idempotency_key="test_key",
        )

        with pytest.raises(APIError):
            broker.place_order(order)

    def test_place_order_simulates_fill(self, broker):
        """주문 즉시 체결 시뮬레이션 확인"""
        fill_received = []

        def fill_callback(fill: FillEvent):
            fill_received.append(fill)

        broker.subscribe_executions(fill_callback)

        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("50000"),
            idempotency_key="test_key",
        )

        broker.place_order(order)

        # 체결 콜백 확인
        assert len(fill_received) == 1
        assert fill_received[0].symbol == "005930"
        assert fill_received[0].qty == Decimal("10")

    def test_cancel_order_success(self, broker):
        """주문 취소 성공"""
        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("50000"),
            idempotency_key="test_key",
        )

        order_id = broker.place_order(order)
        success = broker.cancel_order(order_id)

        assert success is True
        assert broker._orders[0].status == "CANCELED"

    def test_cancel_order_not_found(self, broker):
        """존재하지 않는 주문 취소 실패"""
        success = broker.cancel_order("UNKNOWN_ORDER_ID")

        assert success is False

    def test_get_orders_returns_all_orders(self, broker):
        """주문 목록 반환 확인"""
        order1 = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("50000"),
            idempotency_key="test_key1",
        )

        order2 = OrderRequest(
            account_id="1234567890",
            symbol="000660",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=Decimal("5"),
            price=Decimal("100000"),
            idempotency_key="test_key2",
        )

        broker.place_order(order1)
        broker.place_order(order2)

        orders = broker.get_orders("1234567890")

        assert len(orders) == 2

    def test_get_cash_returns_default_balance(self, broker):
        """예수금 기본값 확인"""
        cash = broker.get_cash("1234567890")

        assert cash == Decimal("100000000")

    def test_subscribe_quotes_triggers_callback(self, broker):
        """호가 구독 콜백 확인"""
        quote_received = []

        def quote_callback(quote: QuoteEvent):
            quote_received.append(quote)

        broker.subscribe_quotes(["005930"], quote_callback)

        # 콜백 등록 확인
        assert len(broker._quote_callbacks) == 1
        assert len(quote_received) == 1
        assert quote_received[0].symbol == "005930"
        assert quote_received[0].bid_price == Decimal("50000")

    def test_subscribe_executions_registers_callback(self, broker):
        """체결 구독 콜백 등록 확인"""
        execution_received = []

        def execution_callback(fill: FillEvent):
            execution_received.append(fill)

        broker.subscribe_executions(execution_callback)

        # 콜백 등록 확인
        assert len(broker._execution_callbacks) == 1

    def test_connect_websocket_sets_connected(self, broker):
        """WebSocket 연결 상태 확인"""
        broker.connect_websocket()

        assert broker._connected is True

    def test_disconnect_websocket_sets_disconnected(self, broker):
        """WebSocket 연결 해제 상태 확인"""
        broker.connect_websocket()
        broker.disconnect_websocket()

        assert broker._connected is False

    def test_reset_clears_all_state(self, broker):
        """리셋 상태 초기화 확인"""
        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("50000"),
            idempotency_key="test_key",
        )

        broker.place_order(order)
        broker.connect_websocket()
        broker.subscribe_quotes(["005930"], lambda x: None)
        broker.subscribe_executions(lambda x: None)

        # 리셋 전 상태 확인
        assert len(broker._orders) == 1
        assert broker._connected is True
        assert len(broker._quote_callbacks) == 1
        assert len(broker._execution_callbacks) == 1

        # 리셋 후 상태 확인
        broker.reset()

        assert len(broker._orders) == 0
        assert broker._connected is False
        assert len(broker._quote_callbacks) == 0
        assert len(broker._execution_callbacks) == 0
        assert broker._cash == Decimal("100000000")
        assert broker._authenticated is False
