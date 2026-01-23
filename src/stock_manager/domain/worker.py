"""
Worker Domain Models

Worker process and related domain models for SPEC-BACKEND-WORKER-004.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum


class WorkerStatus(Enum):
    """Worker status (ED-001: Worker Status Machine)"""

    IDLE = "IDLE"  # Initial state, not yet started
    SCANNING = "SCANNING"  # Scanning market for candidates
    HOLDING = "HOLDING"  # Holding a position, waiting for sell signal
    EXITING = "EXITING"  # Graceful shutdown in progress


@dataclass
class StockLock:
    """Stock lock for multi-worker coordination (WH-001)

    Prevents multiple workers from buying the same stock simultaneously.
    Uses PostgreSQL row-level locks with TTL for crash recovery.
    """

    id: int
    symbol: str  # Stock symbol (e.g., "005930")
    worker_id: str  # Worker instance ID
    acquired_at: datetime  # When lock was acquired
    expires_at: datetime  # Lock expiration (TTL)
    heartbeat_at: datetime  # Last heartbeat timestamp
    status: str  # "ACTIVE" or "EXPIRED"
    created_at: datetime
    updated_at: datetime

    def is_valid(self) -> bool:
        """Check if lock is still valid (not expired)"""
        return self.status == "ACTIVE" and datetime.utcnow() < self.expires_at

    def needs_renewal(self, ttl: timedelta) -> bool:
        """Check if lock needs to be renewed soon"""
        time_until_expiry = self.expires_at - datetime.utcnow()
        return time_until_expiry < (ttl / 2)


@dataclass
class WorkerProcess:
    """Worker process tracking (WH-002)

    Tracks active worker processes for crash recovery and monitoring.
    """

    id: int
    worker_id: str  # Unique worker instance ID
    status: WorkerStatus  # Current worker status
    current_symbol: str | None  # Currently held stock symbol (if HOLDING)
    started_at: datetime  # When worker started
    last_heartbeat_at: datetime  # Last heartbeat timestamp
    heartbeat_interval: timedelta  # Heartbeat interval
    created_at: datetime
    updated_at: datetime

    def is_alive(self, ttl: timedelta) -> bool:
        """Check if worker is alive based on heartbeat"""
        time_since_heartbeat = datetime.utcnow() - self.last_heartbeat_at
        return time_since_heartbeat < (ttl * 3)


@dataclass
class Candidate:
    """Candidate stock for trading (WT-002)

    Represents a stock that meets initial screening criteria
    and is ready for strategy evaluation.
    """

    symbol: str  # Stock symbol
    name: str  # Stock name
    current_price: Decimal  # Current market price
    volume: int  # Recent trading volume
    change_percent: Decimal  # Price change percentage
    discovered_at: datetime  # When candidate was discovered
    metadata: dict  # Additional candidate metadata (e.g., technical indicators)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "current_price": float(self.current_price),
            "volume": self.volume,
            "change_percent": float(self.change_percent),
            "discovered_at": self.discovered_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class PositionSnapshot:
    """Position snapshot for PnL calculation (WH-003)

    Captures position state at a specific point in time
    for PnL calculation.
    """

    symbol: str  # Stock symbol
    qty: Decimal  # Position quantity (positive for long, negative for short)
    avg_price: Decimal  # Average entry price
    current_price: Decimal  # Current market price
    timestamp: datetime  # Snapshot timestamp
    realized_pnl: Decimal  # Realized PnL up to this point
    metadata: dict  # Additional metadata

    def calculate_unrealized_pnl(self) -> Decimal:
        """Calculate unrealized PnL"""
        return (self.current_price - self.avg_price) * self.qty

    def calculate_total_pnl(self) -> Decimal:
        """Calculate total PnL (realized + unrealized)"""
        return self.realized_pnl + self.calculate_unrealized_pnl()


@dataclass
class DailySummary:
    """Daily PnL summary (WH-004)

    Daily summary of trading performance including realized/unrealized PnL,
    win rate, and trading statistics.
    """

    id: int
    worker_id: str  # Worker ID
    summary_date: datetime.date  # Summary date (UTC)
    total_trades: int  # Total number of trades executed
    winning_trades: int  # Number of winning trades
    losing_trades: int  # Number of losing trades
    gross_profit: Decimal  # Total gross profit from winning trades
    gross_loss: Decimal  # Total gross loss from losing trades
    net_pnl: Decimal  # Net PnL (profit - loss)
    unrealized_pnl: Decimal  # Unrealized PnL from open positions
    max_drawdown: Decimal  # Maximum drawdown during the day
    win_rate: Decimal  # Win rate (winning_trades / total_trades)
    profit_factor: Decimal  # Profit factor (gross_profit / gross_loss)
    created_at: datetime
    updated_at: datetime

    def calculate_win_rate(self) -> Decimal:
        """Calculate win rate"""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(self.winning_trades) / Decimal(self.total_trades)

    def calculate_profit_factor(self) -> Decimal:
        """Calculate profit factor"""
        if self.gross_loss == 0:
            return Decimal("0") if self.gross_profit == 0 else Decimal("999.99")
        return self.gross_profit / abs(self.gross_loss)
