"""Pure guardrail decision helpers for runtime trading behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


AutoExitTrigger = Literal["stop_loss", "take_profit"]
OperationalState = Literal["normal", "degraded_reduce_only", "blocked"]
OrderSide = Literal["buy", "sell"]
PendingOrderRecoveryStatus = Literal["unresolved", "partial_fill", "filled"]
RecoveryMode = Literal["warn", "block"]
WebSocketLifecycleStatus = Literal["connected", "closed", "reconnect_exhausted"]
RuntimeFaultAction = Literal["log_only", "reduce_only", "blocked"]
OrderPermissionRejectCode = Literal[
    "trading_disabled",
    "pending_same_side",
    "no_open_position",
    "exceeds_position",
    "invalid_quantity",
]

_DEGRADED_REDUCE_ONLY_REASONS = {
    "startup_recovery_unresolved_orders",
    "runtime_reconciliation_drift",
    "execution_stream_unavailable",
    "daily_loss_killswitch",
    "reconciliation_stale",
    "market_data_stale",
    "submission_result_unknown",
    "runtime_balance_unavailable",
}


@dataclass(frozen=True)
class AutoExitOrderDecision:
    order_type: Literal["market", "limit"]
    price: int | None


@dataclass(frozen=True)
class StartupGuardDecision:
    operational_state: OperationalState
    degraded_reason: str | None

    @property
    def should_block_trading(self) -> bool:
        return self.operational_state != "normal"


@dataclass(frozen=True)
class BuyFillInferenceDecision:
    filled_delta: int
    unresolved_reason: str | None


@dataclass(frozen=True)
class PendingOrderRecoveryDecision:
    target_filled_quantity: int
    fill_delta: int
    status: PendingOrderRecoveryStatus

    @property
    def should_keep_pending(self) -> bool:
        return self.status != "filled"


@dataclass(frozen=True)
class RuntimeGuardDecision:
    operational_state: OperationalState
    degraded_reason: str | None

    @property
    def should_block_trading(self) -> bool:
        return self.operational_state != "normal"


@dataclass(frozen=True)
class WebSocketGuardDecision:
    start_polling_fallback: bool
    operational_state: OperationalState
    degraded_reason: str | None

    @property
    def should_block_trading(self) -> bool:
        return self.operational_state != "normal"


@dataclass(frozen=True)
class OrderPermissionDecision:
    allowed: bool
    reject_code: OrderPermissionRejectCode | None = None
    reduce_only: bool = False


@dataclass(frozen=True)
class SubmissionRecoveryDecision:
    bind_broker_order: bool
    matched_broker_order_id: str | None
    keep_pending: bool
    downgrade_to_reduce_only: bool
    operator_action_required: bool


@dataclass(frozen=True)
class ExecutionIntegrityDecision:
    apply_event: bool
    dedupe_key: str | None
    downgrade_to_reduce_only: bool
    operator_action_required: bool
    reason: str | None = None


@dataclass(frozen=True)
class RuntimeFaultDecision:
    action: RuntimeFaultAction
    degraded_reason: str | None
    operator_action_required: bool

    @property
    def operational_state(self) -> OperationalState:
        if self.action == "blocked":
            return "blocked"
        if self.action == "reduce_only":
            return "degraded_reduce_only"
        return "normal"


@dataclass(frozen=True)
class RealtimeStartupDecision:
    quote_stream_active: bool
    start_polling_fallback: bool
    operational_state: OperationalState
    degraded_reason: str | None

    @property
    def should_block_trading(self) -> bool:
        return self.operational_state != "normal"


@dataclass(frozen=True)
class EngineOperabilityDecision:
    is_healthy: bool
    is_ready_for_new_orders: bool
    should_keep_session_running: bool
    operational_state: OperationalState


@dataclass(frozen=True)
class SessionHandoffDecision:
    should_stop: bool
    require_operator_handoff: bool
    summary: str | None


def resolve_auto_exit_order(
    *, trigger_type: AutoExitTrigger, current_price: int | None
) -> AutoExitOrderDecision:
    """Resolve the order shape for an automatic exit."""
    if trigger_type == "stop_loss":
        return AutoExitOrderDecision(order_type="market", price=None)

    if current_price is None or current_price <= 0:
        raise ValueError("take_profit requires a positive current_price")

    return AutoExitOrderDecision(order_type="limit", price=current_price)


def resolve_operational_state(*, degraded_reason: str | None) -> OperationalState:
    """Map a degraded reason to a concrete operational state."""
    if degraded_reason in (None, ""):
        return "normal"
    if degraded_reason == "startup_recovery_failed":
        return "blocked"
    if degraded_reason in _DEGRADED_REDUCE_ONLY_REASONS:
        return "degraded_reduce_only"
    return "blocked"


def evaluate_startup_guard(
    *,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    recovery_mode: RecoveryMode,
    recovery_result: str,
    unresolved_order_count: int,
) -> StartupGuardDecision:
    """Return how startup reconciliation should change engine operability."""
    normalized_result = recovery_result.strip().lower()

    if is_paper_trading or allow_unsafe_trading or recovery_mode != "block":
        return StartupGuardDecision(operational_state="normal", degraded_reason=None)

    if normalized_result == "failed":
        return StartupGuardDecision(
            operational_state="blocked",
            degraded_reason="startup_recovery_failed",
        )

    if unresolved_order_count > 0:
        return StartupGuardDecision(
            operational_state="degraded_reduce_only",
            degraded_reason="startup_recovery_unresolved_orders",
        )

    return StartupGuardDecision(operational_state="normal", degraded_reason=None)


def infer_buy_fill_from_balance(
    *,
    order_quantity: int,
    filled_quantity: int,
    position_quantity_at_submit: int | None,
    broker_position_quantity: int | None,
) -> BuyFillInferenceDecision:
    """Infer buy-side fill progress from a broker balance snapshot."""
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


def evaluate_pending_order_recovery(
    *,
    order_quantity: int,
    filled_quantity: int,
    reconciled_filled_quantity: int,
) -> PendingOrderRecoveryDecision:
    """Normalize a broker-reported filled quantity into a pending-order state."""
    normalized_order_quantity = max(order_quantity, 0)
    current_filled = min(max(filled_quantity, 0), normalized_order_quantity)
    reconciled_filled = min(max(reconciled_filled_quantity, 0), normalized_order_quantity)
    target_filled_quantity = max(current_filled, reconciled_filled)
    fill_delta = max(0, target_filled_quantity - current_filled)

    if normalized_order_quantity > 0 and target_filled_quantity >= normalized_order_quantity:
        status: PendingOrderRecoveryStatus = "filled"
    elif target_filled_quantity > 0:
        status = "partial_fill"
    else:
        status = "unresolved"

    return PendingOrderRecoveryDecision(
        target_filled_quantity=target_filled_quantity,
        fill_delta=fill_delta,
        status=status,
    )


def evaluate_submission_recovery(
    *,
    matched_broker_order_id: str | None,
    final_attempt: bool,
) -> SubmissionRecoveryDecision:
    """Return how a submission-unknown order should be tracked after broker inquiry."""
    normalized_id = (
        str(matched_broker_order_id).strip()
        if matched_broker_order_id not in (None, "")
        else None
    )
    if normalized_id is not None:
        return SubmissionRecoveryDecision(
            bind_broker_order=True,
            matched_broker_order_id=normalized_id,
            keep_pending=True,
            downgrade_to_reduce_only=True,
            operator_action_required=False,
        )

    return SubmissionRecoveryDecision(
        bind_broker_order=False,
        matched_broker_order_id=None,
        keep_pending=True,
        downgrade_to_reduce_only=True,
        operator_action_required=final_attempt,
    )


def build_execution_dedupe_key(
    *,
    broker_order_id: str | None,
    side: str | None,
    cumulative_quantity: Any,
    remaining_quantity: Any,
    event_status: str | None,
    executed_quantity: Any,
    executed_price: Any,
) -> str | None:
    """Build a deterministic dedupe key using only broker-derived fields."""
    normalized_broker_order_id = (
        str(broker_order_id).strip() if broker_order_id not in (None, "") else ""
    )
    normalized_side = str(side).strip() if side not in (None, "") else ""
    normalized_status = str(event_status).strip() if event_status not in (None, "") else ""
    normalized_cumulative = (
        str(cumulative_quantity).strip() if cumulative_quantity not in (None, "") else ""
    )
    normalized_remaining = (
        str(remaining_quantity).strip() if remaining_quantity not in (None, "") else ""
    )
    normalized_quantity = (
        str(executed_quantity).strip() if executed_quantity not in (None, "") else ""
    )
    normalized_price = str(executed_price).strip() if executed_price not in (None, "") else ""

    if not normalized_broker_order_id:
        return None

    if normalized_cumulative:
        return "|".join(
            [
                normalized_broker_order_id,
                normalized_side,
                normalized_cumulative,
                normalized_remaining,
                normalized_status,
            ]
        )

    if normalized_quantity and normalized_price:
        return "|".join(
            [
                normalized_broker_order_id,
                normalized_side,
                normalized_quantity,
                normalized_price,
                normalized_status,
            ]
        )

    return None


def evaluate_execution_integrity(
    *,
    dedupe_key: str | None,
    matched_pending_order: bool,
    apply_error: bool = False,
) -> ExecutionIntegrityDecision:
    """Decide whether an execution event is safe to apply to local state."""
    if apply_error:
        return ExecutionIntegrityDecision(
            apply_event=False,
            dedupe_key=dedupe_key,
            downgrade_to_reduce_only=True,
            operator_action_required=True,
            reason="execution_apply_failed",
        )

    if not dedupe_key:
        return ExecutionIntegrityDecision(
            apply_event=False,
            dedupe_key=None,
            downgrade_to_reduce_only=True,
            operator_action_required=True,
            reason="execution_key_missing",
        )

    if not matched_pending_order:
        return ExecutionIntegrityDecision(
            apply_event=False,
            dedupe_key=dedupe_key,
            downgrade_to_reduce_only=True,
            operator_action_required=True,
            reason="unmatched_execution_notice",
        )

    return ExecutionIntegrityDecision(
        apply_event=True,
        dedupe_key=dedupe_key,
        downgrade_to_reduce_only=False,
        operator_action_required=False,
        reason=None,
    )


def evaluate_runtime_fault(*, fault: str) -> RuntimeFaultDecision:
    """Map runtime faults into log-only, reduce-only, or blocked actions."""
    normalized_fault = fault.strip().lower()
    if normalized_fault in {
        "submission_unknown",
        "submission_result_unknown",
        "unmatched_execution",
        "unmatched_execution_notice",
        "execution_apply_failed",
        "execution_key_missing",
        "open_order_truth_unavailable",
        "runtime_reconciliation_drift",
        "operator_action_required",
    }:
        degraded_reason = None
        if normalized_fault in {"submission_unknown", "submission_result_unknown"}:
            degraded_reason = "submission_result_unknown"
        elif normalized_fault == "runtime_reconciliation_drift":
            degraded_reason = "runtime_reconciliation_drift"

        return RuntimeFaultDecision(
            action="reduce_only",
            degraded_reason=degraded_reason,
            operator_action_required=True,
        )

    if normalized_fault in {
        "startup_auth_failed",
        "startup_broker_truth_unavailable",
        "startup_state_and_truth_unavailable",
    }:
        return RuntimeFaultDecision(
            action="blocked",
            degraded_reason="startup_recovery_failed",
            operator_action_required=True,
        )

    return RuntimeFaultDecision(
        action="log_only",
        degraded_reason=None,
        operator_action_required=False,
    )


def evaluate_session_handoff(
    *,
    has_positions: bool,
    operator_action_required: bool,
) -> SessionHandoffDecision:
    """Return how shutdown should be presented to the operator."""
    if has_positions:
        return SessionHandoffDecision(
            should_stop=True,
            require_operator_handoff=True,
            summary="open_positions_remain",
        )
    if operator_action_required:
        return SessionHandoffDecision(
            should_stop=True,
            require_operator_handoff=True,
            summary="operator_action_required",
        )
    return SessionHandoffDecision(
        should_stop=True,
        require_operator_handoff=False,
        summary=None,
    )


def evaluate_runtime_guard(
    *,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    has_discrepancies: bool,
) -> RuntimeGuardDecision:
    """Return how runtime reconciliation drift should change operability."""
    if not has_discrepancies or is_paper_trading or allow_unsafe_trading:
        return RuntimeGuardDecision(operational_state="normal", degraded_reason=None)

    return RuntimeGuardDecision(
        operational_state="degraded_reduce_only",
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
            operational_state="normal",
            degraded_reason=None,
        )

    should_reduce_only = (
        websocket_execution_notice_enabled and not is_paper_trading and not allow_unsafe_trading
    )
    return WebSocketGuardDecision(
        start_polling_fallback=websocket_monitoring_enabled,
        operational_state="degraded_reduce_only" if should_reduce_only else "normal",
        degraded_reason="execution_stream_unavailable" if should_reduce_only else None,
    )


def evaluate_realtime_startup(
    *,
    is_paper_trading: bool,
    allow_unsafe_trading: bool,
    websocket_monitoring_enabled: bool,
    websocket_execution_notice_enabled: bool,
    quote_subscription_succeeded: bool,
    execution_subscription_succeeded: bool,
) -> RealtimeStartupDecision:
    """Evaluate startup-time websocket readiness."""
    should_reduce_only = (
        websocket_execution_notice_enabled
        and not execution_subscription_succeeded
        and not is_paper_trading
        and not allow_unsafe_trading
    )
    return RealtimeStartupDecision(
        quote_stream_active=websocket_monitoring_enabled and quote_subscription_succeeded,
        start_polling_fallback=websocket_monitoring_enabled and not quote_subscription_succeeded,
        operational_state="degraded_reduce_only" if should_reduce_only else "normal",
        degraded_reason="execution_stream_unavailable" if should_reduce_only else None,
    )


def evaluate_order_permission(
    *,
    operational_state: OperationalState,
    side: OrderSide,
    position_quantity: int,
    requested_quantity: int,
    has_pending_same_side: bool,
) -> OrderPermissionDecision:
    """Evaluate whether the engine should accept an order request."""
    normalized_position_quantity = max(position_quantity, 0)
    normalized_requested_quantity = max(requested_quantity, 0)

    if side == "buy":
        if operational_state != "normal":
            return OrderPermissionDecision(allowed=False, reject_code="trading_disabled")
        if has_pending_same_side:
            return OrderPermissionDecision(allowed=False, reject_code="pending_same_side")
        return OrderPermissionDecision(allowed=True, reduce_only=False)

    if normalized_position_quantity <= 0:
        return OrderPermissionDecision(allowed=False, reject_code="no_open_position")
    if normalized_requested_quantity <= 0:
        return OrderPermissionDecision(allowed=False, reject_code="invalid_quantity")
    if normalized_requested_quantity > normalized_position_quantity:
        return OrderPermissionDecision(allowed=False, reject_code="exceeds_position")
    if has_pending_same_side:
        return OrderPermissionDecision(allowed=False, reject_code="pending_same_side")
    if operational_state == "blocked":
        return OrderPermissionDecision(allowed=False, reject_code="trading_disabled")

    return OrderPermissionDecision(allowed=True, reduce_only=True)


def evaluate_engine_operability(
    *,
    running: bool,
    rate_limiter_available: int,
    reconciliation_fresh: bool,
    has_positions: bool,
    price_monitor_running: bool,
    market_data_fresh: bool,
    websocket_monitoring_enabled: bool,
    websocket_connected: bool,
    operational_state: OperationalState,
) -> EngineOperabilityDecision:
    """Split health, readiness, and session-liveness into explicit outputs."""
    monitoring_available = price_monitor_running or (
        websocket_monitoring_enabled and websocket_connected
    )
    has_runtime_health = (
        running
        and rate_limiter_available > 0
        and reconciliation_fresh
        and (
            not has_positions
            or (monitoring_available and market_data_fresh)
        )
    )
    is_ready_for_new_orders = has_runtime_health and operational_state == "normal"
    should_keep_session_running = has_runtime_health and (
        operational_state == "normal"
        or (operational_state == "degraded_reduce_only" and has_positions)
    )
    return EngineOperabilityDecision(
        is_healthy=has_runtime_health,
        is_ready_for_new_orders=is_ready_for_new_orders,
        should_keep_session_running=should_keep_session_running,
        operational_state=operational_state,
    )
