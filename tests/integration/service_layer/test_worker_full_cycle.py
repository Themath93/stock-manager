"""
Full Cycle Integration Test for PoC

Tests complete trading workflow:
SCANNING → Buy Signal → Order → HOLDING → Sell Signal → Order → SCANNING

TOMBSTONE: PoC test using DummyStrategy and MockBrokerAdapter
TODO: Replace with real strategy and KIS broker before production
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from stock_manager.service_layer.worker_main import WorkerMain
from stock_manager.service_layer.lock_service import LockService
from stock_manager.service_layer.worker_lifecycle_service import WorkerLifecycleService
from stock_manager.service_layer.strategy_executor import StrategyExecutor
from stock_manager.service_layer.dummy_strategy import DummyStrategy
from stock_manager.service_layer.order_service import OrderService
from stock_manager.adapters.broker.mock import MockBrokerAdapter
from stock_manager.adapters.storage.postgresql_adapter import create_postgresql_adapter
from stock_manager.config.app_config import AppConfig
from stock_manager.domain.worker import Candidate, WorkerStatus
from stock_manager.domain.order import OrderRequest, OrderStatus


@pytest.fixture(scope="module")
def db_connection():
    """Database connection for integration tests"""
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stock_manager")
    adapter = create_postgresql_adapter(database_url=db_url)
    adapter.connect()
    yield adapter
    adapter.close()


@pytest.fixture(scope="module")
def mock_broker():
    """Mock broker adapter"""
    broker = MockBrokerAdapter()
    broker.authenticate()
    return broker


@pytest.fixture(scope="module")
def app_config():
    """App config"""
    return AppConfig(account_id="7263942401")


@pytest.fixture(scope="module")
def order_service(db_connection, mock_broker, app_config):
    """Order service"""
    return OrderService(mock_broker, db_connection, app_config)


@pytest.fixture(scope="module")
def position_service(db_connection):
    """Position service"""
    from stock_manager.service_layer.position_service import PositionService
    return PositionService(db_connection)


@pytest.fixture(scope="module")
def market_data_poller_mock():
    """Mock market data poller"""
    poller = Mock()

    # Mock discover_candidates to return test candidates
    async def mock_discover(max_candidates: int):
        return [
            Candidate(
                symbol="005930",
                name="Samsung Electronics",
                current_price=Decimal("50000"),
                volume=1000000,
                change_percent=Decimal("2.5"),
                discovered_at=datetime.now(),
                metadata={"rsi": Decimal("65")},
            ),
            Candidate(
                symbol="006400",  # Different symbol for testing
                name="SK Hynix",
                current_price=Decimal("100000"),
                volume=500000,
                change_percent=Decimal("1.8"),
                discovered_at=datetime.now(),
                metadata={"rsi": Decimal("60")},
            ),
        ][:max_candidates]

    poller.discover_candidates = mock_discover
    return poller


@pytest.fixture(scope="module")
def daily_summary_service_mock():
    """Mock daily summary service"""
    service = Mock()
    service.generate_daily_summary = AsyncMock(return_value=None)
    return service


@pytest.mark.integration
class TestWorkerFullCycle:
    """Full cycle integration test for PoC"""

    @pytest.mark.asyncio
    async def test_full_trading_cycle(
        self,
        db_connection,
        mock_broker,
        app_config,
        order_service,
        market_data_poller_mock,
        daily_summary_service_mock,
    ):
        """Test complete trading cycle: SCANNING → BUY → HOLDING → SELL → SCANNING

        PoC Workflow:
        1. Start worker (IDLE)
        2. Discover candidates (SCANNING)
        3. Get buy signal from DummyStrategy
        4. Acquire lock
        5. Create buy order
        6. Hold position
        7. Get sell signal (simulate 5% profit)
        8. Create sell order
        9. Release lock
        10. Back to SCANNING
        """
        worker_id = "test-worker-poc-001"

        # === Cleanup any existing data ===
        db_connection.execute_query(
            "DELETE FROM worker_processes WHERE worker_id = %s",
            params=(worker_id,)
        )
        db_connection.execute_query(
            "DELETE FROM orders WHERE idempotency_key LIKE %s OR broker_order_id LIKE %s",
            params=(f"poc-{worker_id}-%", "MOCK_%")
        )
        db_connection.execute_query(
            "DELETE FROM stock_locks WHERE worker_id = %s",
            params=(worker_id,)
        )

        # === Setup Services ===
        lock_service = LockService(db_connection)

        # Use DummyStrategy for PoC
        strategy = DummyStrategy(
            buy_confidence=Decimal("0.8"),
            sell_confidence=Decimal("0.8"),
            suggested_qty=Decimal("10"),
        )
        strategy_executor = StrategyExecutor(
            strategy=strategy,
            min_confidence=Decimal("0.5"),
        )

        worker_lifecycle = WorkerLifecycleService(
            db=db_connection,
        )

        # Create WorkerMain
        worker = WorkerMain(
            worker_id=worker_id,
            lock_service=lock_service,
            worker_lifecycle=worker_lifecycle,
            market_data_poller=market_data_poller_mock,
            strategy_executor=strategy_executor,
            order_service=order_service,
            daily_summary_service=daily_summary_service_mock,
            heartbeat_interval=timedelta(seconds=1),  # Shorter for testing
            poll_interval=timedelta(seconds=1),
            lock_ttl=timedelta(minutes=5),
        )

        # === Step 1: Start Worker ===
        print("\n=== Step 1: Starting Worker ===")
        worker_lifecycle.start(worker_id=worker_id)
        assert worker_lifecycle.get_worker(worker_id).status == WorkerStatus.IDLE
        print("✅ Worker started in IDLE state")

        # === Step 2: Discover Candidates (SCANNING) ===
        print("\n=== Step 2: Discovering Candidates ===")
        candidates = await market_data_poller_mock.discover_candidates(max_candidates=2)
        assert len(candidates) > 0
        candidate = candidates[0]  # Use first candidate (005930)
        print(f"✅ Discovered {len(candidates)} candidates: {[c.symbol for c in candidates]}")
        print(f"   Selected: {candidate.symbol} @ {candidate.current_price}")

        # === Step 3: Get Buy Signal from DummyStrategy ===
        print("\n=== Step 3: Evaluating Buy Signal ===")
        buy_signal = await strategy_executor.should_buy(candidate, position_qty=Decimal("0"))
        assert buy_signal is not None
        assert buy_signal.symbol == "005930"
        assert buy_signal.suggested_qty == Decimal("10")
        print(f"✅ Buy signal received: {buy_signal.symbol}, qty={buy_signal.suggested_qty}, confidence={buy_signal.confidence}")

        # === Step 4: Acquire Lock ===
        print("\n=== Step 4: Acquiring Stock Lock ===")
        lock = lock_service.acquire(
            symbol=candidate.symbol,
            worker_id=worker_id,
            ttl=timedelta(minutes=5),
        )
        assert lock.symbol == "005930"
        assert lock.worker_id == worker_id
        print(f"✅ Lock acquired: {lock.symbol} by {lock.worker_id}")

        # === Step 5: Create Buy Order ===
        print("\n=== Step 5: Creating Buy Order ===")
        order_request = OrderRequest(
            symbol=candidate.symbol,
            side="BUY",
            order_type="MARKET",
            qty=Decimal("10"),
            price=candidate.current_price,
            idempotency_key=f"poc-{worker_id}-{candidate.symbol}-{datetime.now().timestamp()}",
        )

        order = order_service.create_order(order_request)
        order_service.send_order(order.id)
        # Re-fetch order to get updated status
        order = order_service.get_order(order.id)
        assert order.status == OrderStatus.SENT  # Mock broker accepts immediately
        print(f"✅ Buy order created: ID={order.id}, symbol={order.symbol}, qty={order.qty}")

        # === Step 6: Transition to SCANNING then HOLDING ===
        print("\n=== Step 6: Transitioning to SCANNING then HOLDING ===")
        worker_lifecycle.transition_status(worker_id, WorkerStatus.SCANNING)
        assert worker_lifecycle.get_worker(worker_id).status == WorkerStatus.SCANNING
        worker_lifecycle.transition_status(worker_id, WorkerStatus.HOLDING, current_symbol=candidate.symbol)
        assert worker_lifecycle.get_worker(worker_id).status == WorkerStatus.HOLDING
        print(f"✅ Worker now HOLDING: {candidate.symbol}")

        # === Step 7: Simulate Price Increase (5% Profit) ===
        print("\n=== Step 7: Simulating Price Increase ===")
        avg_price = candidate.current_price
        current_price = avg_price * Decimal("1.05")  # 5% increase
        print(f"   Avg Price: {avg_price} → Current Price: {current_price} (+5%)")

        # === Step 8: Get Sell Signal ===
        print("\n=== Step 8: Evaluating Sell Signal ===")
        sell_signal = await strategy_executor.should_sell(
            symbol=candidate.symbol,
            position_qty=Decimal("10"),
            avg_price=avg_price,
            current_price=current_price,
        )
        assert sell_signal is not None
        assert sell_signal.symbol == "005930"
        print(f"✅ Sell signal received: {sell_signal.reason}")

        # === Step 9: Create Sell Order ===
        print("\n=== Step 9: Creating Sell Order ===")
        sell_request = OrderRequest(
            symbol=candidate.symbol,
            side="SELL",
            order_type="MARKET",
            qty=Decimal("10"),
            price=current_price,
            idempotency_key=f"poc-{worker_id}-{candidate.symbol}-sell-{datetime.now().timestamp()}",
        )

        sell_order = order_service.create_order(sell_request)
        order_service.send_order(sell_order.id)
        # Re-fetch order to get updated status
        sell_order = order_service.get_order(sell_order.id)
        print(f"✅ Sell order created: ID={sell_order.id}, symbol={sell_order.symbol}, qty={sell_order.qty}")

        # === Step 10: Release Lock ===
        print("\n=== Step 10: Releasing Stock Lock ===")
        lock_service.release(symbol=candidate.symbol, worker_id=worker_id)
        print(f"✅ Lock released: {candidate.symbol}")

        # === Step 11: Return to SCANNING ===
        print("\n=== Step 11: Transitioning back to SCANNING ===")
        worker_lifecycle.transition_status(worker_id, WorkerStatus.SCANNING, current_symbol=None)
        assert worker_lifecycle.get_worker(worker_id).status == WorkerStatus.SCANNING
        print("✅ Worker back to SCANNING state")

        # === Summary ===
        print("\n" + "="*60)
        print("🎉 FULL CYCLE TEST PASSED!")
        print("="*60)
        print(f"Worker: {worker_id}")
        print(f"Symbol: {candidate.symbol}")
        print(f"Buy Price: {avg_price}")
        print(f"Sell Price: {current_price}")
        print("Profit: 5% (simulated)")
        print(f"Buy Order ID: {order.id}")
        print(f"Sell Order ID: {sell_order.id}")
        print("="*60)

        # === Cleanup ===
        # Clean up test data
        db_connection.execute_query(
            "DELETE FROM orders WHERE broker_order_id LIKE %s",
            params=(f"poc-{worker_id}-%",)
        )
        worker_lifecycle.stop(worker_id)


@pytest.mark.integration
class TestWorkerFullCycleAutomated:
    """Automated full cycle test (simpler version)"""

    @pytest.mark.asyncio
    async def test_automated_full_cycle(
        self,
        db_connection,
        mock_broker,
        app_config,
        order_service,
    ):
        """Test automated full cycle using simplified workflow"""
        worker_id = "test-worker-auto-001"

        # Setup
        lock_service = LockService(db_connection)
        strategy = DummyStrategy()
        executor = StrategyExecutor(strategy=strategy)
        lifecycle = WorkerLifecycleService(db=db_connection)

        # Test candidate
        candidate = Candidate(
            symbol="005930",
            name="Samsung",
            current_price=Decimal("50000"),
            volume=1000000,
            change_percent=Decimal("2.5"),
            discovered_at=datetime.now(),
            metadata={},
        )

        # Start
        lifecycle.start(worker_id)
        lifecycle.transition_status(worker_id, WorkerStatus.IDLE)

        # Full cycle
        lock = lock_service.acquire(candidate.symbol, worker_id, ttl=timedelta(minutes=5))

        buy_signal = await executor.should_buy(candidate)
        assert buy_signal is not None

        order = order_service.create_order(
            OrderRequest(
                account_id=app_config.account_id,
                symbol=candidate.symbol,
                side="BUY",
                order_type="MARKET",
                qty=Decimal("10"),
                price=candidate.current_price,
                idempotency_key=f"auto-{worker_id}-{datetime.now().timestamp()}",
            )
        )

        sell_signal = await executor.should_sell(
            candidate.symbol,
            Decimal("10"),
            Decimal("50000"),
            Decimal("52500"),  # 5% profit
        )
        assert sell_signal is not None

        lock_service.release(candidate.symbol, worker_id)

        # Cleanup
        lifecycle.stop(worker_id)
        db_connection.execute_query("DELETE FROM orders WHERE id = %s", params=(order.id,))

        print("\n✅ Automated full cycle test passed!")
