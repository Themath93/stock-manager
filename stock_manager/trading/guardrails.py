"""Pure guardrail decision helpers for runtime trading behavior.

This module intentionally contains only immutable decision models and pure
functions so the engine can keep side effects at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AutoExitTrigger = Literal["stop_loss", "take_profit"]
RecoveryMode = Literal["warn", "block"]
WebSocketLifecycleStatus = Literal["connected", "closed", "reconnect_exhausted"]


@dataclass(frozen=True)
class AutoExitOrderDecision:
    order_type: Literal["market", "limit"]
    price: int | None


@dataclass(frozen=True)
class StartupGuardDecision:
    should_block_trading: bool
    degraded_reason: str | None


@dataclass(frozen=True)
class BuyFillInferenceDecision:
    filled_delta: int
    unresolved_reason: str | None


@dataclass(frozen=True)
class RuntimeGuardDecision:
    should_block_trading: bool
    degraded_reason: str | None


@dataclass(frozen=True)
class WebSocketGuardDecision:
    start_polling_fallback: bool
    should_block_trading: bool
    degraded_reason: str | None


def resolve_auto_exit_order(
    *, trigger_type: AutoExitTrigger, current_price: int | None
) -> AutoExitOrderDecision:
    """Resolve the order shape for an automatic exit."""
    if trigger_type == "stop_loss":
        return AutoExitOrderDecision(order_type="market", price=None)

    if current_price is None or current_price <= 0:
        raise ValueError("take_profit requires a positive current_price")

    return AutoExitOrderDecision(order_type="limit", price=current_price)


def evaluate_startup_guard(
    *,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    recovery_mode: RecoveryMode,
    recovery_result: str,
    unresolved_order_count: int,
) -> StartupGuardDecision:
    """Return whether startup should fail closed."""
    normalized_result = recovery_result.strip().lower()

    if is_paper_trading or allow_unsafe_trading or recovery_mode != "block":
        return StartupGuardDecision(should_block_trading=False, degraded_reason=None)

    if normalized_result == "failed":
        return StartupGuardDecision(
            should_block_trading=True,
            degraded_reason="startup_recovery_failed",
        )

    if unresolved_order_count > 0:
        return StartupGuardDecision(
            should_block_trading=True,
            degraded_reason="startup_recovery_unresolved_orders",
        )

    return StartupGuardDecision(should_block_trading=False, degraded_reason=None)


def infer_buy_fill_from_balance(
    *,
    order_quantity: int,
    filled_quantity: int,
    position_quantity_at_submit: int | None,
    broker_position_quantity: int | None,
) -> BuyFillInferenceDecision:
    """Infer buy-side fill progress from a broker balance snapshot.

    The balance snapshot is only authoritative for the delta above the
    submit-time baseline. If the baseline is missing, the engine must remain
    conservative and keep the order unresolved.
    """
    if broker_position_quantity is None:
        return BuyFillInferenceDecision(
            filled_delta=0,
            unresolved_reason="buy_fill_balance_unavailable",
        )

    if position_quantity_at_submit is None:
        return BuyFillInferenceDecision(
            filled_delta=0,
            unresolved_reason="buy_fill_baseline_missing",
        )

    baseline = max(position_quantity_at_submit, 0)
    broker_quantity = max(broker_position_quantity, 0)
    total_increase = max(broker_quantity - baseline, 0)
    inferred_target = min(max(order_quantity, 0), total_increase)
    delta = max(0, inferred_target - max(filled_quantity, 0))

    if delta > 0:
        return BuyFillInferenceDecision(filled_delta=delta, unresolved_reason=None)

    return BuyFillInferenceDecision(
        filled_delta=0,
        unresolved_reason="buy_fill_requires_quantity_increase",
    )


def evaluate_runtime_guard(
    *,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    has_discrepancies: bool,
) -> RuntimeGuardDecision:
    """Return whether runtime reconciliation drift should block trading."""
    if not has_discrepancies or is_paper_trading or allow_unsafe_trading:
        return RuntimeGuardDecision(should_block_trading=False, degraded_reason=None)

    return RuntimeGuardDecision(
        should_block_trading=True,
        degraded_reason="runtime_reconciliation_drift",
    )


def evaluate_websocket_guard(
    *,
    lifecycle_status: WebSocketLifecycleStatus,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    websocket_monitoring_enabled: bool,
    websocket_execution_notice_enabled: bool,
) -> WebSocketGuardDecision:
    """Return how the engine should react to websocket lifecycle changes."""
    if lifecycle_status != "reconnect_exhausted":
        return WebSocketGuardDecision(
            start_polling_fallback=False,
            should_block_trading=False,
            degraded_reason=None,
        )

    should_block = (
        websocket_execution_notice_enabled and not is_paper_trading and not allow_unsafe_trading
    )
    return WebSocketGuardDecision(
        start_polling_fallback=websocket_monitoring_enabled,
        should_block_trading=should_block,
        degraded_reason="execution_stream_unavailable" if should_block else None,
    )
