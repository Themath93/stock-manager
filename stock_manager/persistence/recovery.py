"""
Crash recovery protocol for trading engine.

MUST run on every startup before trading begins.
BROKER IS SOURCE OF TRUTH - local state is reconciled to match broker.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import logging

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
        if str(broker_response.get("rt_cd")) != "0":
            reason = broker_response.get("msg1") or "unknown error"
            report.result = RecoveryResult.FAILED
            report.errors.append(f"Failed to query broker balance: {reason}")
            return report

        broker_positions = broker_response.get("output1", [])
        if not isinstance(broker_positions, list):
            broker_positions = []
        broker_symbols = {
            symbol for symbol in (_get_broker_symbol(p) for p in broker_positions) if symbol
        }
        local_symbols = set(local_state.positions.keys())

        # Step 3: Find orphans (at broker, not local)
        for symbol in broker_symbols - local_symbols:
            report.orphan_positions.append(symbol)
            broker_qty = _get_broker_qty(broker_positions, symbol)
            # Add to local state
            local_state.positions[symbol] = {
                "symbol": symbol,
                "quantity": broker_qty,
                "status": "open_reconciled",
            }
            logger.warning(
                f"Orphan position found at broker: {symbol} qty={broker_qty}"
            )

        # Step 4: Find missing (local, not at broker)
        for symbol in local_symbols - broker_symbols:
            report.missing_positions.append(symbol)
            local_state.positions[symbol]["status"] = "stale"
            logger.warning(f"Missing position at broker: {symbol}")

        # Step 5: Check quantity mismatches
        for symbol in broker_symbols & local_symbols:
            broker_qty = _get_broker_qty(broker_positions, symbol)
            local_qty = local_state.positions[symbol].get("quantity", 0)
            if broker_qty != local_qty:
                report.quantity_mismatches[symbol] = (local_qty, broker_qty)
                # BROKER IS SOURCE OF TRUTH
                local_state.positions[symbol]["quantity"] = broker_qty
                logger.warning(
                    f"Quantity mismatch for {symbol}: local={local_qty}, broker={broker_qty}"
                )

        # Step 6: Determine result
        if (
            report.orphan_positions
            or report.missing_positions
            or report.quantity_mismatches
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
        if _get_broker_symbol(pos) == symbol:
            qty = pos.get("hldg_qty")
            if qty is None:
                qty = pos.get("HLDG_QTY", 0)
            return int(qty or 0)
    return 0


def _get_broker_symbol(position: dict) -> str:
    """Extract symbol key from broker position dict with key-variant support."""
    symbol = position.get("pdno")
    if symbol is None:
        symbol = position.get("PDNO")
    return str(symbol) if symbol is not None else ""
