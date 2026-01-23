"""
Unit tests for PostgreSQL Adapter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Mock psycopg2.pool before importing adapter
with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool

    from stock_manager.adapters.storage.postgresql_adapter import (
        PostgreSQLAdapter,
        create_postgresql_adapter,
    )


class TestPostgreSQLAdapter:
    """Test cases for PostgreSQL adapter"""

    @pytest.fixture
    def adapter(self):
        """Create PostgreSQL adapter for testing"""
        return PostgreSQLAdapter(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            min_connections=1,
            max_connections=5,
        )

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization with parameters"""
        assert adapter.host == "localhost"
        assert adapter.port == 5432
        assert adapter.database == "test_db"
        assert adapter.user == "test_user"
        assert adapter.password == "test_pass"
        assert adapter.min_connections == 1
        assert adapter.max_connections == 5
        assert adapter._connection_pool is None

    def test_adapter_default_parameters(self):
        """Test adapter initialization with default parameters"""
        adapter = PostgreSQLAdapter()
        assert adapter.host == "localhost"
        assert adapter.port == 5432
        assert adapter.database == "stock_manager"
        assert adapter.user == "postgres"
        assert adapter.password == ""
        assert adapter.min_connections == 1
        assert adapter.max_connections == 10

    def test_connect_failure(self, adapter):
        """Test connection pool initialization failure"""
        with patch(
            "stock_manager.adapters.storage.postgresql_adapter.pool.ThreadedConnectionPool"
        ) as mock_pool_class:
            mock_pool_class.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                adapter.connect()

    def test_execute_query_not_connected(self, adapter):
        """Test query execution when not connected"""
        with pytest.raises(RuntimeError, match="Connection pool not initialized"):
            adapter.execute_query("SELECT 1")

    def test_execute_transaction_not_connected(self, adapter):
        """Test transaction execution when not connected"""
        with pytest.raises(RuntimeError, match="Connection pool not initialized"):
            adapter.execute_transaction([])

    def test_close_not_connected(self, adapter):
        """Test closing when not connected"""
        adapter.close()  # Should not raise error
        assert adapter._connection_pool is None

    def test_pool_status_not_connected(self, adapter):
        """Test pool_status property when not connected"""
        status = adapter.pool_status

        assert status["min_connections"] == 0
        assert status["max_connections"] == 0
        assert status["closed"] is True

    def test_transaction_context_manager_not_connected(self, adapter):
        """Test transaction context manager when not connected"""
        with pytest.raises(RuntimeError, match="Connection pool not initialized"):
            with adapter.transaction():
                pass


class TestCreatePostgreSQLAdapter:
    """Test cases for create_postgresql_adapter factory function"""

    def test_create_with_url(self):
        """Test creating adapter from URL"""
        adapter = create_postgresql_adapter(
            database_url="postgresql://user:pass@host:5432/database"
        )

        assert adapter.host == "host"
        assert adapter.port == 5432
        assert adapter.database == "database"
        assert adapter.user == "user"
        assert adapter.password == "pass"

    def test_create_with_url_missing_parts(self):
        """Test creating adapter from URL with missing parts"""
        adapter = create_postgresql_adapter(database_url="postgresql://host/database")

        assert adapter.host == "host"
        assert adapter.port == 5432  # default
        assert adapter.database == "database"
        assert adapter.user == "postgres"  # default
        assert adapter.password == ""  # default

    def test_create_with_kwargs(self):
        """Test creating adapter with kwargs"""
        adapter = create_postgresql_adapter(
            host="custom_host",
            port=9999,
            database="custom_db",
        )

        assert adapter.host == "custom_host"
        assert adapter.port == 9999
        assert adapter.database == "custom_db"

    def test_create_with_url_and_kwargs(self):
        """Test creating adapter with URL and kwargs"""
        adapter = create_postgresql_adapter(
            database_url="postgresql://user:pass@host/database",
            min_connections=2,
            max_connections=20,
        )

        assert adapter.host == "host"
        assert adapter.database == "database"
        assert adapter.min_connections == 2
        assert adapter.max_connections == 20
