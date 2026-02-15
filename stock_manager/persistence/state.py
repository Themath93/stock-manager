"""
Durable state persistence with crash recovery guarantees.

Protocol:
1. Write to temp file in same directory
2. fsync temp file (force to disk)
3. Atomic rename
4. fsync directory (ensure rename is durable)
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
import logging

from stock_manager.trading.models import Order, OrderStatus, Position, PositionStatus

logger = logging.getLogger(__name__)


@dataclass
class TradingState:
    """Complete trading state for persistence."""

    positions: dict[str, Any] = field(default_factory=dict)  # symbol -> Position dict
    pending_orders: dict[str, Any] = field(default_factory=dict)  # order_id -> Order dict
    risk_controls: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 2

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "positions": {
                symbol: _serialize_position(symbol, pos) for symbol, pos in self.positions.items()
            },
            "pending_orders": {
                order_id: _serialize_order(order_id, order)
                for order_id, order in self.pending_orders.items()
            },
            "risk_controls": dict(self.risk_controls),
            "last_updated": self.last_updated.isoformat(),
            "version": 2,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradingState":
        """Create from dict."""
        raw_positions = data.get("positions", {})
        raw_orders = data.get("pending_orders", {})
        raw_risk_controls = data.get("risk_controls", {})

        positions: dict[str, Position] = {}
        for symbol, raw in raw_positions.items():
            position = _deserialize_position(symbol, raw)
            if position is not None:
                positions[symbol] = position

        pending_orders: dict[str, Order] = {}
        for order_id, raw in raw_orders.items():
            order = _deserialize_order(order_id, raw)
            if order is not None:
                pending_orders[order_id] = order

        return cls(
            positions=positions,
            pending_orders=pending_orders,
            risk_controls=raw_risk_controls if isinstance(raw_risk_controls, dict) else {},
            last_updated=_parse_dt(data.get("last_updated")) or datetime.now(timezone.utc),
            version=int(data.get("version", 1)),
        )


def save_state_atomic(state: TradingState, path: Path) -> None:
    """
    Atomic write with durability guarantee.

    CRITICAL: This ensures state survives power failure/crash.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"

    # Step 1: Write to temp file
    with open(tmp_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)
        # Step 2: Force to disk (CRITICAL)
        f.flush()
        os.fsync(f.fileno())

    # Step 3: Atomic rename (POSIX guarantee)
    tmp_path.replace(path)

    # Step 4: Sync directory entry
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def load_state(path: Path) -> TradingState | None:
    """Load state from file, return None if not exists."""
    path = Path(path)
    if not path.exists():
        return None
    with open(path, "r") as f:
        data = json.load(f)
    return TradingState.from_dict(data)


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _serialize_position(symbol: str, position: Any) -> dict[str, Any]:
    if isinstance(position, Position):
        return {
            "symbol": position.symbol,
            "quantity": int(position.quantity),
            "entry_price": str(position.entry_price),
            "current_price": str(position.current_price)
            if position.current_price is not None
            else None,
            "stop_loss": str(position.stop_loss) if position.stop_loss is not None else None,
            "take_profit": str(position.take_profit) if position.take_profit is not None else None,
            "unrealized_pnl": str(position.unrealized_pnl),
            "status": position.status.value,
            "opened_at": position.opened_at.isoformat(),
            "closed_at": position.closed_at.isoformat() if position.closed_at is not None else None,
        }

    if isinstance(position, dict):
        # Legacy/dict compatibility path; normalize and persist as v2 schema.
        return {
            "symbol": str(position.get("symbol", symbol)),
            "quantity": int(position.get("quantity", 0)),
            "entry_price": str(position.get("entry_price", "0")),
            "current_price": str(position.get("current_price"))
            if position.get("current_price") is not None
            else None,
            "stop_loss": str(position.get("stop_loss"))
            if position.get("stop_loss") is not None
            else None,
            "take_profit": str(position.get("take_profit"))
            if position.get("take_profit") is not None
            else None,
            "unrealized_pnl": str(position.get("unrealized_pnl", "0")),
            "status": str(position.get("status", PositionStatus.OPEN.value)),
            "opened_at": str(position.get("opened_at", datetime.now(timezone.utc).isoformat())),
            "closed_at": str(position.get("closed_at"))
            if position.get("closed_at") is not None
            else None,
        }

    raise TypeError(f"Unsupported position type for {symbol}: {type(position)}")


def _deserialize_position(symbol: str, raw: Any) -> Position | None:
    if isinstance(raw, Position):
        return raw

    if isinstance(raw, str):
        # Legacy broken payload, e.g. "Position(...)". Skip and recover from broker later.
        logger.warning("Skipping legacy string position for %s during state load", symbol)
        return None

    if not isinstance(raw, dict):
        logger.warning("Skipping invalid position type for %s: %s", symbol, type(raw))
        return None

    try:
        parsed_symbol = str(raw.get("symbol", symbol))
        quantity = int(raw.get("quantity", 0))
        entry_price = _parse_decimal(raw.get("entry_price")) or Decimal("0")
        current_price = _parse_decimal(raw.get("current_price"))
        stop_loss = _parse_decimal(raw.get("stop_loss"))
        take_profit = _parse_decimal(raw.get("take_profit"))
        unrealized_pnl = _parse_decimal(raw.get("unrealized_pnl")) or Decimal("0")
        opened_at = _parse_dt(raw.get("opened_at")) or datetime.now(timezone.utc)
        closed_at = _parse_dt(raw.get("closed_at"))

        status_value = str(raw.get("status", PositionStatus.OPEN.value))
        try:
            status = PositionStatus(status_value)
        except ValueError:
            status = PositionStatus.OPEN

        return Position(
            symbol=parsed_symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            unrealized_pnl=unrealized_pnl,
            status=status,
            opened_at=opened_at,
            closed_at=closed_at,
        )
    except Exception as e:
        logger.warning("Skipping malformed position for %s: %s", symbol, e)
        return None


def _serialize_order(order_id: str, order: Any) -> dict[str, Any]:
    if isinstance(order, Order):
        return {
            "order_id": order.order_id,
            "idempotency_key": order.idempotency_key,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": int(order.quantity),
            "price": order.price,
            "order_type": order.order_type,
            "status": order.status.value,
            "broker_order_id": order.broker_order_id,
            "submission_attempts": int(order.submission_attempts),
            "max_attempts": int(order.max_attempts),
            "created_at": order.created_at.isoformat(),
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
        }

    if isinstance(order, dict):
        return {
            "order_id": str(order.get("order_id", order_id)),
            "idempotency_key": str(order.get("idempotency_key", "")),
            "symbol": str(order.get("symbol", "")),
            "side": str(order.get("side", "")),
            "quantity": int(order.get("quantity", 0)),
            "price": order.get("price"),
            "order_type": str(order.get("order_type", "limit")),
            "status": str(order.get("status", OrderStatus.CREATED.value)),
            "broker_order_id": order.get("broker_order_id"),
            "submission_attempts": int(order.get("submission_attempts", 0)),
            "max_attempts": int(order.get("max_attempts", 3)),
            "created_at": str(order.get("created_at", datetime.now(timezone.utc).isoformat())),
            "submitted_at": str(order.get("submitted_at")) if order.get("submitted_at") else None,
            "filled_at": str(order.get("filled_at")) if order.get("filled_at") else None,
        }

    raise TypeError(f"Unsupported order type for {order_id}: {type(order)}")


def _deserialize_order(order_id: str, raw: Any) -> Order | None:
    if isinstance(raw, Order):
        return raw

    if not isinstance(raw, dict):
        logger.warning("Skipping invalid order type for %s: %s", order_id, type(raw))
        return None

    try:
        status_value = str(raw.get("status", OrderStatus.CREATED.value))
        try:
            status = OrderStatus(status_value)
        except ValueError:
            status = OrderStatus.CREATED

        return Order(
            order_id=str(raw.get("order_id", order_id)),
            idempotency_key=str(raw.get("idempotency_key", "")),
            symbol=str(raw.get("symbol", "")),
            side=str(raw.get("side", "")),
            quantity=int(raw.get("quantity", 0)),
            price=raw.get("price"),
            order_type=str(raw.get("order_type", "limit")),
            status=status,
            broker_order_id=raw.get("broker_order_id"),
            submission_attempts=int(raw.get("submission_attempts", 0)),
            max_attempts=int(raw.get("max_attempts", 3)),
            created_at=_parse_dt(raw.get("created_at")) or datetime.now(timezone.utc),
            submitted_at=_parse_dt(raw.get("submitted_at")),
            filled_at=_parse_dt(raw.get("filled_at")),
        )
    except Exception as e:
        logger.warning("Skipping malformed order for %s: %s", order_id, e)
        return None
