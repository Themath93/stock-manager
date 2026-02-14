"""Trading models for order management and position tracking.

This module provides core data models for:
- Order lifecycle management with idempotency
- Position tracking with P&L calculation
- Trading configuration
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from stock_manager.trading.strategies.base import Strategy


class OrderStatus(Enum):
    """Order lifecycle states."""

    CREATED = "created"
    VALIDATING = "validating"
    SUBMITTED = "submitted"
    PENDING_BROKER = "pending_broker"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PositionStatus(Enum):
    """Position lifecycle states."""

    OPEN = "open"
    OPEN_RECONCILED = "open_reconciled"
    CLOSED = "closed"
    STALE = "stale"


@dataclass
class Order:
    """Order with idempotency support.

    Attributes:
        order_id: Unique internal order identifier
        idempotency_key: Key for duplicate detection
        symbol: Stock symbol (e.g., "005930")
        side: Order side ("buy" or "sell")
        quantity: Number of shares
        price: Limit price (None for market orders)
        order_type: "limit" or "market"
        status: Current order status
        broker_order_id: Broker's order reference
        submission_attempts: Number of submission attempts
        max_attempts: Maximum retry attempts
        created_at: Order creation timestamp
        submitted_at: Broker submission timestamp
        filled_at: Order fill timestamp
    """

    order_id: str = field(default_factory=lambda: str(uuid4()))
    idempotency_key: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    side: str = ""  # "buy" or "sell"
    quantity: int = 0
    price: int | None = None  # None = market order
    order_type: str = "limit"  # "limit" or "market"
    status: OrderStatus = OrderStatus.CREATED
    broker_order_id: str | None = None
    submission_attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: datetime | None = None
    filled_at: datetime | None = None

    def can_retry(self) -> bool:
        """Check if order can be retried.

        Returns:
            True if order is eligible for retry
        """
        return (
            self.status in [OrderStatus.CREATED, OrderStatus.SUBMITTED]
            and self.submission_attempts < self.max_attempts
        )


@dataclass
class Position:
    """Stock position with P&L tracking.

    Attributes:
        symbol: Stock symbol
        quantity: Number of shares held
        entry_price: Average entry price
        current_price: Current market price
        stop_loss: Stop loss price level
        take_profit: Take profit price level
        unrealized_pnl: Unrealized profit/loss
        status: Current position status
        opened_at: Position open timestamp
        closed_at: Position close timestamp
    """

    symbol: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    unrealized_pnl: Decimal = Decimal("0")
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None


@dataclass(frozen=True)
class TradingConfig:
    """Trading configuration.

    Attributes:
        max_positions: Maximum concurrent positions
        polling_interval_sec: Order status polling interval
        rate_limit_per_sec: API rate limit
        max_position_size_pct: Maximum position size as portfolio percentage
        default_stop_loss_pct: Default stop loss percentage
        default_take_profit_pct: Default take profit percentage
    """

    max_positions: int = 1
    polling_interval_sec: float = 2.0
    rate_limit_per_sec: int = 20
    max_position_size_pct: Decimal = Decimal("0.10")
    default_stop_loss_pct: Decimal = Decimal("0.05")
    default_take_profit_pct: Decimal = Decimal("0.10")

    strategy: "Strategy | None" = None
    strategy_symbols: tuple[str, ...] = ()
    strategy_order_quantity: int = 1
    strategy_max_symbols_per_cycle: int = 50
    strategy_max_buys_per_cycle: int = 1
    strategy_run_interval_sec: float = 60.0
    auto_exit_cooldown_sec: float = 1.0
