"""
Domain model tests for Order, Fill, OrderStatus
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.stock_manager.domain.order import Order, Fill, OrderRequest, OrderStatus


class TestOrderStatus:
    """OrderStatus Enum 테스트"""

    def test_order_status_values(self):
        """OrderStatus enum 값 확인"""
        assert OrderStatus.NEW.value == "NEW"
        assert OrderStatus.SENT.value == "SENT"
        assert OrderStatus.PARTIAL.value == "PARTIAL"
        assert OrderStatus.FILLED.value == "FILLED"
        assert OrderStatus.CANCELED.value == "CANCELED"
        assert OrderStatus.REJECTED.value == "REJECTED"
        assert OrderStatus.ERROR.value == "ERROR"


class TestOrderRequest:
    """OrderRequest dataclass 테스트"""

    def test_create_order_request_market(self):
        """시장가 주문 요청 생성"""
        request = OrderRequest(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            idempotency_key="unique_key_001",
        )

        assert request.symbol == "005930"
        assert request.side == "BUY"
        assert request.order_type == "MARKET"
        assert request.qty == Decimal("100")
        assert request.price is None
        assert request.idempotency_key == "unique_key_001"

    def test_create_order_request_limit(self):
        """지정가 주문 요청 생성"""
        request = OrderRequest(
            symbol="000660",
            side="SELL",
            order_type="LIMIT",
            qty=Decimal("50"),
            price=Decimal("100000"),
            idempotency_key="unique_key_002",
        )

        assert request.symbol == "000660"
        assert request.side == "SELL"
        assert request.order_type == "LIMIT"
        assert request.qty == Decimal("50")
        assert request.price == Decimal("100000")
        assert request.idempotency_key == "unique_key_002"


class TestOrder:
    """Order dataclass 테스트"""

    def test_create_order_new(self):
        """NEW 상태 주문 생성"""
        order = Order(
            id=1,
            broker_order_id=None,
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.NEW,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.id == 1
        assert order.broker_order_id is None
        assert order.status == OrderStatus.NEW
        assert order.filled_qty == Decimal("0")

    def test_create_order_sent(self):
        """SENT 상태 주문 생성"""
        order = Order(
            id=2,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_002",
            symbol="000660",
            side="SELL",
            order_type="LIMIT",
            qty=Decimal("50"),
            price=Decimal("100000"),
            status=OrderStatus.SENT,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.broker_order_id == "BROKER001"
        assert order.status == OrderStatus.SENT

    def test_create_order_partial(self):
        """PARTIAL 상태 주문 생성 (부분 체결)"""
        order = Order(
            id=3,
            broker_order_id="BROKER002",
            idempotency_key="unique_key_003",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.PARTIAL,
            filled_qty=Decimal("50"),
            avg_fill_price=Decimal("50000"),
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.status == OrderStatus.PARTIAL
        assert order.filled_qty == Decimal("50")
        assert order.avg_fill_price == Decimal("50000")

    def test_create_order_filled(self):
        """FILLED 상태 주문 생성 (완전 체결)"""
        order = Order(
            id=4,
            broker_order_id="BROKER003",
            idempotency_key="unique_key_004",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("100"),
            avg_fill_price=Decimal("50000"),
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Decimal("100")
        assert order.avg_fill_price == Decimal("50000")

    def test_is_fully_filled_true(self):
        """완전 체결 여부 확인 (True)"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("100"),
            avg_fill_price=Decimal("50000"),
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.filled_qty == order.qty

    def test_is_fully_filled_false(self):
        """완전 체결 여부 확인 (False - 부분 체결)"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.PARTIAL,
            filled_qty=Decimal("50"),
            avg_fill_price=Decimal("50000"),
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert order.filled_qty < order.qty


class TestFill:
    """Fill dataclass 테스트"""

    def test_create_fill(self):
        """체결 레코드 생성"""
        fill = Fill(
            id=1,
            order_id=1,
            broker_fill_id="BROKER_FILL_001",
            symbol="005930",
            side="BUY",
            qty=Decimal("50"),
            price=Decimal("50000"),
            filled_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert fill.id == 1
        assert fill.order_id == 1
        assert fill.broker_fill_id == "BROKER_FILL_001"
        assert fill.symbol == "005930"
        assert fill.side == "BUY"
        assert fill.qty == Decimal("50")
        assert fill.price == Decimal("50000")
