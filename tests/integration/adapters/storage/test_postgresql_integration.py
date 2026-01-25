"""
Integration tests for PostgreSQL Adapter

These tests require:
1. PostgreSQL database running (use docker-compose up)
2. Database schema applied (use docker-compose up -d to run migrations)

To run:
    docker-compose up -d postgres
    pytest tests/integration/adapters/storage/test_postgresql_integration.py -v
"""

import os
import pytest
from pathlib import Path

from stock_manager.adapters.storage.postgresql_adapter import (
    PostgreSQLAdapter,
    create_postgresql_adapter,
)


# Skip integration tests if PostgreSQL is not available
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_credentials():
    """Get database credentials from environment variables"""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "stock_manager"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


@pytest.fixture(scope="module")
def adapter(db_credentials):
    """Create and connect PostgreSQL adapter"""
    adapter = PostgreSQLAdapter(**db_credentials)

    # Try to connect, skip if database is not available
    try:
        adapter.connect()
        yield adapter
    except Exception as e:
        pytest.skip(f"PostgreSQL database not available: {e}")
    finally:
        adapter.close()


class TestPostgreSQLConnection:
    """Test PostgreSQL database connection"""

    def test_connection_successful(self, adapter):
        """Test that connection is established successfully"""
        assert adapter.is_connected
        assert adapter._connection_pool is not None

    def test_pool_status(self, adapter):
        """Test connection pool status"""
        status = adapter.pool_status
        assert "min_connections" in status
        assert "max_connections" in status
        assert "closed" in status
        assert status["closed"] is False

    def test_simple_query(self, adapter):
        """Test simple SELECT query"""
        result = adapter.execute_query("SELECT 1 as test", fetch_one=True)
        assert result is not None
        assert result["test"] == 1

    def test_connection_string_factory(self, db_credentials):
        """Test create_postgresql_adapter factory with connection string"""
        url = (
            f"postgresql://{db_credentials['user']}:{db_credentials['password']}"
            f"@{db_credentials['host']}:{db_credentials['port']}/{db_credentials['database']}"
        )
        adapter = create_postgresql_adapter(database_url=url)
        assert adapter.host == db_credentials["host"]
        assert adapter.port == db_credentials["port"]
        assert adapter.database == db_credentials["database"]
        assert adapter.user == db_credentials["user"]
        assert adapter.password == db_credentials["password"]


class TestPostgreSQLSchema:
    """Test PostgreSQL schema tables and structures"""

    @pytest.fixture
    def schema_tables(self):
        """Return expected schema tables"""
        return [
            "strategies",
            "strategy_params",
            "orders",
            "fills",
            "positions",
            "events",
            "strategy_param_drafts",
            "trade_journals",
            "ai_job_runs",
        ]

    def test_core_tables_exist(self, adapter, schema_tables):
        """Test that all core schema tables exist"""
        # Query information_schema for table names
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        result = adapter.execute_query(query, fetch_all=True)
        existing_tables = [row["table_name"] for row in result]

        # Check all expected tables exist
        for table in schema_tables:
            assert table in existing_tables, f"Table '{table}' not found in database"

    def test_orders_table_structure(self, adapter):
        """Test orders table structure"""
        query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'orders'
            ORDER BY ordinal_position
        """
        columns = adapter.execute_query(query, fetch_all=True)
        column_names = [col["column_name"] for col in columns]

        # Verify key columns exist
        expected_columns = [
            "id",
            "broker_order_id",
            "idempotency_key",
            "symbol",
            "side",
            "order_type",
            "qty",
            "price",
            "status",
            "requested_at",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in orders table"

    def test_fills_table_structure(self, adapter):
        """Test fills table structure"""
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fills'
            ORDER BY ordinal_position
        """
        columns = adapter.execute_query(query, fetch_all=True)
        column_names = [col["column_name"] for col in columns]

        # Verify key columns exist
        expected_columns = [
            "id",
            "order_id",
            "broker_fill_id",
            "symbol",
            "qty",
            "price",
            "filled_at",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in fills table"

    def test_positions_table_structure(self, adapter):
        """Test positions table structure"""
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'positions'
            ORDER BY ordinal_position
        """
        columns = adapter.execute_query(query, fetch_all=True)
        column_names = [col["column_name"] for col in columns]

        # Verify key columns exist
        expected_columns = ["id", "symbol", "qty", "avg_price", "created_at", "updated_at"]
        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in positions table"

    def test_enum_types_exist(self, adapter):
        """Test that required enum types exist"""
        query = """
            SELECT typname
            FROM pg_type
            WHERE typtype = 'e'
            AND typname IN ('order_side', 'order_type', 'order_status', 'event_level')
        """
        result = adapter.execute_query(query, fetch_all=True)
        enum_types = [row["typname"] for row in result]

        expected_enums = ["order_side", "order_type", "order_status", "event_level"]
        for enum in expected_enums:
            assert enum in enum_types, f"Enum type '{enum}' not found in database"


class TestPostgreSQLCRUDOperations:
    """Test CRUD operations with PostgreSQL adapter"""

    def test_insert_and_select_order(self, adapter):
        """Test inserting and selecting an order"""
        # Insert a test order
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = adapter.execute_query(
            insert_query,
            params=("TEST-001", "test-key-001", "005930", "BUY", "MARKET", 100, None, "NEW"),
            fetch_one=True,
        )

        assert result is not None
        order_id = result["id"]

        # Select the order
        select_query = "SELECT * FROM orders WHERE id = %s"
        order = adapter.execute_query(select_query, params=(order_id,), fetch_one=True)

        assert order is not None
        assert order["symbol"] == "005930"
        assert order["side"] == "BUY"
        assert order["order_type"] == "MARKET"
        assert order["qty"] == 100
        assert order["status"] == "NEW"

        # Clean up
        adapter.execute_query("DELETE FROM orders WHERE id = %s", params=(order_id,))

    def test_insert_fill(self, adapter):
        """Test inserting a fill"""
        # First create an order
        insert_order_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        order_result = adapter.execute_query(
            insert_order_query,
            params=("TEST-002", "test-key-002", "005930", "BUY", "MARKET", 100, None, "FILLED"),
            fetch_one=True,
        )
        order_id = order_result["id"]

        # Insert a fill
        insert_fill_query = """
            INSERT INTO fills (order_id, broker_fill_id, symbol, qty, price, filled_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """
        fill_result = adapter.execute_query(
            insert_fill_query,
            params=(order_id, "FILL-001", "005930", 100, 75000),
            fetch_one=True,
        )

        assert fill_result is not None
        fill_id = fill_result["id"]

        # Select the fill
        select_fill_query = "SELECT * FROM fills WHERE id = %s"
        fill = adapter.execute_query(select_fill_query, params=(fill_id,), fetch_one=True)

        assert fill is not None
        assert fill["order_id"] == order_id
        assert fill["symbol"] == "005930"
        assert fill["qty"] == 100
        assert fill["price"] == 75000

        # Clean up
        adapter.execute_query("DELETE FROM fills WHERE id = %s", params=(fill_id,))
        adapter.execute_query("DELETE FROM orders WHERE id = %s", params=(order_id,))

    def test_update_order_status(self, adapter):
        """Test updating order status"""
        # Insert order
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = adapter.execute_query(
            insert_query,
            params=("TEST-003", "test-key-003", "005930", "BUY", "MARKET", 100, None, "NEW"),
            fetch_one=True,
        )
        order_id = result["id"]

        # Update status
        update_query = "UPDATE orders SET status = %s WHERE id = %s"
        adapter.execute_query(update_query, params=("SENT", order_id))

        # Verify update
        select_query = "SELECT status FROM orders WHERE id = %s"
        order = adapter.execute_query(select_query, params=(order_id,), fetch_one=True)

        assert order["status"] == "SENT"

        # Clean up
        adapter.execute_query("DELETE FROM orders WHERE id = %s", params=(order_id,))

    def test_transaction_rollback(self, adapter):
        """Test transaction rollback on error"""
        with adapter.transaction():
            # Insert order
            insert_query = """
                INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            result = adapter.execute_query(
                insert_query,
                params=("TEST-004", "test-key-004", "005930", "BUY", "MARKET", 100, None, "NEW"),
                fetch_one=True,
            )
            order_id = result["id"]

            # Intentionally cause error to test rollback
            adapter.execute_query("INSERT INTO nonexistent_table VALUES (1)")

        # Transaction should have been rolled back
        select_query = "SELECT * FROM orders WHERE id = %s"
        order = adapter.execute_query(select_query, params=(order_id,), fetch_one=True)

        assert order is None, "Order should have been rolled back"

    def test_fetch_all_orders(self, adapter):
        """Test fetching multiple orders"""
        # Insert multiple orders
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        order_ids = []
        for i in range(3):
            result = adapter.execute_query(
                insert_query,
                params=(
                    f"TEST-00{i}",
                    f"test-key-00{i}",
                    f"00593{i}",
                    "BUY",
                    "MARKET",
                    100,
                    None,
                    "NEW",
                ),
                fetch_one=True,
            )
            order_ids.append(result["id"])

        # Fetch all orders
        select_query = "SELECT * FROM orders WHERE id IN %s ORDER BY id"
        orders = adapter.execute_query(select_query, params=(tuple(order_ids),), fetch_all=True)

        assert len(orders) == 3
        assert all(order["side"] == "BUY" for order in orders)

        # Clean up
        for order_id in order_ids:
            adapter.execute_query("DELETE FROM orders WHERE id = %s", params=(order_id,))


class TestPostgreSQLConstraints:
    """Test PostgreSQL constraints and indexes"""

    def test_orders_unique_constraint(self, adapter):
        """Test unique constraint on idempotency_key"""
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Insert first order
        adapter.execute_query(
            insert_query,
            params=("TEST-005", "duplicate-key", "005930", "BUY", "MARKET", 100, None, "NEW"),
        )

        # Try to insert with duplicate idempotency_key - should fail
        with pytest.raises(Exception):  # psycopg2.IntegrityError
            adapter.execute_query(
                insert_query,
                params=("TEST-006", "duplicate-key", "005930", "BUY", "MARKET", 200, None, "NEW"),
            )

        # Clean up
        adapter.execute_query(
            "DELETE FROM orders WHERE idempotency_key = %s", params=("duplicate-key",)
        )

    def test_positions_unique_constraint(self, adapter):
        """Test unique constraint on symbol in positions"""
        insert_query = """
            INSERT INTO positions (symbol, qty, avg_price)
            VALUES (%s, %s, %s)
        """
        # Insert first position
        adapter.execute_query(insert_query, params=("005930", 100, 75000))

        # Try to insert duplicate symbol - should fail
        with pytest.raises(Exception):  # psycopg2.IntegrityError
            adapter.execute_query(insert_query, params=("005930", 200, 76000))

        # Clean up
        adapter.execute_query("DELETE FROM positions WHERE symbol = %s", params=("005930",))

    def test_orders_qty_check_constraint(self, adapter):
        """Test check constraint on qty (must be > 0)"""
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Try to insert order with qty = 0 - should fail
        with pytest.raises(Exception):  # psycopg2.IntegrityError
            adapter.execute_query(
                insert_query,
                params=("TEST-007", "test-key-007", "005930", "BUY", "MARKET", 0, None, "NEW"),
            )

    def test_limit_order_price_check(self, adapter):
        """Test check constraint: LIMIT orders must have price"""
        insert_query = """
            INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Try to insert LIMIT order without price - should fail
        with pytest.raises(Exception):  # psycopg2.IntegrityError
            adapter.execute_query(
                insert_query,
                params=("TEST-008", "test-key-008", "005930", "BUY", "LIMIT", 100, None, "NEW"),
            )
