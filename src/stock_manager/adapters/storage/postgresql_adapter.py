"""
PostgreSQL Adapter

Implements DatabasePort for PostgreSQL database operations.
Uses psycopg2 for database connectivity with connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2 import pool, sql
    from psycopg2.extras import RealDictCursor
except ImportError:
    raise ImportError("psycopg2-binary is required. Install with: pip install psycopg2-binary")

from .port import DatabasePort

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabasePort):
    """PostgreSQL database adapter

    Implements DatabasePort for PostgreSQL operations with connection pooling.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "stock_manager",
        user: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        """Initialize PostgreSQL adapter

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connection pool size
            max_connections: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections

        self._connection_pool: Optional[pool.ThreadedConnectionPool] = None

    def connect(self) -> None:
        """Initialize connection pool"""
        if self._connection_pool is not None:
            logger.warning("Connection pool already initialized")
            return

        try:
            self._connection_pool = pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            logger.info(
                f"PostgreSQL connection pool initialized: {self.host}:{self.port}/{self.database}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Optional[Any]:
        """Execute a SQL query

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return single row (dict)
            fetch_all: Return all rows (list of dict)

        Returns:
            Query result (dict, list of dict, or None)

        Raises:
            RuntimeError: If connection pool is not initialized
            Exception: If query execution fails
        """
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")

        try:
            with self._connection_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)

                    if fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return None

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            raise

    def execute_transaction(
        self,
        queries: list[tuple[str, Optional[tuple]]],
    ) -> bool:
        """Execute multiple queries in a transaction

        Args:
            queries: List of (query, params) tuples

        Returns:
            bool: True if transaction succeeded

        Raises:
            RuntimeError: If connection pool is not initialized
            Exception: If transaction execution fails
        """
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")

        try:
            with self._connection_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for query, params in queries:
                        cursor.execute(query, params)
                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Transaction execution failed: {e}")
            logger.debug(f"Queries: {queries}")
            # Rollback is automatic on exception
            return False

    def close(self) -> None:
        """Close connection pool"""
        if self._connection_pool is None:
            return

        try:
            self._connection_pool.closeall()
            self._connection_pool = None
            logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            logger.error(f"Failed to close connection pool: {e}")

    @contextmanager
    def transaction(self):
        """Context manager for transaction handling

        Usage:
            with db.transaction():
                db.execute_query("INSERT ...")
                db.execute_query("UPDATE ...")
        """
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")

        conn = None
        try:
            conn = self._connection_pool.getconn()
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    @property
    def is_connected(self) -> bool:
        """Check if connection pool is initialized

        Returns:
            bool: True if connected
        """
        return self._connection_pool is not None

    @property
    def pool_status(self) -> Dict[str, int]:
        """Get connection pool status

        Returns:
            dict: Pool statistics
        """
        if self._connection_pool is None:
            return {"min_connections": 0, "max_connections": 0, "closed": True}

        return {
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "closed": self._connection_pool.closed,
        }


def create_postgresql_adapter(
    database_url: Optional[str] = None,
    **kwargs,
) -> PostgreSQLAdapter:
    """Factory function to create PostgreSQL adapter

    Args:
        database_url: PostgreSQL connection URL (e.g., "postgresql://user:pass@host:port/db")
        **kwargs: Additional parameters for PostgreSQLAdapter

    Returns:
        PostgreSQLAdapter: Initialized adapter

    Example:
        adapter = create_postgresql_adapter(
            database_url="postgresql://postgres:password@localhost:5432/stock_manager"
        )
        adapter.connect()
    """
    if database_url:
        import urllib.parse

        parsed = urllib.parse.urlparse(database_url)

        kwargs.setdefault("host", parsed.hostname or "localhost")
        kwargs.setdefault("port", parsed.port or 5432)
        kwargs.setdefault("database", parsed.path.lstrip("/") or "stock_manager")
        kwargs.setdefault("user", parsed.username or "postgres")
        kwargs.setdefault("password", parsed.password or "")

    adapter = PostgreSQLAdapter(**kwargs)
    return adapter
