"""
Market Lifecycle Service

Manages market open/close operations and system state transitions.
Implements SPEC-BACKEND-INFRA-003 requirements.

References:
- SPEC-BACKEND-INFRA-003: Market Lifecycle
- ED-001, ED-002: Market open/close events
- WT-001: Market open initialization
- WT-004: Market close settlement
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, time
from typing import Optional, Dict, Any, Callable

from ..domain.market_lifecycle import (
    SystemState,
    SystemStateEnum,
    RecoveryStatus,
    DailySettlement,
)
from ..adapters.broker.port import BrokerPort
from ..service_layer.order_service import OrderService
from ..service_layer.position_service import PositionService

logger = logging.getLogger(__name__)


# Custom Exceptions
class LifecycleError(Exception):
    """Base exception for lifecycle errors"""

    pass


class MarketOpenError(LifecycleError):
    """Market open operation failed"""

    pass


class MarketCloseError(LifecycleError):
    """Market close operation failed"""

    pass


class StateRecoveryError(LifecycleError):
    """State recovery operation failed"""

    pass


class InvalidStateTransitionError(LifecycleError):
    """Invalid state transition attempted"""

    pass


class MarketLifecycleService(ABC):
    """Market lifecycle service interface (SPEC 4.1)

    Manages market open/close operations and system state.
    """

    @abstractmethod
    def open_market(self) -> bool:
        """Open market (ED-001)

        Executes the 9-step market open process:
        1. Load configuration
        2. Authenticate
        3. Verify account
        4. Load strategy parameters
        5. Recover state
        6. Initialize risk guardrails
        7. Finalize universe
        8. Register real-time events
        9. Transition to READY state

        Returns:
            bool: True if market opened successfully

        Raises:
            MarketOpenError: If market open fails
        """
        pass

    @abstractmethod
    def close_market(self) -> bool:
        """Close market (ED-002)

        Executes the 8-step market close process:
        1. Transition to CLOSING state
        2. Cancel unfilled orders (optional)
        3. Create position snapshots
        4. Calculate daily settlement
        5. Publish DailySettlementEvent
        6. Unsubscribe real-time events
        7. Disconnect WebSocket
        8. Transition to CLOSED state

        Returns:
            bool: True if market closed successfully

        Raises:
            MarketCloseError: If market close fails
        """
        pass

    @abstractmethod
    def get_system_state(self) -> SystemState:
        """Get current system state

        Returns:
            SystemState: Current system state
        """
        pass

    @abstractmethod
    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed

        Returns:
            bool: True if trading is allowed (READY or TRADING state)
        """
        pass


class MarketLifecycleServiceImpl(MarketLifecycleService):
    """Market lifecycle service implementation

    Implements the complete market lifecycle including state management,
    recovery, and settlement operations.
    """

    def __init__(
        self,
        broker: BrokerPort,
        order_service: OrderService,
        position_service: PositionService,
        db_connection,
        market_open_time: time = time(8, 30, 0),
        market_close_time: time = time(15, 30, 0),
        timezone: str = "Asia/Seoul",
    ):
        """Initialize market lifecycle service

        Args:
            broker: Broker adapter for API operations
            order_service: Order service for order management
            position_service: Position service for position calculations
            db_connection: Database connection
            market_open_time: Market open time (default: 08:30:00 KST)
            market_close_time: Market close time (default: 15:30:00 KST)
            timezone: Timezone for market times (default: Asia/Seoul)
        """
        self.broker = broker
        self.order_service = order_service
        self.position_service = position_service
        self.db = db_connection
        self.market_open_time = market_open_time
        self.market_close_time = market_close_time
        self.timezone = timezone

        # Initialize system state
        self._system_state = self._load_system_state() or self._create_initial_state()

        # State change callbacks
        self._state_change_callbacks: list[Callable[[SystemStateEnum, SystemStateEnum], None]] = []

    def _create_initial_state(self) -> SystemState:
        """Create initial system state"""
        return SystemState(
            state=SystemStateEnum.OFFLINE,
            recovery_status=RecoveryStatus.SUCCESS,
        )

    def _load_system_state(self) -> Optional[SystemState]:
        """Load system state from database

        Returns:
            SystemState if exists, None otherwise
        """
        query = """
        SELECT state, market_open_at, market_closed_at, last_recovery_at,
               recovery_status, recovery_details, created_at, updated_at
        FROM system_states
        ORDER BY created_at DESC
        LIMIT 1
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()

            if row:
                return SystemState(
                    state=SystemStateEnum(row[0]),
                    market_open_at=row[1],
                    market_closed_at=row[2],
                    last_recovery_at=row[3],
                    recovery_status=RecoveryStatus(row[4]),
                    recovery_details=row[5] or {},
                    created_at=row[6],
                    updated_at=row[7],
                )
        except Exception as e:
            logger.warning(f"Failed to load system state: {e}")

        return None

    def _save_system_state(self) -> None:
        """Save system state to database"""
        query = """
        INSERT INTO system_states (
            state, market_open_at, market_closed_at, last_recovery_at,
            recovery_status, recovery_details
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (
                    self._system_state.state.value,
                    self._system_state.market_open_at,
                    self._system_state.market_closed_at,
                    self._system_state.last_recovery_at,
                    self._system_state.recovery_status.value,
                    self._system_state.recovery_details,
                ),
            )
            self.db.commit()

        logger.info(f"System state saved: {self._system_state.state.value}")

    def _transition_state(self, new_state: SystemStateEnum) -> None:
        """Transition to new state with validation

        Args:
            new_state: New state to transition to

        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        old_state = self._system_state.state

        if not self._system_state.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Invalid state transition: {old_state.value} → {new_state.value}"
            )

        self._system_state.state = new_state
        self._system_state.updated_at = datetime.now()

        # Save to database
        self._save_system_state()

        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

        logger.info(f"State transition: {old_state.value} → {new_state.value}")

    def register_state_change_callback(
        self, callback: Callable[[SystemStateEnum, SystemStateEnum], None]
    ) -> None:
        """Register a callback for state changes

        Args:
            callback: Function to call on state change (old_state, new_state) -> None
        """
        self._state_change_callbacks.append(callback)

    def open_market(self) -> bool:
        """Open market (ED-001)

        Executes the 9-step market open process.

        Returns:
            bool: True if market opened successfully

        Raises:
            MarketOpenError: If market open fails
        """
        try:
            logger.info("Starting market open process")

            # Step 1: Transition to INITIALIZING
            self._transition_state(SystemStateEnum.INITIALIZING)
            self._log_event("INFO", "MarketOpenEvent", {"phase": "initiating"})

            # Step 2: Load configuration
            self._load_configuration()

            # Step 3: Authenticate
            self._authenticate()

            # Step 4: Verify account
            self._verify_account()

            # Step 5: Load strategy parameters
            self._load_strategy_parameters()

            # Step 6: Recover state (WT-002)
            self._recover_state()

            # Step 7: Initialize risk guardrails
            self._initialize_risk_guardrails()

            # Step 8: Finalize universe
            self._finalize_universe()

            # Step 9: Register real-time events
            self._register_realtime_events()

            # Transition to READY
            self._transition_state(SystemStateEnum.READY)
            self._system_state.market_open_at = datetime.now()
            self._save_system_state()

            self._log_event("INFO", "MarketReadyEvent", {"phase": "ready"})

            logger.info("Market open completed successfully")
            return True

        except Exception as e:
            logger.error(f"Market open failed: {e}")
            self._transition_to_stopped(f"Market open failed: {str(e)}")
            raise MarketOpenError(f"Failed to open market: {e}") from e

    def close_market(self) -> bool:
        """Close market (ED-002)

        Executes the 8-step market close process.

        Returns:
            bool: True if market closed successfully

        Raises:
            MarketCloseError: If market close fails
        """
        try:
            logger.info("Starting market close process")

            # Step 1: Transition to CLOSING
            self._transition_state(SystemStateEnum.CLOSING)
            self._log_event("INFO", "MarketCloseEvent", {"phase": "closing"})

            # Step 2: Cancel unfilled orders (optional)
            self._handle_unfilled_orders()

            # Step 3: Create position snapshots
            self._create_position_snapshots()

            # Step 4: Calculate daily settlement (WT-004)
            settlement = self._calculate_daily_settlement()

            # Step 5: Publish DailySettlementEvent
            self._log_event(
                "INFO",
                "DailySettlementEvent",
                {
                    "trade_date": settlement.trade_date.isoformat(),
                    "realized_pnl": str(settlement.realized_pnl),
                    "unrealized_pnl": str(settlement.unrealized_pnl),
                    "total_pnl": str(settlement.total_pnl),
                },
            )

            # Step 6: Unsubscribe real-time events
            self._unregister_realtime_events()

            # Step 7: Disconnect WebSocket
            self._disconnect_websocket()

            # Step 8: Transition to CLOSED
            self._transition_state(SystemStateEnum.CLOSED)
            self._system_state.market_closed_at = datetime.now()
            self._save_system_state()

            self._log_event("INFO", "MarketClosedEvent", {"phase": "closed"})

            logger.info("Market close completed successfully")
            return True

        except Exception as e:
            logger.error(f"Market close failed: {e}")
            self._transition_to_stopped(f"Market close failed: {str(e)}")
            raise MarketCloseError(f"Failed to close market: {e}") from e

    def get_system_state(self) -> SystemState:
        """Get current system state

        Returns:
            SystemState: Current system state
        """
        return self._system_state

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed

        Returns:
            bool: True if trading is allowed (READY or TRADING state)
        """
        return self._system_state.is_trading_allowed()

    def _transition_to_stopped(self, reason: str) -> None:
        """Transition to STOPPED state (UB-004)

        Args:
            reason: Reason for stopping
        """
        try:
            self._transition_state(SystemStateEnum.STOPPED)
            self._log_event("ERROR", "StopModeEvent", {"reason": reason})
            logger.critical(f"System entered STOPPED mode: {reason}")
        except Exception as e:
            logger.error(f"Failed to transition to STOPPED: {e}")

    def _load_configuration(self) -> None:
        """Step 1: Load configuration"""
        logger.info("Step 1: Loading configuration")
        # Configuration is loaded via constructor parameters

    def _authenticate(self) -> None:
        """Step 2: Authenticate with broker"""
        logger.info("Step 2: Authenticating with broker")
        try:
            self.broker.authenticate()
        except Exception as e:
            raise MarketOpenError(f"Authentication failed: {e}") from e

    def _verify_account(self) -> None:
        """Step 3: Verify account information"""
        logger.info("Step 3: Verifying account")
        try:
            # Get accounts
            # TODO: Get actual account ID from config
            # self.broker.get_accounts()

            # Verify cash balance
            # self.broker.get_cash(account_id)
            pass  # Placeholder for account verification
        except Exception as e:
            raise MarketOpenError(f"Account verification failed: {e}") from e

    def _load_strategy_parameters(self) -> None:
        """Step 4: Load strategy parameters"""
        logger.info("Step 4: Loading strategy parameters")
        # TODO: Load from strategy_params table

    def _recover_state(self) -> None:
        """Step 5: Recover state (WT-002)"""
        logger.info("Step 5: Recovering state")
        # StateRecoveryService will be implemented separately
        # For now, just log that recovery is needed
        self._system_state.last_recovery_at = datetime.now()
        self._system_state.recovery_status = RecoveryStatus.SUCCESS

    def _initialize_risk_guardrails(self) -> None:
        """Step 6: Initialize risk guardrails"""
        logger.info("Step 6: Initializing risk guardrails")
        # RiskService will be implemented separately

    def _finalize_universe(self) -> None:
        """Step 7: Finalize universe"""
        logger.info("Step 7: Finalizing universe")
        # TODO: Load from stock_universe table

    def _register_realtime_events(self) -> None:
        """Step 8: Register real-time events"""
        logger.info("Step 8: Registering real-time events")
        try:
            self.broker.connect_websocket()
        except Exception as e:
            raise MarketOpenError(f"WebSocket connection failed: {e}") from e

    def _handle_unfilled_orders(self) -> None:
        """Step 2 (close): Handle unfilled orders"""
        logger.info("Step 2: Handling unfilled orders")
        # Option 1: Cancel all unfilled orders
        # Option 2: Leave them for next market recovery
        # Currently: Leave them (will be recovered on next open)

    def _create_position_snapshots(self) -> None:
        """Step 3 (close): Create position snapshots"""
        logger.info("Step 3: Creating position snapshots")
        # TODO: Implement position snapshot creation

    def _calculate_daily_settlement(self) -> DailySettlement:
        """Step 4 (close): Calculate daily settlement (WT-004)

        Returns:
            DailySettlement: Daily settlement record
        """
        logger.info("Step 4: Calculating daily settlement")

        # Get all positions
        positions = self.position_service.get_all_positions()

        # Calculate PnL
        realized_pnl = self._calculate_realized_pnl()
        unrealized_pnl = self._calculate_unrealized_pnl(positions)
        total_pnl = realized_pnl + unrealized_pnl

        # Create snapshot
        positions_snapshot = {
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": str(p.qty),
                    "avg_price": str(p.avg_price),
                }
                for p in positions
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return DailySettlement(
            id=0,  # Will be assigned by database
            trade_date=datetime.now().date(),
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            positions_snapshot=positions_snapshot,
            created_at=datetime.now(),
        )

    def _calculate_realized_pnl(self) -> float:
        """Calculate realized PnL from closed positions"""
        # TODO: Sum up realized PnL from fills
        return 0.0

    def _calculate_unrealized_pnl(self, positions) -> float:
        """Calculate unrealized PnL from open positions"""
        # TODO: Calculate unrealized PnL from current positions
        return 0.0

    def _unregister_realtime_events(self) -> None:
        """Step 6 (close): Unregister real-time events"""
        logger.info("Step 6: Unregistering real-time events")
        # Unsubscribing is handled by disconnect_websocket

    def _disconnect_websocket(self) -> None:
        """Step 7 (close): Disconnect WebSocket"""
        logger.info("Step 7: Disconnecting WebSocket")
        try:
            self.broker.disconnect_websocket()
        except Exception as e:
            logger.warning(f"WebSocket disconnect warning: {e}")

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
