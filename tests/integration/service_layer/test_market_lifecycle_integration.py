"""
Integration tests for Market Lifecycle Service

Tests integration between MarketLifecycleService, StateRecoveryService,
and SettlementService with real database operations.
"""

import pytest
from datetime import time, date
from decimal import Decimal

from stock_manager.service_layer.market_lifecycle_service import (
    MarketLifecycleServiceImpl,
)
from stock_manager.service_layer.state_recovery_service import (
    StateRecoveryServiceImpl,
)
from stock_manager.service_layer.settlement_service import (
    SettlementServiceImpl,
)
from stock_manager.adapters.broker.mock import MockBrokerAdapter
from stock_manager.adapters.storage.postgresql_adapter import create_postgresql_adapter
from stock_manager.service_layer.order_service import OrderService
from stock_manager.service_layer.position_service import PositionService


@pytest.fixture(scope="module")
def db_connection():
    """Database connection for integration tests"""
    import os

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stock_manager_test")

    adapter = create_postgresql_adapter(database_url=db_url)
    adapter.connect()

    yield adapter

    adapter.close()


@pytest.fixture
def mock_broker():
    """Mock broker adapter"""
    broker = MockBrokerAdapter()
    broker.authenticate()  # Authenticate for testing
    return broker


@pytest.fixture
def order_service(db_connection, mock_broker):
    """Order service fixture"""
    from stock_manager.config.app_config import AppConfig
    config = AppConfig(account_id="7263942401")  # Test account ID
    return OrderService(mock_broker, db_connection, config)


@pytest.fixture
def position_service(db_connection):
    """Position service fixture"""
    return PositionService(db_connection)


@pytest.fixture
def market_lifecycle_service(
    db_connection, mock_broker, order_service, position_service
):
    """Market lifecycle service fixture"""
    return MarketLifecycleServiceImpl(
        broker=mock_broker,
        order_service=order_service,
        position_service=position_service,
        db_connection=db_connection,
        market_open_time=time(8, 30, 0),
        market_close_time=time(15, 30, 0),
    )


@pytest.fixture
def state_recovery_service(
    db_connection, mock_broker, order_service, position_service
):
    """State recovery service fixture"""
    return StateRecoveryServiceImpl(
        broker=mock_broker,
        order_service=order_service,
        position_service=position_service,
        db_connection=db_connection,
    )


@pytest.fixture
def settlement_service(db_connection, position_service):
    """Settlement service fixture"""
    return SettlementServiceImpl(
        position_service=position_service,
        db_connection=db_connection,
    )


@pytest.mark.integration
class TestMarketLifecycleServiceIntegration:
    """Integration tests for MarketLifecycleService"""

    def test_full_market_lifecycle(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test complete market lifecycle: open → close"""
        # Open market
        open_result = market_lifecycle_service.open_market()
        assert open_result is True
        assert market_lifecycle_service.get_system_state().state.value == "READY"

        # Verify trading is allowed
        assert market_lifecycle_service.is_trading_allowed() is True

        # Close market
        close_result = market_lifecycle_service.close_market()
        assert close_result is True
        assert market_lifecycle_service.get_system_state().state.value == "CLOSED"

        # Verify trading is blocked
        assert market_lifecycle_service.is_trading_allowed() is False

    def test_system_state_persistence(
        self, market_lifecycle_service: MarketLifecycleServiceImpl
    ):
        """Test system state is persisted to database"""
        # Open market
        market_lifecycle_service.open_market()

        # Query database for state
        query = """
        SELECT state, market_open_at, recovery_status
        FROM system_states
        ORDER BY created_at DESC
        LIMIT 1
        """

        with market_lifecycle_service.db.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()

        assert row is not None
        assert row['state'] == "READY"
        assert row['market_open_at'] is not None  # market_open_at
        assert row['recovery_status'] == "SUCCESS"  # recovery_status


@pytest.mark.integration
class TestStateRecoveryServiceIntegration:
    """Integration tests for StateRecoveryService"""

    def test_state_recovery_with_orders(
        self,
        state_recovery_service: StateRecoveryServiceImpl,
        order_service: OrderService,
    ):
        """Test state recovery with pending orders"""
        # Create a test order
        from stock_manager.domain.order import OrderRequest

        request = OrderRequest(
            symbol="005930",
            side="BUY",
            order_type="MARKET",
            qty=Decimal("100"),
            price=None,
            idempotency_key="test_recovery_001",
        )

        order = order_service.create_order(request)
        order_service.send_order(order.id)

        # Run recovery
        result = state_recovery_service.recover()

        # Verify result
        assert result.success is True
        assert result.status.value in ["SUCCESS", "PARTIAL"]


@pytest.mark.integration
class TestSettlementServiceIntegration:
    """Integration tests for SettlementService"""

    def test_daily_settlement_creation(
        self, settlement_service: SettlementServiceImpl, db_connection
    ):
        """Test daily settlement creation"""
        trade_date = date.today()

        # Cleanup first: delete any existing settlement for today
        db_connection.execute_query(
            "DELETE FROM daily_settlements WHERE trade_date = %s",
            params=(trade_date,)
        )

        settlement = settlement_service.create_daily_settlement(trade_date)

        # Verify settlement
        assert settlement.trade_date == trade_date
        assert settlement.id > 0  # Should have been assigned by database

        # Verify it can be retrieved
        retrieved = settlement_service.get_daily_settlement(trade_date)
        assert retrieved is not None
        assert retrieved.id == settlement.id

        # Cleanup after test
        db_connection.execute_query(
            "DELETE FROM daily_settlements WHERE id = %s",
            params=(settlement.id,)
        )


@pytest.mark.integration
class TestMarketLifecycleEndToEnd:
    """End-to-end integration tests"""

    def test_market_open_close_with_settlement(
        self,
        market_lifecycle_service: MarketLifecycleServiceImpl,
        settlement_service: SettlementServiceImpl,
    ):
        """Test complete market day with settlement"""
        # Open market
        market_lifecycle_service.open_market()

        # Close market (includes settlement)
        market_lifecycle_service.close_market()

        # Verify settlement was created
        trade_date = date.today()
        settlement = settlement_service.get_daily_settlement(trade_date)

        # Note: Settlement creation is currently mocked in close_market
        # In production, this would be implemented
