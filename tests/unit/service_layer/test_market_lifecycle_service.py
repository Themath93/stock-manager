"""
Unit tests for MarketLifecycleService

Tests for market lifecycle operations including state transitions,
market open/close processes, and recovery operations.
"""

import pytest
from datetime import datetime, time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from stock_manager.service_layer.market_lifecycle_service import (
    MarketLifecycleServiceImpl,
    MarketOpenError,
    MarketCloseError,
    InvalidStateTransitionError,
)
from stock_manager.domain.market_lifecycle import (
    SystemState,
    SystemStateEnum,
    RecoveryStatus,
)
from stock_manager.domain.order import OrderStatus


@pytest.fixture
def mock_broker():
    """Mock broker adapter"""
    broker = Mock()
    broker.authenticate.return_value = Mock(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600,
        expires_at=datetime.now(),
    )
    broker.get_orders.return_value = []
    broker.get_cash.return_value = Decimal("100000000")
    broker.connect_websocket.return_value = None
    broker.disconnect_websocket.return_value = None
    return broker


@pytest.fixture
def mock_order_service():
    """Mock order service"""
    order_service = Mock()
    order_service.get_pending_orders.return_value = []
    return order_service


@pytest.fixture
def mock_position_service():
    """Mock position service"""
    position_service = Mock()
    position_service.get_all_positions.return_value = []
    position_service.calculate_position.return_value = Mock(
        symbol="005930",
        qty=Decimal("100"),
        avg_price=Decimal("50000"),
    )
    return position_service


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    from contextlib import contextmanager

    db = Mock()

    # Create cursor mock
    cursor_mock = Mock()
    cursor_mock.fetchone.return_value = None  # No existing state
    cursor_mock.fetchall.return_value = []

    @contextmanager
    def mock_cursor():
        yield cursor_mock

    db.cursor = mock_cursor
    db.commit = Mock()

    return db


@pytest.fixture
def market_lifecycle_service(
    mock_broker, mock_order_service, mock_position_service, mock_db_connection
):
    """Market lifecycle service fixture"""
    return MarketLifecycleServiceImpl(
        broker=mock_broker,
        order_service=mock_order_service,
        position_service=mock_position_service,
        db_connection=mock_db_connection,
        market_open_time=time(8, 30, 0),
        market_close_time=time(15, 30, 0),
    )


class TestSystemState:
    """SystemState domain model tests"""

    def test_initial_state_creation(self):
        """Test creating initial system state"""
        state = SystemState(
            state=SystemStateEnum.OFFLINE,
            recovery_status=RecoveryStatus.SUCCESS,
        )

        assert state.state == SystemStateEnum.OFFLINE
        assert state.market_open_at is None
        assert state.market_closed_at is None
        assert state.last_recovery_at is None
        assert state.recovery_status == RecoveryStatus.SUCCESS

    def test_is_trading_allowed_ready(self):
        """Test trading allowed in READY state"""
        state = SystemState(state=SystemStateEnum.READY)
        assert state.is_trading_allowed() is True

    def test_is_trading_allowed_trading(self):
        """Test trading allowed in TRADING state"""
        state = SystemState(state=SystemStateEnum.TRADING)
        assert state.is_trading_allowed() is True

    def test_is_trading_allowed_stopped(self):
        """Test trading blocked in STOPPED state (UB-004)"""
        state = SystemState(state=SystemStateEnum.STOPPED)
        assert state.is_trading_allowed() is False

    def test_is_trading_allowed_closed(self):
        """Test trading blocked in CLOSED state"""
        state = SystemState(state=SystemStateEnum.CLOSED)
        assert state.is_trading_allowed() is False

    def test_is_market_open(self):
        """Test market is open detection"""
        ready_state = SystemState(state=SystemStateEnum.READY)
        assert ready_state.is_market_open() is True

        trading_state = SystemState(state=SystemStateEnum.TRADING)
        assert trading_state.is_market_open() is True

        closed_state = SystemState(state=SystemStateEnum.CLOSED)
        assert closed_state.is_market_open() is False

    def test_valid_state_transitions(self):
        """Test valid state transitions (UB-001)"""
        state = SystemState(state=SystemStateEnum.OFFLINE)

        # OFFLINE → INITIALIZING: Valid
        assert state.can_transition_to(SystemStateEnum.INITIALIZING) is True

        # INITIALIZING → READY: Valid
        state.state = SystemStateEnum.INITIALIZING
        assert state.can_transition_to(SystemStateEnum.READY) is True

        # READY → TRADING: Valid
        state.state = SystemStateEnum.READY
        assert state.can_transition_to(SystemStateEnum.TRADING) is True

    def test_invalid_state_transitions(self):
        """Test invalid state transitions (UB-001)"""
        state = SystemState(state=SystemStateEnum.OFFLINE)

        # OFFLINE → TRADING: Invalid (must go through INITIALIZING, READY)
        assert state.can_transition_to(SystemStateEnum.TRADING) is False

        # OFFLINE → CLOSED: Invalid
        assert state.can_transition_to(SystemStateEnum.CLOSED) is False

    def test_stopped_state_from_any_state(self):
        """Test STOPPED can be reached from any state (emergency)"""
        for state_enum in SystemStateEnum:
            if state_enum == SystemStateEnum.STOPPED:
                continue
            state = SystemState(state=state_enum)
            # Any state can transition to STOPPED
            assert state.can_transition_to(SystemStateEnum.STOPPED) is True


class TestMarketLifecycleService:
    """MarketLifecycleService tests"""

    def test_initialization(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test service initialization"""
        assert market_lifecycle_service.get_system_state().state == SystemStateEnum.OFFLINE

    def test_get_system_state(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test getting current system state"""
        state = market_lifecycle_service.get_system_state()
        assert isinstance(state, SystemState)
        assert state.state == SystemStateEnum.OFFLINE

    def test_is_trading_allowed_when_ready(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test trading allowed when in READY state"""
        # Set state to READY
        market_lifecycle_service._system_state.state = SystemStateEnum.READY

        assert market_lifecycle_service.is_trading_allowed() is True

    def test_is_trading_allowed_when_stopped(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test trading blocked when in STOPPED state (UB-004)"""
        # Set state to STOPPED
        market_lifecycle_service._system_state.state = SystemStateEnum.STOPPED

        assert market_lifecycle_service.is_trading_allowed() is False

    def test_open_market_success(
        self,
        market_lifecycle_service: MarketLifecycleServiceImpl,
        mock_broker,
    ):
        """Test successful market open (ED-001, WT-001)"""
        # Mock successful operations
        mock_broker.connect_websocket.return_value = None

        # Open market
        result = market_lifecycle_service.open_market()

        # Verify success
        assert result is True

        # Verify state transitions
        assert market_lifecycle_service._system_state.state == SystemStateEnum.READY
        assert market_lifecycle_service._system_state.market_open_at is not None

    def test_open_market_auth_failure(
        self,
        market_lifecycle_service: MarketLifecycleServiceImpl,
        mock_broker,
    ):
        """Test market open failure on authentication"""
        # Mock authentication failure
        mock_broker.authenticate.side_effect = Exception("Authentication failed")

        # Attempt to open market
        with pytest.raises(MarketOpenError):
            market_lifecycle_service.open_market()

        # Verify STOPPED state (WT-003)
        assert market_lifecycle_service._system_state.state == SystemStateEnum.STOPPED

    def test_close_market_success(
        self,
        market_lifecycle_service: MarketLifecycleServiceImpl,
    ):
        """Test successful market close (ED-002, WT-004)"""
        # Set state to TRADING first
        market_lifecycle_service._system_state.state = SystemStateEnum.TRADING

        # Close market
        result = market_lifecycle_service.close_market()

        # Verify success
        assert result is True

        # Verify state transitions
        assert market_lifecycle_service._system_state.state == SystemStateEnum.CLOSED
        assert market_lifecycle_service._system_state.market_closed_at is not None

    def test_invalid_state_transition(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test invalid state transition raises error"""
        # Current state: OFFLINE
        # Try to transition to TRADING (invalid)

        with pytest.raises(InvalidStateTransitionError):
            market_lifecycle_service._transition_state(SystemStateEnum.TRADING)

    def test_state_change_callback(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test state change callback is invoked"""
        callback_mock = Mock()

        # Register callback
        market_lifecycle_service.register_state_change_callback(callback_mock)

        # Perform state transition
        market_lifecycle_service._transition_state(SystemStateEnum.INITIALIZING)

        # Verify callback was invoked
        callback_mock.assert_called_once_with(
            SystemStateEnum.OFFLINE, SystemStateEnum.INITIALIZING
        )

    def test_transition_to_stopped_on_error(
        self,
        market_lifecycle_service: MarketLifecycleServiceImpl,
        mock_broker,
    ):
        """Test transition to STOPPED on critical error (WT-003, UB-004)"""
        # Mock authentication failure
        mock_broker.authenticate.side_effect = Exception("Critical error")

        # Try to open market (should fail and transition to STOPPED)
        with pytest.raises(MarketOpenError):
            market_lifecycle_service.open_market()

        # Verify STOPPED state
        assert market_lifecycle_service._system_state.state == SystemStateEnum.STOPPED
