from stock_manager.trading.guardrails import (
    evaluate_engine_operability,
    evaluate_order_permission,
    evaluate_pending_order_recovery,
    evaluate_realtime_startup,
    evaluate_runtime_guard,
    evaluate_startup_guard,
    evaluate_websocket_guard,
    infer_buy_fill_from_balance,
    resolve_auto_exit_order,
    resolve_operational_state,
)


def test_resolve_auto_exit_order_uses_market_order_for_stop_loss() -> None:
    decision = resolve_auto_exit_order(trigger_type="stop_loss", current_price=70000)

    assert decision.order_type == "market"
    assert decision.price is None


def test_resolve_auto_exit_order_uses_limit_order_for_take_profit() -> None:
    decision = resolve_auto_exit_order(trigger_type="take_profit", current_price=70000)

    assert decision.order_type == "limit"
    assert decision.price == 70000


def test_evaluate_startup_guard_blocks_live_failed_recovery() -> None:
    decision = evaluate_startup_guard(
        is_paper_trading=False,
        allow_unsafe_trading=False,
        recovery_mode="block",
        recovery_result="failed",
        unresolved_order_count=0,
    )

    assert decision.should_block_trading is True
    assert decision.operational_state == "blocked"
    assert decision.degraded_reason == "startup_recovery_failed"


def test_evaluate_startup_guard_blocks_live_unresolved_orders() -> None:
    decision = evaluate_startup_guard(
        is_paper_trading=False,
        allow_unsafe_trading=False,
        recovery_mode="block",
        recovery_result="reconciled",
        unresolved_order_count=1,
    )

    assert decision.should_block_trading is True
    assert decision.operational_state == "degraded_reduce_only"
    assert decision.degraded_reason == "startup_recovery_unresolved_orders"


def test_evaluate_startup_guard_keeps_mock_sessions_running() -> None:
    decision = evaluate_startup_guard(
        is_paper_trading=True,
        allow_unsafe_trading=False,
        recovery_mode="block",
        recovery_result="failed",
        unresolved_order_count=2,
    )

    assert decision.should_block_trading is False
    assert decision.operational_state == "normal"
    assert decision.degraded_reason is None


def test_resolve_operational_state_maps_known_reasons() -> None:
    assert resolve_operational_state(degraded_reason=None) == "normal"
    assert resolve_operational_state(degraded_reason="startup_recovery_failed") == "blocked"
    assert (
        resolve_operational_state(degraded_reason="execution_stream_unavailable")
        == "degraded_reduce_only"
    )


def test_infer_buy_fill_from_balance_uses_baseline_delta() -> None:
    decision = infer_buy_fill_from_balance(
        order_quantity=10,
        filled_quantity=0,
        position_quantity_at_submit=10,
        broker_position_quantity=15,
    )

    assert decision.filled_delta == 5
    assert decision.unresolved_reason is None


def test_infer_buy_fill_from_balance_requires_quantity_increase() -> None:
    decision = infer_buy_fill_from_balance(
        order_quantity=10,
        filled_quantity=0,
        position_quantity_at_submit=10,
        broker_position_quantity=10,
    )

    assert decision.filled_delta == 0
    assert decision.unresolved_reason == "buy_fill_requires_quantity_increase"


def test_infer_buy_fill_from_balance_requires_baseline() -> None:
    decision = infer_buy_fill_from_balance(
        order_quantity=10,
        filled_quantity=0,
        position_quantity_at_submit=None,
        broker_position_quantity=15,
    )

    assert decision.filled_delta == 0
    assert decision.unresolved_reason == "buy_fill_baseline_missing"


def test_evaluate_runtime_guard_blocks_live_discrepancy() -> None:
    decision = evaluate_runtime_guard(
        is_paper_trading=False,
        allow_unsafe_trading=False,
        has_discrepancies=True,
    )

    assert decision.should_block_trading is True
    assert decision.operational_state == "degraded_reduce_only"
    assert decision.degraded_reason == "runtime_reconciliation_drift"


def test_evaluate_websocket_guard_falls_back_and_blocks_live_execution_stream() -> None:
    decision = evaluate_websocket_guard(
        lifecycle_status="reconnect_exhausted",
        is_paper_trading=False,
        allow_unsafe_trading=False,
        websocket_monitoring_enabled=True,
        websocket_execution_notice_enabled=True,
    )

    assert decision.start_polling_fallback is True
    assert decision.should_block_trading is True
    assert decision.operational_state == "degraded_reduce_only"
    assert decision.degraded_reason == "execution_stream_unavailable"


def test_evaluate_websocket_guard_warns_only_in_mock() -> None:
    decision = evaluate_websocket_guard(
        lifecycle_status="reconnect_exhausted",
        is_paper_trading=True,
        allow_unsafe_trading=False,
        websocket_monitoring_enabled=True,
        websocket_execution_notice_enabled=True,
    )

    assert decision.start_polling_fallback is True
    assert decision.should_block_trading is False
    assert decision.operational_state == "normal"
    assert decision.degraded_reason is None


def test_evaluate_pending_order_recovery_marks_partial_fill() -> None:
    decision = evaluate_pending_order_recovery(
        order_quantity=10,
        filled_quantity=0,
        reconciled_filled_quantity=4,
    )

    assert decision.status == "partial_fill"
    assert decision.fill_delta == 4
    assert decision.target_filled_quantity == 4
    assert decision.should_keep_pending is True


def test_evaluate_pending_order_recovery_marks_full_fill() -> None:
    decision = evaluate_pending_order_recovery(
        order_quantity=10,
        filled_quantity=3,
        reconciled_filled_quantity=10,
    )

    assert decision.status == "filled"
    assert decision.fill_delta == 7
    assert decision.target_filled_quantity == 10
    assert decision.should_keep_pending is False


def test_evaluate_order_permission_allows_reduce_only_sell_in_degraded_mode() -> None:
    decision = evaluate_order_permission(
        operational_state="degraded_reduce_only",
        side="sell",
        position_quantity=10,
        requested_quantity=10,
        has_pending_same_side=False,
    )

    assert decision.allowed is True
    assert decision.reduce_only is True


def test_evaluate_order_permission_blocks_buy_in_degraded_mode() -> None:
    decision = evaluate_order_permission(
        operational_state="degraded_reduce_only",
        side="buy",
        position_quantity=0,
        requested_quantity=1,
        has_pending_same_side=False,
    )

    assert decision.allowed is False
    assert decision.reject_code == "trading_disabled"


def test_evaluate_realtime_startup_blocks_live_execution_stream_failure() -> None:
    decision = evaluate_realtime_startup(
        is_paper_trading=False,
        allow_unsafe_trading=False,
        websocket_monitoring_enabled=True,
        websocket_execution_notice_enabled=True,
        quote_subscription_succeeded=False,
        execution_subscription_succeeded=False,
    )

    assert decision.quote_stream_active is False
    assert decision.start_polling_fallback is True
    assert decision.operational_state == "degraded_reduce_only"
    assert decision.degraded_reason == "execution_stream_unavailable"


def test_evaluate_engine_operability_splits_health_and_session_liveness() -> None:
    decision = evaluate_engine_operability(
        running=True,
        rate_limiter_available=1,
        reconciliation_fresh=True,
        has_positions=False,
        price_monitor_running=False,
        market_data_fresh=True,
        websocket_monitoring_enabled=False,
        websocket_connected=False,
        operational_state="degraded_reduce_only",
    )

    assert decision.is_healthy is True
    assert decision.is_ready_for_new_orders is False
    assert decision.should_keep_session_running is False
    assert decision.operational_state == "degraded_reduce_only"


def test_evaluate_engine_operability_keeps_degraded_session_running_with_positions() -> None:
    decision = evaluate_engine_operability(
        running=True,
        rate_limiter_available=1,
        reconciliation_fresh=True,
        has_positions=True,
        price_monitor_running=True,
        market_data_fresh=True,
        websocket_monitoring_enabled=False,
        websocket_connected=False,
        operational_state="degraded_reduce_only",
    )

    assert decision.is_healthy is True
    assert decision.is_ready_for_new_orders is False
    assert decision.should_keep_session_running is True
