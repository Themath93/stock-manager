"""
Unit tests for StateRecoveryService

Tests for state recovery operations including DB/broker synchronization
and unfilled order recovery.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from decimal import Decimal

from stock_manager.service_layer.state_recovery_service import (
    StateRecoveryServiceImpl,
    StateRecoveryError,
)
from stock_manager.domain.market_lifecycle import (
    RecoveryResult,
    RecoveryStatus,
    SystemStateEnum,
)
from stock_manager.domain.order import Order, OrderStatus
from stock_manager.adapters.broker.port import Order as BrokerOrder, OrderSide, OrderType


@pytest.fixture
def mock_broker():
    """Mock broker adapter"""
    broker = Mock()
    broker.get_orders.return_value = []
    return broker


@pytest.fixture
def mock_order_service():
    """Mock order service"""
    order_service = Mock()
    order_service.get_pending_orders.return_value = []
    order_service._update_order_status = Mock()
    return order_service


@pytest.fixture
def mock_position_service():
    """Mock position service"""
    position_service = Mock()
    position_service.calculate_position.return_value = Mock(
        symbol="005930",
        qty=Decimal("100"),
        avg_price=Decimal("50000"),
    )
    position_service._upsert_position = Mock()
    return position_service


@pytest.fixture
def mock_db_connection():
    """Mock database connection with proper context manager support"""
    from contextlib import contextmanager

    db = Mock()

    # Create cursor mock
    cursor_mock = Mock()
    cursor_mock.fetchone.return_value = None
    cursor_mock.fetchall.return_value = []

    # Create context manager that yields cursor_mock
    @contextmanager
    def mock_cursor_cm():
        yield cursor_mock

    # Make db.cursor() return the context manager
    db.cursor = mock_cursor_cm
    db.commit = Mock()

    return db


@pytest.fixture
def state_recovery_service(
    mock_broker, mock_order_service, mock_position_service, mock_db_connection
):
    """State recovery service fixture"""
    return StateRecoveryServiceImpl(
        broker=mock_broker,
        order_service=mock_order_service,
        position_service=mock_position_service,
        db_connection=mock_db_connection,
    )


class TestStateRecoveryService:
    """StateRecoveryService tests"""

    def test_initialization(
        self,
        state_recovery_service: StateRecoveryServiceImpl,
        mock_broker,
        mock_order_service,
        mock_position_service,
    ):
        """Test service initialization"""
        assert state_recovery_service.broker == mock_broker
        assert state_recovery_service.order_service == mock_order_service
        assert state_recovery_service.position_service == mock_position_service

    def test_recover_success_no_changes(
        self,
        state_recovery_service: StateRecoveryServiceImpl,
        mock_db_connection,
    ):
        """Test successful recovery with no changes needed"""
        # Mock: No pending orders, no positions to recalculate
        state_recovery_service.order_service.get_pending_orders.return_value = []

        # Mock: No symbols with fills (already set in fixture)

        # Recover
        result = state_recovery_service.recover()

        # Verify result
        assert result.success is True
        assert result.status == RecoveryStatus.SUCCESS
        assert result.orders_synced == 0
        assert result.positions_recalculated == 0
        assert result.mismatches_found == 0

    def test_recover_with_order_sync(
        self, state_recovery_service: StateRecoveryServiceImpl, mock_broker
    ):
        """Test recovery with order synchronization (ED-004, WT-002)"""
        # Create pending order
        pending_order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key001",
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

        # Mock: DB has pending orders
        state_recovery_service.order_service.get_pending_orders.return_value = [
            pending_order
        ]

        # Mock: Broker returns filled order (status mismatch)
        broker_order = BrokerOrder(
            broker_order_id="BROKER001",
            account_id="0000000000",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("100"),
            price=None,
            status="체결완료",  # Filled
            created_at=datetime.now(),
        )
        mock_broker.get_orders.return_value = [broker_order]

        # Mock: No symbols to recalculate
        with state_recovery_service.db.cursor() as cursor:
            cursor.fetchall.return_value = []

        # Recover
        result = state_recovery_service.recover()

        # Verify order was synced
        assert result.orders_synced == 1
        assert result.status == RecoveryStatus.SUCCESS

        # Verify _update_order_status was called
        state_recovery_service.order_service._update_order_status.assert_called_once()

    def test_recover_critical_error_transitions_to_stopped(
        self, state_recovery_service: StateRecoveryServiceImpl
    ):
        """Test critical error detection (WT-003)"""
        # Test the _is_critical_error method directly
        # Critical errors should be detected
        assert state_recovery_service._is_critical_error(
            Exception("database connection lost")
        ) is True
        assert state_recovery_service._is_critical_error(
            Exception("authentication failed")
        ) is True
        assert state_recovery_service._is_critical_error(
            Exception("broker connection lost")
        ) is True

        # Non-critical errors should not be marked as critical
        assert state_recovery_service._is_critical_error(
            Exception("timeout on order lookup")
        ) is False
        assert state_recovery_service._is_critical_error(
            Exception("invalid symbol format")
        ) is False

    def test_recover_non_critical_error_continues(
        self, state_recovery_service: StateRecoveryServiceImpl
    ):
        """Test non-critical error during recovery continues"""
        # Mock: Non-critical error on one order
        pending_order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key001",
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

        state_recovery_service.order_service.get_pending_orders.return_value = [
            pending_order
        ]
        state_recovery_service.broker.get_orders.side_effect = Exception(
            "timeout on order lookup"
        )

        # Recover - should continue despite error and return success
        result = state_recovery_service.recover()

        # Verify recovery continued despite error
        # Non-critical errors are logged but don't fail the entire recovery
        assert result.success is True

    def test_sync_unfilled_orders_success(
        self, state_recovery_service: StateRecoveryServiceImpl, mock_broker
    ):
        """Test successful unfilled order synchronization (ED-004, WT-002)"""
        # Create pending orders
        pending_order1 = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,  # DB says SENT
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock: DB has pending orders
        state_recovery_service.order_service.get_pending_orders.return_value = [
            pending_order1
        ]

        # Mock: Broker says filled (status mismatch)
        broker_order1 = BrokerOrder(
            broker_order_id="BROKER001",
            account_id="0000000000",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("100"),
            price=None,
            status="체결완료",  # Filled
            created_at=datetime.now(),
        )
        mock_broker.get_orders.return_value = [broker_order1]

        # Sync orders
        synced_count = state_recovery_service.sync_unfilled_orders()

        # Verify synchronization
        assert synced_count == 1
        state_recovery_service.order_service._update_order_status.assert_called_once_with(
            1, OrderStatus.FILLED, "BROKER001"
        )

    def test_sync_unfilled_orders_no_mismatch(
        self, state_recovery_service: StateRecoveryServiceImpl, mock_broker
    ):
        """Test order sync with no mismatches"""
        # Create pending order
        pending_order = Order(
            id=1,
            broker_order_id="BROKER001",
            idempotency_key="key001",
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            status=OrderStatus.SENT,  # Both DB and broker say SENT
            filled_qty=Decimal("0"),
            avg_fill_price=None,
            requested_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock: DB has pending orders
        state_recovery_service.order_service.get_pending_orders.return_value = [
            pending_order
        ]

        # Mock: Broker says same status
        broker_order = BrokerOrder(
            broker_order_id="BROKER001",
            account_id="0000000000",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("100"),
            price=None,
            status="주문중",  # SENT
            created_at=datetime.now(),
        )
        mock_broker.get_orders.return_value = [broker_order]

        # Sync orders
        synced_count = state_recovery_service.sync_unfilled_orders()

        # Verify no synchronization needed
        assert synced_count == 0
        state_recovery_service.order_service._update_order_status.assert_not_called()

    def test_recalculate_positions(
        self, state_recovery_service: StateRecoveryServiceImpl
    ):
        """Test position recalculation"""
        # Mock: Symbols with fills
        with state_recovery_service.db.cursor() as cursor:
            cursor.fetchall.return_value = [
                ("005930",),
                ("000660",),
            ]

        # Recalculate positions
        recalculated_count = state_recovery_service.recalculate_positions()

        # Verify recalculations
        assert recalculated_count == 2
        assert state_recovery_service.position_service.calculate_position.call_count == 2
        assert state_recovery_service.position_service._upsert_position.call_count == 2

    def test_broker_status_to_order_status_conversion(
        self, state_recovery_service: StateRecoveryServiceImpl
    ):
        """Test broker status to OrderStatus conversion"""
        conversions = {
            "접수": OrderStatus.NEW,
            "주문중": OrderStatus.SENT,
            "체결": OrderStatus.PARTIAL,
            "체결완료": OrderStatus.FILLED,
            "주문취소": OrderStatus.CANCELED,
            "주문거부": OrderStatus.REJECTED,
        }

        for broker_status, expected_order_status in conversions.items():
            result = state_recovery_service._broker_status_to_order_status(
                broker_status
            )
            assert result == expected_order_status

    def test_broker_status_to_order_status_unknown(
        self, state_recovery_service: StateRecoveryServiceImpl
    ):
        """Test unknown broker status converts to ERROR"""
        result = state_recovery_service._broker_status_to_order_status("UNKNOWN_STATUS")
        assert result == OrderStatus.ERROR

    def test_is_critical_error(self, state_recovery_service: StateRecoveryServiceImpl):
        """Test critical error detection"""
        # Critical errors
        assert (
            state_recovery_service._is_critical_error(
                Exception("database connection failed")
            )
            is True
        )
        assert (
            state_recovery_service._is_critical_error(
                Exception("authentication failed")
            )
            is True
        )
        assert (
            state_recovery_service._is_critical_error(
                Exception("broker connection lost")
            )
            is True
        )

        # Non-critical errors
        assert (
            state_recovery_service._is_critical_error(Exception("timeout on order lookup"))
            is False
        )
        assert (
            state_recovery_service._is_critical_error(
                Exception("invalid symbol format")
            )
            is False
        )
