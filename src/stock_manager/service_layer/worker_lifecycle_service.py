"""
Worker Lifecycle Service

Manages worker process lifecycle including startup, shutdown, status transitions,
and heartbeat management. Implements WH-002: Worker Process Tracking.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from ..domain.worker import WorkerStatus, WorkerProcess
from ..adapters.storage.port import DatabasePort

logger = logging.getLogger(__name__)


class WorkerNotFoundError(Exception):
    """Worker process not found"""

    pass


class WorkerAlreadyExistsError(Exception):
    """Worker process already exists"""

    pass


class InvalidStatusTransitionError(Exception):
    """Invalid worker status transition"""

    pass


class WorkerLifecycleService:
    """Worker Lifecycle Service

    Manages worker process registration, status tracking, and heartbeat
    monitoring for crash recovery.
    """

    def __init__(
        self,
        db: DatabasePort,
        default_heartbeat_interval: timedelta = timedelta(seconds=30),
        worker_ttl: timedelta = timedelta(minutes=5),
    ):
        """Initialize Worker Lifecycle Service

        Args:
            db: Database connection
            default_heartbeat_interval: Default heartbeat interval
            worker_ttl: Worker TTL for crash detection (3x heartbeat_interval)
        """
        self.db = db
        self.default_heartbeat_interval = default_heartbeat_interval
        self.worker_ttl = worker_ttl

    def start(
        self,
        worker_id: Optional[str] = None,
        heartbeat_interval: Optional[timedelta] = None,
    ) -> WorkerProcess:
        """Register and start a new worker process

        Args:
            worker_id: Worker instance ID (auto-generated if None)
            heartbeat_interval: Heartbeat interval (default: default_heartbeat_interval)

        Returns:
            WorkerProcess: Created worker process

        Raises:
            WorkerAlreadyExistsError: If worker_id already exists
        """
        worker_id = worker_id or str(uuid4())
        heartbeat_interval = heartbeat_interval or self.default_heartbeat_interval
        now = datetime.now(timezone.utc)

        # Check if worker already exists
        existing = self._get_worker_by_id(worker_id)
        if existing:
            raise WorkerAlreadyExistsError(f"Worker {worker_id} already exists")

        try:
            query = """
                INSERT INTO worker_processes (
                    worker_id, status, current_symbol, started_at, last_heartbeat_at, heartbeat_interval
                )
                VALUES (%s, 'IDLE', NULL, %s, %s, %s)
                RETURNING id, worker_id, status, current_symbol, started_at, last_heartbeat_at, heartbeat_interval, created_at, updated_at
            """
            params = (worker_id, now, now, heartbeat_interval)

            result = self.db.execute_query(query, params, fetch_one=True)

            logger.info(f"Started worker process: {worker_id}")

            return WorkerProcess(
                id=result["id"],
                worker_id=result["worker_id"],
                status=WorkerStatus(result["status"]),
                current_symbol=result["current_symbol"],
                started_at=result["started_at"],
                last_heartbeat_at=result["last_heartbeat_at"],
                heartbeat_interval=result["heartbeat_interval"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to start worker {worker_id}: {e}")
            raise

    def stop(self, worker_id: str) -> bool:
        """Stop a worker process (graceful shutdown)

        Args:
            worker_id: Worker instance ID

        Returns:
            bool: True if worker was stopped

        Raises:
            WorkerNotFoundError: If worker not found
        """
        # Transition to EXITING status
        self.transition_status(worker_id, WorkerStatus.EXITING)

        logger.info(f"Stopped worker process: {worker_id}")
        return True

    def heartbeat(self, worker_id: str) -> bool:
        """Send worker heartbeat

        Args:
            worker_id: Worker instance ID

        Returns:
            bool: True if heartbeat was recorded

        Raises:
            WorkerNotFoundError: If worker not found
        """
        try:
            now = datetime.now(timezone.utc)

            query = """
                UPDATE worker_processes
                SET last_heartbeat_at = %s, updated_at = CURRENT_TIMESTAMP
                WHERE worker_id = %s AND status != 'EXITING'
                RETURNING id
            """
            params = (now, worker_id)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                raise WorkerNotFoundError(f"Worker {worker_id} not found or already exiting")

            logger.debug(f"Heartbeat received from {worker_id}")
            return True

        except WorkerNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to record heartbeat for {worker_id}: {e}")
            return False

    def transition_status(
        self,
        worker_id: str,
        new_status: WorkerStatus,
        current_symbol: Optional[str] = None,
    ) -> WorkerProcess:
        """Transition worker to new status

        Args:
            worker_id: Worker instance ID
            new_status: New worker status
            current_symbol: Current symbol (required when entering HOLDING state)

        Returns:
            WorkerProcess: Updated worker process

        Raises:
            WorkerNotFoundError: If worker not found
            InvalidStatusTransitionError: If transition is invalid
        """
        # Get current worker
        worker = self.get_worker(worker_id)
        if worker is None:
            raise WorkerNotFoundError(f"Worker {worker_id} not found")

        # Validate status transition
        if not self._is_valid_transition(worker.status, new_status):
            raise InvalidStatusTransitionError(
                f"Invalid status transition: {worker.status.value} -> {new_status.value}"
            )

        # Validate current_symbol for HOLDING state
        if new_status == WorkerStatus.HOLDING and current_symbol is None:
            raise ValueError("current_symbol is required when transitioning to HOLDING state")

        try:
            now = datetime.now(timezone.utc)

            query = """
                UPDATE worker_processes
                SET status = %s, current_symbol = %s, last_heartbeat_at = %s, updated_at = CURRENT_TIMESTAMP
                WHERE worker_id = %s
                RETURNING id, worker_id, status, current_symbol, started_at, last_heartbeat_at, heartbeat_interval, created_at, updated_at
            """
            params = (new_status.value, current_symbol, now, worker_id)

            result = self.db.execute_query(query, params, fetch_one=True)

            logger.info(
                f"Worker {worker_id} status transition: {worker.status.value} -> {new_status.value}"
            )

            return WorkerProcess(
                id=result["id"],
                worker_id=result["worker_id"],
                status=WorkerStatus(result["status"]),
                current_symbol=result["current_symbol"],
                started_at=result["started_at"],
                last_heartbeat_at=result["last_heartbeat_at"],
                heartbeat_interval=result["heartbeat_interval"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to transition worker {worker_id} to {new_status.value}: {e}")
            raise

    def get_worker(self, worker_id: str) -> Optional[WorkerProcess]:
        """Get worker process by ID

        Args:
            worker_id: Worker instance ID

        Returns:
            Optional[WorkerProcess]: Worker process if found
        """
        return self._get_worker_by_id(worker_id)

    def list_active_workers(self) -> list[WorkerProcess]:
        """List all active (non-exiting) workers

        Returns:
            list[WorkerProcess]: List of active workers
        """
        try:
            query = """
                SELECT id, worker_id, status, current_symbol, started_at, last_heartbeat_at, heartbeat_interval, created_at, updated_at
                FROM worker_processes
                WHERE status != 'EXITING'
                ORDER BY started_at DESC
            """

            results = self.db.execute_query(query, fetch_all=True)

            return (
                [
                    WorkerProcess(
                        id=r["id"],
                        worker_id=r["worker_id"],
                        status=WorkerStatus(r["status"]),
                        current_symbol=r["current_symbol"],
                        started_at=r["started_at"],
                        last_heartbeat_at=r["last_heartbeat_at"],
                        heartbeat_interval=r["heartbeat_interval"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                    for r in results
                ]
                if results
                else []
            )

        except Exception as e:
            logger.error(f"Failed to list active workers: {e}")
            return []

    def cleanup_stale_workers(self) -> int:
        """Cleanup workers that have not sent heartbeat within TTL

        Returns:
            int: Number of workers cleaned up
        """
        try:
            now = datetime.now(timezone.utc)
            ttl_threshold = now - self.worker_ttl

            query = """
                UPDATE worker_processes
                SET status = 'EXITING', updated_at = CURRENT_TIMESTAMP
                WHERE status != 'EXITING' AND last_heartbeat_at < %s
                RETURNING id
            """
            params = (ttl_threshold,)

            results = self.db.execute_query(query, params, fetch_all=True)

            count = len(results) if results else 0
            if count > 0:
                logger.info(f"Cleaned up {count} stale workers")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup stale workers: {e}")
            return 0

    def _get_worker_by_id(self, worker_id: str) -> Optional[WorkerProcess]:
        """Get worker by ID"""
        try:
            query = """
                SELECT id, worker_id, status, current_symbol, started_at, last_heartbeat_at, heartbeat_interval, created_at, updated_at
                FROM worker_processes
                WHERE worker_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = (worker_id,)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                return None

            return WorkerProcess(
                id=result["id"],
                worker_id=result["worker_id"],
                status=WorkerStatus(result["status"]),
                current_symbol=result["current_symbol"],
                started_at=result["started_at"],
                last_heartbeat_at=result["last_heartbeat_at"],
                heartbeat_interval=result["heartbeat_interval"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to get worker {worker_id}: {e}")
            return None

    def _is_valid_transition(
        self,
        current: WorkerStatus,
        new: WorkerStatus,
    ) -> bool:
        """Validate worker status transition

        Valid transitions:
        - IDLE -> SCANNING
        - SCANNING -> HOLDING
        - HOLDING -> SCANNING (after sell)
        - Any -> EXITING
        - EXITING -> (terminal state, no transitions out)
        """
        if new == WorkerStatus.EXITING:
            return True

        if current == WorkerStatus.IDLE:
            return new == WorkerStatus.SCANNING

        if current == WorkerStatus.SCANNING:
            return new == WorkerStatus.HOLDING

        if current == WorkerStatus.HOLDING:
            return new == WorkerStatus.SCANNING

        if current == WorkerStatus.EXITING:
            return False

        return False
