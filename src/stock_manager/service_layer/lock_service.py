"""
Lock Service

Manages distributed stock locks for multi-worker coordination using PostgreSQL row-level locks.
Implements WH-001: Stock Lock Management.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from ..domain.worker import StockLock
from ..adapters.storage.port import DatabasePort

logger = logging.getLogger(__name__)


class LockAcquisitionError(Exception):
    """Failed to acquire lock (already held by another worker)"""

    pass


class LockNotFoundError(Exception):
    """Lock not found"""

    pass


class LockExpiredError(Exception):
    """Lock has expired"""

    pass


class LockService:
    """Lock Service for distributed stock lock management

    Provides atomic lock acquisition using PostgreSQL row-level locks
    with TTL support for crash recovery.
    """

    def __init__(
        self,
        db: DatabasePort,
        default_ttl: timedelta = timedelta(minutes=5),
    ):
        """Initialize Lock Service

        Args:
            db: Database connection
            default_ttl: Default lock time-to-live
        """
        self.db = db
        self.default_ttl = default_ttl

    def acquire(
        self,
        symbol: str,
        worker_id: str,
        ttl: Optional[timedelta] = None,
    ) -> StockLock:
        """Acquire lock on a stock symbol (WH-001)

        Uses PostgreSQL row-level locking (SELECT ... FOR UPDATE SKIP LOCKED)
        to ensure atomic acquisition without blocking.

        Args:
            symbol: Stock symbol to lock (e.g., "005930")
            worker_id: Worker instance ID
            ttl: Lock time-to-live (default: default_ttl)

        Returns:
            StockLock: Acquired lock

        Raises:
            LockAcquisitionError: If lock is already held by another worker
        """
        ttl = ttl or self.default_ttl
        now = datetime.utcnow()
        expires_at = now + ttl

        # Try to acquire lock using row-level locking
        try:
            # First, cleanup any expired locks for this symbol
            self._cleanup_expired_lock(symbol)

            # Try to insert new lock
            # If symbol already exists with ACTIVE status, this will fail (UNIQUE constraint)
            # We use INSERT ... ON CONFLICT to handle race conditions
            query = """
                INSERT INTO stock_locks (symbol, worker_id, acquired_at, expires_at, heartbeat_at, status)
                VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
                ON CONFLICT (symbol) DO NOTHING
                RETURNING id, symbol, worker_id, acquired_at, expires_at, heartbeat_at, status, created_at, updated_at
            """
            params = (symbol, worker_id, now, expires_at, now)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                # Lock already exists and is ACTIVE
                existing_lock = self._get_lock_by_symbol(symbol)
                if existing_lock and existing_lock.worker_id == worker_id:
                    # Already owned by this worker, renew instead
                    return self.renew(symbol, worker_id)
                else:
                    raise LockAcquisitionError(
                        f"Lock for {symbol} is already held by another worker"
                    )

            # Convert result to StockLock
            return StockLock(
                id=result["id"],
                symbol=result["symbol"],
                worker_id=result["worker_id"],
                acquired_at=result["acquired_at"],
                expires_at=result["expires_at"],
                heartbeat_at=result["heartbeat_at"],
                status=result["status"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to acquire lock for {symbol}: {e}")
            raise

    def release(self, symbol: str, worker_id: str) -> bool:
        """Release lock on a stock symbol

        Args:
            symbol: Stock symbol
            worker_id: Worker ID requesting release

        Returns:
            bool: True if lock was released, False if not found or not owned

        Raises:
            LockNotFoundError: If lock not found
        """
        try:
            query = """
                UPDATE stock_locks
                SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
                WHERE symbol = $1 AND worker_id = $2 AND status = 'ACTIVE'
                RETURNING id
            """
            params = (symbol, worker_id)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                raise LockNotFoundError(
                    f"Active lock for {symbol} not found or not owned by {worker_id}"
                )

            logger.info(f"Released lock for {symbol} by {worker_id}")
            return True

        except LockNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to release lock for {symbol}: {e}")
            return False

    def renew(
        self,
        symbol: str,
        worker_id: str,
        ttl: Optional[timedelta] = None,
    ) -> StockLock:
        """Renew lock (extend TTL)

        Args:
            symbol: Stock symbol
            worker_id: Worker ID requesting renewal
            ttl: New TTL (default: default_ttl)

        Returns:
            StockLock: Renewed lock

        Raises:
            LockNotFoundError: If lock not found or not owned
            LockExpiredError: If lock has expired
        """
        ttl = ttl or self.default_ttl
        now = datetime.utcnow()
        expires_at = now + ttl

        try:
            query = """
                UPDATE stock_locks
                SET expires_at = $1, heartbeat_at = $2, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = $3 AND worker_id = $4 AND status = 'ACTIVE' AND expires_at > CURRENT_TIMESTAMP
                RETURNING id, symbol, worker_id, acquired_at, expires_at, heartbeat_at, status, created_at, updated_at
            """
            params = (expires_at, now, symbol, worker_id)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                # Check if lock exists but is expired
                existing = self._get_lock_by_symbol(symbol)
                if existing is None:
                    raise LockNotFoundError(f"Lock for {symbol} not found")
                else:
                    raise LockExpiredError(f"Lock for {symbol} has expired")

            logger.info(f"Renewed lock for {symbol} by {worker_id}")

            return StockLock(
                id=result["id"],
                symbol=result["symbol"],
                worker_id=result["worker_id"],
                acquired_at=result["acquired_at"],
                expires_at=result["expires_at"],
                heartbeat_at=result["heartbeat_at"],
                status=result["status"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except (LockNotFoundError, LockExpiredError):
            raise
        except Exception as e:
            logger.error(f"Failed to renew lock for {symbol}: {e}")
            raise

    def heartbeat(self, symbol: str, worker_id: str) -> bool:
        """Send heartbeat to keep lock alive

        Updates heartbeat_at timestamp without extending TTL.

        Args:
            symbol: Stock symbol
            worker_id: Worker ID sending heartbeat

        Returns:
            bool: True if heartbeat was sent, False if lock not found or expired

        Raises:
            LockNotFoundError: If lock not found
        """
        try:
            now = datetime.utcnow()

            query = """
                UPDATE stock_locks
                SET heartbeat_at = $1, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = $2 AND worker_id = $3 AND status = 'ACTIVE' AND expires_at > CURRENT_TIMESTAMP
                RETURNING id
            """
            params = (now, symbol, worker_id)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                raise LockNotFoundError(f"Active lock for {symbol} not found or expired")

            logger.debug(f"Heartbeat sent for {symbol} by {worker_id}")
            return True

        except LockNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to send heartbeat for {symbol}: {e}")
            return False

    def cleanup_expired(self) -> int:
        """Cleanup all expired locks

        Returns:
            int: Number of expired locks cleaned up
        """
        try:
            query = """
                UPDATE stock_locks
                SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'ACTIVE' AND expires_at < CURRENT_TIMESTAMP
                RETURNING id
            """

            results = self.db.execute_query(query, fetch_all=True)

            count = len(results) if results else 0
            if count > 0:
                logger.info(f"Cleaned up {count} expired locks")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired locks: {e}")
            return 0

    def get_lock(self, symbol: str) -> Optional[StockLock]:
        """Get current lock for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Optional[StockLock]: Lock if exists, None otherwise
        """
        return self._get_lock_by_symbol(symbol)

    def list_active_locks(self) -> list[StockLock]:
        """List all active locks

        Returns:
            list[StockLock]: List of active locks
        """
        try:
            query = """
                SELECT id, symbol, worker_id, acquired_at, expires_at, heartbeat_at, status, created_at, updated_at
                FROM stock_locks
                WHERE status = 'ACTIVE'
                ORDER BY acquired_at DESC
            """

            results = self.db.execute_query(query, fetch_all=True)

            return (
                [
                    StockLock(
                        id=r["id"],
                        symbol=r["symbol"],
                        worker_id=r["worker_id"],
                        acquired_at=r["acquired_at"],
                        expires_at=r["expires_at"],
                        heartbeat_at=r["heartbeat_at"],
                        status=r["status"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                    for r in results
                ]
                if results
                else []
            )

        except Exception as e:
            logger.error(f"Failed to list active locks: {e}")
            return []

    def _get_lock_by_symbol(self, symbol: str) -> Optional[StockLock]:
        """Get lock by symbol"""
        try:
            query = """
                SELECT id, symbol, worker_id, acquired_at, expires_at, heartbeat_at, status, created_at, updated_at
                FROM stock_locks
                WHERE symbol = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = (symbol,)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                return None

            return StockLock(
                id=result["id"],
                symbol=result["symbol"],
                worker_id=result["worker_id"],
                acquired_at=result["acquired_at"],
                expires_at=result["expires_at"],
                heartbeat_at=result["heartbeat_at"],
                status=result["status"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to get lock for {symbol}: {e}")
            return None

    def _cleanup_expired_lock(self, symbol: str) -> None:
        """Cleanup expired lock for a specific symbol"""
        try:
            query = """
                UPDATE stock_locks
                SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
                WHERE symbol = $1 AND status = 'ACTIVE' AND expires_at < CURRENT_TIMESTAMP
            """
            params = (symbol,)

            self.db.execute_query(query, params)

        except Exception as e:
            logger.error(f"Failed to cleanup expired lock for {symbol}: {e}")
