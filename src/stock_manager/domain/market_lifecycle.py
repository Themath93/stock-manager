"""
Market Lifecycle Domain Models

Domain models for market lifecycle management including system state,
daily settlement, and market open/close operations.

References:
- SPEC-BACKEND-INFRA-003 (Market Lifecycle)
- UB-001: System State Machine
- ED-001 ~ ED-004: Market Events
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any


class SystemStateEnum(Enum):
    """System state machine (UB-001)

    State transitions:
    OFFLINE → INITIALIZING → READY → TRADING → CLOSING → CLOSED → INITIALIZING
                    ↓
                  STOPPED
    """

    OFFLINE = "OFFLINE"  # System not started
    INITIALIZING = "INITIALIZING"  # Market open in progress
    READY = "READY"  # Market open complete, ready for trading
    TRADING = "TRADING"  # Actively trading
    CLOSING = "CLOSING"  # Market close in progress
    CLOSED = "CLOSED"  # Market closed
    STOPPED = "STOPPED"  # Emergency stop mode (exception state)


class RecoveryStatus(Enum):
    """State recovery status"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass
class SystemState:
    """System state domain model (SPEC 3.1)

    Tracks the current state of the trading system including
    market open/close times and recovery status.
    """

    state: SystemStateEnum
    market_open_at: Optional[datetime] = None
    market_closed_at: Optional[datetime] = None
    last_recovery_at: Optional[datetime] = None
    recovery_status: RecoveryStatus = RecoveryStatus.SUCCESS
    recovery_details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed in current state

        Trading is only allowed in READY or TRADING states.
        STOPPED state blocks all trading operations (UB-004).
        """
        return self.state in [SystemStateEnum.READY, SystemStateEnum.TRADING]

    def is_market_open(self) -> bool:
        """Check if market is open (READY, TRADING, or CLOSING)"""
        return self.state in [
            SystemStateEnum.READY,
            SystemStateEnum.TRADING,
            SystemStateEnum.CLOSING,
        ]

    def can_transition_to(self, new_state: SystemStateEnum) -> bool:
        """Validate state transition (UB-001)

        Valid transitions:
        - OFFLINE → INITIALIZING
        - INITIALIZING → READY
        - READY → TRADING, CLOSING (PoC: allow direct close from READY)
        - TRADING → CLOSING
        - CLOSING → CLOSED
        - CLOSED → INITIALIZING
        - Any state → STOPPED (exception)
        """
        valid_transitions = {
            SystemStateEnum.OFFLINE: [SystemStateEnum.INITIALIZING],
            SystemStateEnum.INITIALIZING: [SystemStateEnum.READY, SystemStateEnum.STOPPED],
            # PoC: Allow READY → CLOSING for simplified close flow
            SystemStateEnum.READY: [
                SystemStateEnum.TRADING,
                SystemStateEnum.CLOSING,
                SystemStateEnum.STOPPED,
            ],
            SystemStateEnum.TRADING: [
                SystemStateEnum.TRADING,
                SystemStateEnum.CLOSING,
                SystemStateEnum.STOPPED,
            ],
            SystemStateEnum.CLOSING: [SystemStateEnum.CLOSED, SystemStateEnum.STOPPED],
            SystemStateEnum.CLOSED: [SystemStateEnum.INITIALIZING],
        }

        # STOPPED can be reached from any state (emergency)
        if new_state == SystemStateEnum.STOPPED:
            return True

        return new_state in valid_transitions.get(self.state, [])


@dataclass
class PositionSnapshot:
    """Position snapshot for daily settlement (WH-003)

    Captures position state at a specific point in time
    for PnL calculation and settlement.
    """

    symbol: str
    qty: Decimal
    avg_price: Decimal
    current_price: Decimal
    timestamp: datetime
    realized_pnl: Decimal = Decimal("0")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_unrealized_pnl(self) -> Decimal:
        """Calculate unrealized PnL"""
        return (self.current_price - self.avg_price) * self.qty

    def calculate_total_pnl(self) -> Decimal:
        """Calculate total PnL (realized + unrealized)"""
        return self.realized_pnl + self.calculate_unrealized_pnl()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "qty": str(self.qty),
            "avg_price": str(self.avg_price),
            "current_price": str(self.current_price),
            "timestamp": self.timestamp.isoformat(),
            "realized_pnl": str(self.realized_pnl),
            "unrealized_pnl": str(self.calculate_unrealized_pnl()),
            "total_pnl": str(self.calculate_total_pnl()),
            "metadata": self.metadata,
        }


@dataclass
class DailySettlement:
    """Daily settlement domain model (SPEC 3.2)

    Records daily trading performance including realized/unrealized PnL.
    Created at market close (WT-004).
    """

    id: int
    trade_date: date
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    positions_snapshot: Dict[str, Any]  # JSONB
    created_at: datetime
    updated_at: Optional[datetime] = None

    @property
    def net_pnl(self) -> Decimal:
        """Alias for total_pnl for compatibility"""
        return self.total_pnl


@dataclass
class RecoveryResult:
    """Result of state recovery operation (ED-003)"""

    success: bool
    status: RecoveryStatus
    orders_synced: int  # Number of orders synchronized
    positions_recalculated: int  # Number of positions recalculated
    mismatches_found: int  # Number of DB/broker mismatches
    details: Dict[str, Any] = field(default_factory=dict)
    recovered_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event logging"""
        return {
            "success": self.success,
            "status": self.status.value,
            "orders_synced": self.orders_synced,
            "positions_recalculated": self.positions_recalculated,
            "mismatches_found": self.mismatches_found,
            "details": self.details,
            "recovered_at": self.recovered_at.isoformat(),
        }
