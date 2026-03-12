"""
Crash recovery protocol for trading engine.

MUST run on every startup before trading begins.
BROKER IS SOURCE OF TRUTH - local state is reconciled to match broker.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
import logging

from stock_manager.trading.guardrails import infer_buy_fill_from_balance
from stock_manager.trading.models import Order, OrderStatus, Position, PositionStatus

logger = logging.getLogger(__name__)


class RecoveryResult(Enum):
    CLEAN = "clean"  # State matches broker
    RECONCILED = "reconciled"  # Mismatches resolved
    FAILED = "failed"  # Manual intervention required


@dataclass
class RecoveryReport:
    """Report from startup reconciliation."""

    result: RecoveryResult = RecoveryResult.CLEAN
    orphan_positions: list[str] = field(
        default_factory=list
    )  # At broker but not local
    missing_positions: list[str] = field(
        default_factory=list
    )  # Local but not at broker
    quantity_mismatches: dict[str, tuple[int, int]] = field(
        default_factory=dict
    )  # symbol: (local, broker)
    pending_orders: list[str] = field(
        default_factory=list
    )  # Orders in unknown state
    errors: list[str] = field(default_factory=list)


def startup_reconciliation(
    local_state: Any,  # TradingState
    client: Any,  # KISRestClient
    inquire_balance_func: Any,  # Function to call broker API
    save_state_func: Any,  # Function to save state
    state_path: Any,  # Path to state file
    inquire_daily_orders_func: Any | None = None,  # Function to query broker daily orders
) -> RecoveryReport:
    """
    MUST run on every startup before trading begins.

    Recovery Protocol:
    1. Load persisted local state
    2. Query broker for actual positions
    3. Query broker for pending orders
    4. Compare and reconcile
    5. Log all discrepancies
    6. Block trading until reconciled
    7. Save reconciled state
    8. Return report

    Args:
        local_state: Current local trading state
        client: KIS REST API client
        inquire_balance_func: Function to query broker balance
        save_state_func: Function to persist state
        state_path: Path to state file

    Returns:
        RecoveryReport with reconciliation results
    """
    report = RecoveryReport()

    try:
        # Step 1-2: Get broker positions
        broker_response = inquire_balance_func(client)
        if broker_response.get("rt_cd") != "0":
            report.result = RecoveryResult.FAILED
            report.errors.append(
                f"Failed to query broker: {broker_response.get('msg1')}"
            )
            return report

        broker_positions = broker_response.get("output1", [])
        broker_symbols = {p["pdno"] for p in broker_positions}
        local_symbols = set(local_state.positions.keys())

        daily_orders_response = None
        if inquire_daily_orders_func is not None:
            try:
                daily_orders_response = inquire_daily_orders_func(client)
            except Exception as e:
                report.errors.append(f"Failed to query daily orders: {e}")

        # Step 3: Find orphans (at broker, not local)
        for symbol in broker_symbols - local_symbols:
            report.orphan_positions.append(symbol)
            broker_qty = _get_broker_qty(broker_positions, symbol)
            _upsert_local_position(local_state.positions, symbol, broker_qty)
            logger.warning(
                f"Orphan position found at broker: {symbol} qty={broker_qty}"
            )

        # Step 4: Find missing (local, not at broker)
        for symbol in local_symbols - broker_symbols:
            report.missing_positions.append(symbol)
            _mark_local_position_stale(local_state.positions, symbol)
            logger.warning(f"Missing position at broker: {symbol}")

        # Step 5: Check quantity mismatches
        for symbol in broker_symbols & local_symbols:
            broker_qty = _get_broker_qty(broker_positions, symbol)
            local_qty = _get_local_qty(local_state.positions[symbol])
            if broker_qty != local_qty:
                report.quantity_mismatches[symbol] = (local_qty, broker_qty)
                # BROKER IS SOURCE OF TRUTH
                _set_local_qty(local_state.positions, symbol, broker_qty)
                logger.warning(
                    f"Quantity mismatch for {symbol}: local={local_qty}, broker={broker_qty}"
                )

        _recover_pending_orders(
            pending_orders=getattr(local_state, "pending_orders", {}),
            broker_positions=broker_positions,
            daily_orders_response=daily_orders_response,
            report=report,
        )

        # Step 6: Determine result
        if (
            report.orphan_positions
            or report.missing_positions
            or report.quantity_mismatches
            or report.pending_orders
        ):
            report.result = RecoveryResult.RECONCILED
        else:
            report.result = RecoveryResult.CLEAN

        # Step 7: Save reconciled state
        save_state_func(local_state, state_path)

        logger.info(f"Startup reconciliation complete: {report.result.value}")

    except Exception as e:
        report.result = RecoveryResult.FAILED
        report.errors.append(str(e))
        logger.error(f"Startup reconciliation failed: {e}")

    return report


def _get_broker_qty(broker_positions: list[dict], symbol: str) -> int:
    """Extract quantity for symbol from broker positions."""
    for pos in broker_positions:
        if pos.get("pdno") == symbol:
            return int(pos.get("hldg_qty", 0))
    return 0


def _get_local_qty(position: Any) -> int:
    if isinstance(position, Position):
        return int(position.quantity)
    if isinstance(position, dict):
        return int(position.get("quantity", 0))
    return int(getattr(position, "quantity", 0))


def _set_local_qty(positions: dict[str, Any], symbol: str, quantity: int) -> None:
    position = positions.get(symbol)
    if isinstance(position, Position):
        position.quantity = quantity
        return
    if isinstance(position, dict):
        position["quantity"] = quantity
        return
    positions[symbol] = {
        "symbol": symbol,
        "quantity": quantity,
        "status": PositionStatus.OPEN_RECONCILED.value,
    }


def _mark_local_position_stale(positions: dict[str, Any], symbol: str) -> None:
    position = positions.get(symbol)
    if isinstance(position, Position):
        position.status = PositionStatus.STALE
        return
    if isinstance(position, dict):
        position["status"] = PositionStatus.STALE.value
        return
    positions[symbol] = {
        "symbol": symbol,
        "quantity": 0,
        "status": PositionStatus.STALE.value,
    }


def _upsert_local_position(positions: dict[str, Any], symbol: str, quantity: int) -> None:
    if symbol in positions:
        _set_local_qty(positions, symbol, quantity)
        return
    positions[symbol] = Position(
        symbol=symbol,
        quantity=quantity,
        entry_price=Decimal("0"),
        status=PositionStatus.OPEN_RECONCILED,
    )


def _recover_pending_orders(
    *,
    pending_orders: dict[str, Any],
    broker_positions: list[dict[str, Any]],
    daily_orders_response: dict[str, Any] | None,
    report: RecoveryReport,
) -> None:
    broker_lookup = {str(pos.get("pdno")): pos for pos in broker_positions if isinstance(pos, dict)}
    daily_orders = daily_orders_response.get("output1", []) if isinstance(daily_orders_response, dict) else []
    if not isinstance(daily_orders, list):
        daily_orders = []

    for order_id, raw_order in list(pending_orders.items()):
        order = raw_order if isinstance(raw_order, Order) else None
        if order is None or order.status not in {
            OrderStatus.SUBMITTED,
            OrderStatus.PENDING_BROKER,
            OrderStatus.PARTIAL_FILL,
        }:
            continue

        broker_position = broker_lookup.get(order.symbol)
        broker_qty = _get_broker_qty(broker_positions, order.symbol)
        daily_order, daily_reason = _find_daily_order(daily_orders, order)

        if order.side == "buy" and daily_order is not None:
            daily_filled_qty = _extract_daily_filled_qty(daily_order)
            if daily_filled_qty > 0:
                order.status = OrderStatus.FILLED
                order.resolution_source = "daily_order"
                order.unresolved_reason = None
                order.filled_quantity = max(order.filled_quantity, min(order.quantity, daily_filled_qty))
                order.filled_avg_price = _to_decimal(
                    daily_order.get("avg_prvs")
                    or daily_order.get("avg_prc")
                    or daily_order.get("ccld_avg_prc")
                    or daily_order.get("ord_avg_prc")
                    or daily_order.get("avg_price")
                )
                order.filled_at = datetime.now(timezone.utc)
                continue

        if order.side == "buy" and broker_position is not None and broker_qty > 0:
            fill_decision = infer_buy_fill_from_balance(
                order_quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                position_quantity_at_submit=order.position_quantity_at_submit,
                broker_position_quantity=broker_qty,
            )
            if fill_decision.filled_delta > 0:
                order.filled_quantity = min(
                    order.quantity,
                    order.filled_quantity + fill_decision.filled_delta,
                )
                order.filled_avg_price = _to_decimal(
                    broker_position.get("pchs_avg_pric") or broker_position.get("PCHS_AVG_PRIC")
                )
                order.resolution_source = "balance"
                order.filled_at = datetime.now(timezone.utc)
                if order.filled_quantity >= order.quantity:
                    order.status = OrderStatus.FILLED
                    order.unresolved_reason = None
                    continue
                order.status = OrderStatus.PARTIAL_FILL

            order.last_reconciled_at = datetime.now(timezone.utc)
            order.unresolved_reason = (
                fill_decision.unresolved_reason or "pending_order_recovery_unresolved"
            )
            report.pending_orders.append(order_id)
            continue

        if daily_order is not None:
            if _looks_rejected_or_cancelled(daily_order):
                order.status = OrderStatus.REJECTED
                order.unresolved_reason = None
                order.last_event_at = datetime.now(timezone.utc)
                continue
            if order.side == "sell":
                daily_filled_qty = _extract_daily_filled_qty(daily_order)
                if daily_filled_qty > 0:
                    order.status = OrderStatus.FILLED
                    order.resolution_source = "daily_order"
                    order.unresolved_reason = None
                    order.filled_quantity = max(order.filled_quantity, min(order.quantity, daily_filled_qty))
                    order.filled_at = datetime.now(timezone.utc)
                    continue

        order.last_reconciled_at = datetime.now(timezone.utc)
        order.unresolved_reason = daily_reason or "pending_order_recovery_unresolved"
        report.pending_orders.append(order_id)


def _find_daily_order(
    daily_orders: list[dict[str, Any]], order: Order
) -> tuple[dict[str, Any] | None, str | None]:
    for item in daily_orders:
        if not isinstance(item, dict):
            continue
        broker_order_id = item.get("odno") or item.get("ODNO")
        if broker_order_id not in (None, "") and order.broker_order_id:
            if str(broker_order_id) == order.broker_order_id:
                return item, None
    candidates: list[dict[str, Any]] = []
    for item in daily_orders:
        if not isinstance(item, dict):
            continue
        symbol = item.get("pdno") or item.get("PDNO")
        if str(symbol or "") != order.symbol:
            continue
        side = item.get("sll_buy_dvsn_cd") or item.get("SLL_BUY_DVSN_CD")
        if side is None:
            continue
        normalized_side = "buy" if str(side) == "02" else "sell" if str(side) == "01" else None
        if normalized_side == order.side:
            candidates.append(item)
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        return None, "ambiguous_daily_order_match"
    return None, "no_daily_order_match"


def _extract_daily_filled_qty(item: dict[str, Any]) -> int:
    for key in (
        "tot_ccld_qty",
        "TOT_CCLD_QTY",
        "ccld_qty",
        "CCLD_QTY",
        "tot_ccld_cqty",
        "TOT_CCLD_CQTY",
    ):
        value = item.get(key)
        if value not in (None, ""):
            try:
                return int(Decimal(str(value)))
            except Exception:
                continue
    return 0


def _looks_rejected_or_cancelled(item: dict[str, Any]) -> bool:
    payload = " ".join(
        str(item.get(key, ""))
        for key in ("ord_stts", "ord_sttus", "ccld_dvsn", "msg1", "status")
    ).lower()
    return any(token in payload for token in ("reject", "거부", "취소", "cancel"))


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
