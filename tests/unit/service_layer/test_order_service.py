"""
Unit tests for OrderService
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from src.stock_manager.service_layer.order_service import (
    OrderService,
    OrderStatus,
    OrderError,
    OrderStatusError,
    IdempotencyConflictError,
    RiskViolationError,
    RiskService,
)
from src.stock_manager.domain.order import Order, OrderRequest


class TestRiskService:
    """RiskService 테스트"""

    @pytest.fixture
    def db_connection(self):
        """테스트용 DB 연결"""
        from contextlib import contextmanager

        db = Mock()

        # Create a proper context manager mock
        cursor_mock = Mock()

        # Set up comprehensive mock responses for all test scenarios
        cursor_mock.fetchone = Mock(
            side_effect=[
                # test_create_order_success - order_id row
                [
                    1,
                    None,
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "NEW",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                # test_send_order_success - get_order_from_db
                [
                    1,
                    None,
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "NEW",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                # test_send_order_invalid_status
                [
                    1,
                    None,
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "FILLED",
                    "100",
                    "50000",
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                # test_cancel_order_success
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "SENT",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                # test_get_order
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "NEW",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                # test_invalid_status_transition
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "FILLED",
                    "100",
                    "50000",
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
            ]
        )

        cursor_mock.fetchall = Mock(
            return_value=[
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "SENT",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                [
                    2,
                    "BROKER002",
                    "unique_key_002",
                    "000660",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "PARTIAL",
                    "50",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
            ]
        )

        cursor_mock.execute = Mock()

        @contextmanager
        def mock_cursor():
            yield cursor_mock

        db.cursor = Mock(side_effect=mock_cursor)
        db.commit = Mock()
        return db

    @pytest.fixture
    def risk_service(self, db_connection):
        """테스트용 RiskService"""
        return RiskService(db_connection)

    def test_validate_order_always_passes(self, risk_service):
        """리스크 검증은 항상 통과 (placeholder)"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key001",
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

        result = risk_service.validate_order(order)

        assert result is True  # placeholder는 항상 True 반환


class TestOrderService:
    """OrderService 테스트"""

    @pytest.fixture
    def mock_broker(self):
        """테스트용 브로커"""
        broker = Mock()
        broker.place_order.return_value = "BROKER001"
        broker.cancel_order.return_value = True
        return broker

    @pytest.fixture
    def db_connection(self):
        """테스트용 DB 연결"""
        from contextlib import contextmanager

        db = Mock()

        # Create a proper context manager mock
        cursor_mock = Mock()

        # Set up fetchone and fetchall to return actual data, not Mock objects
        cursor_mock.fetchone = Mock(
            side_effect=[
                [
                    1,
                    None,
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "NEW",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "SENT",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
            ]
        )

        cursor_mock.fetchall = Mock(
            return_value=[
                [
                    1,
                    "BROKER001",
                    "unique_key_001",
                    "005930",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "SENT",
                    "0",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
                [
                    2,
                    "BROKER002",
                    "unique_key_002",
                    "000660",
                    "BUY",
                    "MARKET",
                    "100",
                    None,
                    "PARTIAL",
                    "50",
                    None,
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ],
            ]
        )

        cursor_mock.execute = Mock()

        @contextmanager
        def mock_cursor():
            yield cursor_mock

        db.cursor = Mock(side_effect=mock_cursor)
        db.commit = Mock()
        return db

    @pytest.fixture
    def order_service(self, mock_broker, db_connection):
        """테스트용 OrderService"""
        return OrderService(mock_broker, db_connection)

    def test_create_order_success(self, order_service, db_connection):
        """주문 생성 성공 테스트"""
        request = OrderRequest(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            idempotency_key="unique_key_001",
        )

        # Mock: DB에 주문 생성
        order_service.db.cursor.execute.return_value = None
        order_service.db.cursor.fetchone.return_value = [
            1,
            None,
            "unique_key_001",
            "005930",
            "BUY",
            "MARKET",
            "100",
            None,
            "NEW",
            "0",
            None,
            datetime.now(),
            datetime.now(),
            datetime.now(),
        ]

        order = order_service.create_order(request)

        assert order.id == 1
        assert order.idempotency_key == "unique_key_001"
        assert order.symbol == "005930"

    def test_create_order_duplicate_idempotency_key(self, order_service, db_connection):
        """idempotency key 중복 시 기존 주문 반환 테스트 (WT-001)"""
        request = OrderRequest(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            idempotency_key="duplicate_key_001",
        )

        # Mock: 기존 주문 조회
        existing_order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="duplicate_key_001",
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
        order_service._find_order_by_idempotency_key = Mock(return_value=existing_order)

        order = order_service.create_order(request)

        assert order == existing_order  # 기존 주문 반환

    def test_create_order_risk_violation(self, order_service):
        """리스크 위반 시 주문 거부 테스트 (WT-003)"""
        request = OrderRequest(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            idempotency_key="unique_key_002",
        )

        # Mock: DB에 주문 생성
        order_service.db.cursor.return_value.__enter__.execute.return_value = None
        order_service.db.cursor.return_value.__enter__.fetchone.return_value = [
            1,
            "BROKER001",
            "unique_key_001",
            "005930",
            "BUY",
            "MARKET",
            "100",
            None,
            "NEW",
            "0",
            None,
            datetime.now(),
            datetime.now(),
            datetime.now(),
        ]

        # Mock: 리스크 검증 실패
        order_service.risk_service.validate_order = Mock(return_value=False)

        with pytest.raises(RiskViolationError):
            order_service.create_order(request)

    def test_send_order_success(self, order_service):
        """주문 전송 성공 테스트 (ED-002)"""
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
        order_service._get_order_from_db = Mock(return_value=order)

        order_service.send_order(1)

        assert order.status == OrderStatus.SENT

    def test_send_order_invalid_status(self, order_service):
        """잘못된 상태에서 주문 전송 시 예외 테스트"""
        order = Order(
            id=1,
            broker_order_id=None,
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.FILLED,  # NEW가 아님
            filled_qty=Decimal("100"),
            avg_fill_price=Decimal("50000"),
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order_service._get_order_from_db = Mock(return_value=order)

        with pytest.raises(OrderStatusError):
            order_service.send_order(1)

    def test_process_fill_partial(self, order_service):
        """부분 체결 처리 테스트 (ED-003)"""
        fill_event = Mock(
            broker_order_id="BROKER001",
            symbol="005930",
            side="BUY",
            qty=Decimal("50"),
            price=Decimal("50000"),
            filled_at=datetime.now(),
        )

        # Mock: 주문 조회
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order_service._find_order_by_broker_order_id = Mock(return_value=order)

        # Mock: 체결 기록 생성
        order_service.db.cursor.return_value.__enter__.execute.return_value = None
        order_service.db.cursor.return_value.__enter__.fetchone.return_value = [
            1,
            1,
            "BROKER001",
            "005930",
            "BUY",
            "50",
            "50000",
            datetime.now(),
            datetime.now(),
            datetime.now(),
        ]
        order_service.db.cursor.return_value.__enter__.fetchone.side_effect = [[1], [50]]

        fill = order_service.process_fill(fill_event)

        assert fill.qty == Decimal("50")
        assert order.status == OrderStatus.PARTIAL  # 부분 체결

    def test_process_fill_complete(self, order_service):
        """완전 체결 처리 테스트 (WT-002)"""
        fill_event = Mock(
            broker_order_id="BROKER001",
            symbol="005930",
            side="BUY",
            qty=Decimal("50"),
            price=Decimal("50000"),
            filled_at=datetime.now(),
        )

        # Mock: 주문 조회 (이미 50 체결됨)
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,
            filled_qty=Decimal("50"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order_service._find_order_by_broker_order_id = Mock(return_value=order)

        # Mock: 체결 기록 생성
        order_service.db.cursor.return_value.__enter__.execute.return_value = None
        order_service.db.cursor.return_value.__enter__.fetchone.return_value = [
            1,
            1,
            "BROKER001",
            "005930",
            "BUY",
            "50",
            "50000",
            datetime.now(),
            datetime.now(),
            datetime.now(),
        ]
        order_service.db.cursor.return_value.__enter__.fetchone.side_effect = [[1], [100]]

        fill = order_service.process_fill(fill_event)

        assert fill.qty == Decimal("50")
        assert order.status == OrderStatus.FILLED  # 완전 체결

    def test_cancel_order_success(self, order_service):
        """주문 취소 성공 테스트 (ED-005)"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order_service._get_order_from_db = Mock(return_value=order)

        success = order_service.cancel_order(1)

        assert success is True
        assert order.status == OrderStatus.CANCELED

    def test_get_order(self, order_service):
        """주문 조회 테스트"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
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
        order_service._get_order_from_db = Mock(return_value=order)

        result = order_service.get_order(1)

        assert result == order
        assert result.id == 1

    def test_get_pending_orders(self, order_service):
        """미체결 주문 조회 테스트"""
        order1 = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order2 = Order(
            id=2,
            broker_order_id="BROKER002",
            idempotency_key="unique_key_002",
            symbol="000660",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.PARTIAL,
            filled_qty=Decimal("50"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        order_service.db.cursor.return_value.__enter__.fetchall.return_value = [
            [
                1,
                "BROKER001",
                "unique_key_001",
                "005930",
                "BUY",
                "MARKET",
                "100",
                None,
                "SENT",
                "0",
                None,
                datetime.now(),
                datetime.now(),
                datetime.now(),
            ],
            [
                2,
                "BROKER002",
                "unique_key_002",
                "000660",
                "BUY",
                "MARKET",
                "100",
                None,
                "PARTIAL",
                "50",
                None,
                datetime.now(),
                datetime.now(),
                datetime.now(),
            ],
        ]

        orders = order_service.get_pending_orders()

        assert len(orders) == 2
        assert orders[0].status == OrderStatus.SENT
        assert orders[1].status == OrderStatus.PARTIAL

    def test_invalid_status_transition(self, order_service):
        """잘못된 상태 전이 시 예외 테스트 (UB-001)"""
        order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="unique_key_001",
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
        order_service._get_order_from_db = Mock(return_value=order)

        # FILLED → PARTIAL (되돌리기, 불허용)
        with pytest.raises(OrderStatusError):
            order_service._update_order_status(1, OrderStatus.PARTIAL, None)
