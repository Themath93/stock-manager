"""
State Recovery Service

Handles state recovery operations including DB/broker synchronization
and unfilled order recovery. Implements SPEC-BACKEND-INFRA-003 requirements.

References:
- SPEC-BACKEND-INFRA-003: State Recovery
- ED-003: State recovered event
- ED-004: Unfilled orders recovered event
- WT-002: DB/broker comparison, broker takes precedence
- WT-003: Critical error → trading stop
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

from ..domain.market_lifecycle import (
    RecoveryResult,
    RecoveryStatus,
    SystemStateEnum,
)
from ..domain.order import Order, OrderStatus
from ..adapters.broker.port import BrokerPort
from ..service_layer.order_service import OrderService
from ..service_layer.position_service import PositionService

logger = logging.getLogger(__name__)


class StateRecoveryError(Exception):
    """State recovery operation failed"""

    pass


class StateRecoveryService(ABC):
    """State recovery service interface (SPEC 4.2)

    Handles state recovery and synchronization operations.
    """

    @abstractmethod
    def recover(self) -> RecoveryResult:
        """Recover system state (ED-003)

        Synchronizes DB and broker states, recovers unfilled orders,
        and recalculates positions.

        Returns:
            RecoveryResult: Recovery operation result

        Raises:
            StateRecoveryError: If recovery fails critically
        """
        pass

    @abstractmethod
    def sync_unfilled_orders(self) -> int:
        """Synchronize unfilled orders with broker state (ED-004)

        Queries DB for unfilled orders, compares with broker state,
        and updates DB to match broker (WT-002).

        Returns:
            int: Number of orders synchronized
        """
        pass

    @abstractmethod
    def recalculate_positions(self) -> int:
        """Recalculate positions from fill history

        Recalculates all positions from scratch using fill records
        to ensure consistency.

        Returns:
            int: Number of positions recalculated
        """
        pass


class StateRecoveryServiceImpl(StateRecoveryService):
    """State recovery service implementation

    Implements comprehensive state recovery including order
    synchronization and position recalculation.
    """

    def __init__(
        self,
        broker: BrokerPort,
        order_service: OrderService,
        position_service: PositionService,
        db_connection,
    ):
        """Initialize state recovery service

        Args:
            broker: Broker adapter for API operations
            order_service: Order service for order management
            position_service: Position service for position calculations
            db_connection: Database connection
        """
        self.broker = broker
        self.order_service = order_service
        self.position_service = position_service
        self.db = db_connection

    def recover(self) -> RecoveryResult:
        """Recover system state (ED-003)

        Executes comprehensive state recovery:
        1. Get pending orders from DB
        2. Get current orders from broker
        3. Compare and synchronize (WT-002)
        4. Recalculate positions
        5. Log recovery result

        Returns:
            RecoveryResult: Recovery operation result

        Raises:
            StateRecoveryError: If critical recovery failure occurs
        """
        logger.info("Starting state recovery")

        orders_synced = 0
        positions_recalculated = 0
        mismatches_found = 0
        details: Dict[str, Any] = {}

        try:
            # Step 1: Synchronize unfilled orders
            orders_synced = self.sync_unfilled_orders()
            details["orders_synced"] = orders_synced

            # Step 2: Recalculate positions
            positions_recalculated = self.recalculate_positions()
            details["positions_recalculated"] = positions_recalculated

            # Step 3: Count mismatches for logging
            mismatches_found = self._count_mismatches()
            details["mismatches_found"] = mismatches_found

            # Determine recovery status
            if orders_synced == 0 and positions_recalculated == 0:
                status = RecoveryStatus.SUCCESS
                logger.info("State recovery completed: no changes needed")
            elif mismatches_found == 0:
                status = RecoveryStatus.SUCCESS
                logger.info(
                    f"State recovery completed: {orders_synced} orders synced, "
                    f"{positions_recalculated} positions recalculated"
                )
            else:
                status = RecoveryStatus.PARTIAL
                logger.warning(
                    f"State recovery partial: {orders_synced} orders synced, "
                    f"{positions_recalculated} positions recalculated, "
                    f"{mismatches_found} mismatches remain"
                )

            result = RecoveryResult(
                success=True,
                status=status,
                orders_synced=orders_synced,
                positions_recalculated=positions_recalculated,
                mismatches_found=mismatches_found,
                details=details,
                recovered_at=datetime.now(),
            )

            # Log StateRecoveredEvent (ED-003)
            self._log_event("INFO", "StateRecoveredEvent", result.to_dict())

            return result

        except Exception as e:
            logger.error(f"State recovery failed: {e}")

            # Log failure event
            self._log_event(
                "ERROR",
                "StateRecoveryFailed",
                {
                    "error": str(e),
                    "orders_synced": orders_synced,
                    "positions_recalculated": positions_recalculated,
                },
            )

            # Check if this is a critical error requiring STOP mode (WT-003)
            if self._is_critical_error(e):
                logger.critical("Critical recovery error, entering STOP mode")
                raise StateRecoveryError(f"Critical recovery failure: {e}") from e

            # Non-critical error, return partial result
            return RecoveryResult(
                success=False,
                status=RecoveryStatus.FAILED,
                orders_synced=orders_synced,
                positions_recalculated=positions_recalculated,
                mismatches_found=mismatches_found,
                details={"error": str(e)},
                recovered_at=datetime.now(),
            )

    def sync_unfilled_orders(self) -> int:
        """Synchronize unfilled orders with broker state (ED-004, WT-002)

        Process:
        1. Query DB for orders with status SENT or PARTIAL
        2. Query broker for current order status
        3. Compare statuses
        4. If mismatch, update DB to match broker (broker is authoritative)

        Returns:
            int: Number of orders synchronized
        """
        logger.info("Synchronizing unfilled orders")

        # Get pending orders from DB
        db_orders = self.order_service.get_pending_orders()
        logger.info(f"Found {len(db_orders)} pending orders in DB")

        synced_count = 0

        for db_order in db_orders:
            try:
                # Get broker orders
                # TODO: Get actual account ID from config
                broker_orders = self.broker.get_orders(account_id="0000000000")

                # Find matching broker order
                broker_order = None
                if db_order.broker_order_id:
                    for bo in broker_orders:
                        if bo.broker_order_id == db_order.broker_order_id:
                            broker_order = bo
                            break

                if not broker_order:
                    logger.warning(
                        f"Order {db_order.id} (broker_id: {db_order.broker_order_id}) "
                        "not found in broker"
                    )
                    continue

                # Compare statuses
                broker_status = self._broker_status_to_order_status(broker_order.status)

                if broker_status != db_order.status:
                    logger.warning(
                        f"Status mismatch for order {db_order.id}: "
                        f"DB={db_order.status.value}, Broker={broker_order.status}"
                    )

                    # Update DB to match broker (WT-002: broker takes precedence)
                    self.order_service._update_order_status(
                        db_order.id, broker_status, db_order.broker_order_id
                    )

                    # Log sync event
                    self._log_event(
                        "INFO",
                        "OrderStatusSynced",
                        {
                            "order_id": db_order.id,
                            "broker_order_id": db_order.broker_order_id,
                            "db_status": db_order.status.value,
                            "broker_status": broker_order.status,
                            "new_status": broker_status.value,
                        },
                    )

                    synced_count += 1

            except Exception as e:
                logger.error(f"Error syncing order {db_order.id}: {e}")
                # Continue with next order instead of failing entire recovery

        logger.info(f"Order synchronization completed: {synced_count} orders synced")

        # Log UnfilledOrdersRecoveredEvent (ED-004)
        if synced_count > 0:
            self._log_event(
                "INFO",
                "UnfilledOrdersRecoveredEvent",
                {
                    "orders_synced": synced_count,
                    "total_pending": len(db_orders),
                },
            )

        return synced_count

    def recalculate_positions(self) -> int:
        """Recalculate positions from fill history

        Recalculates all positions from scratch to ensure consistency
        with fill history.

        Returns:
            int: Number of positions recalculated
        """
        logger.info("Recalculating positions")

        # Get all unique symbols from fills
        symbols_query = """
        SELECT DISTINCT symbol
        FROM fills
        ORDER BY symbol
        """

        with self.db.cursor() as cursor:
            cursor.execute(symbols_query)
            rows = cursor.fetchall()

        symbols = [row[0] for row in rows]
        recalculated_count = 0

        for symbol in symbols:
            try:
                # Recalculate position
                position = self.position_service.calculate_position(symbol)

                # Update in database
                self.position_service._upsert_position(position)

                recalculated_count += 1

            except Exception as e:
                logger.error(f"Error recalculating position for {symbol}: {e}")
                # Continue with next symbol

        logger.info(
            f"Position recalculation completed: {recalculated_count} positions recalculated"
        )

        return recalculated_count

    def _count_mismatches(self) -> int:
        """Count remaining DB/broker mismatches

        Returns:
            int: Number of remaining mismatches
        """
        # For now, return 0 (actual implementation would query recent sync logs)
        return 0

    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if error is critical requiring STOP mode (WT-003)

        Args:
            error: Exception to evaluate

        Returns:
            bool: True if error is critical
        """
        # Define critical error patterns
        critical_patterns = [
            "database connection",
            "authentication failed",
            "broker connection",
            "critical infrastructure",
        ]

        error_message = str(error).lower()

        return any(pattern in error_message for pattern in critical_patterns)

    def _broker_status_to_order_status(self, broker_status: str) -> OrderStatus:
        """Convert broker status to OrderStatus

        Args:
            broker_status: Broker status string (Korean)

        Returns:
            OrderStatus: Corresponding OrderStatus enum
        """
        status_map = {
            "접수": OrderStatus.NEW,
            "주문중": OrderStatus.SENT,
            "체결": OrderStatus.PARTIAL,
            "체결완료": OrderStatus.FILLED,
            "주문취소": OrderStatus.CANCELED,
            "주문거부": OrderStatus.REJECTED,
        }

        return status_map.get(broker_status, OrderStatus.ERROR)

    def _log_event(self, level: str, message: str, payload: dict = None) -> None:
        """Log event to database

        Args:
            level: Log level (INFO, WARN, ERROR)
            message: Event message
            payload: Event payload
        """
        query = """
        INSERT INTO events (level, message, payload)
        VALUES (%s, %s, %s)
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(query, (level, message, payload if payload else None))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
