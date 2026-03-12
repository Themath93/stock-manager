from stock_manager.trading.guardrails import (
    evaluate_runtime_guard,
    evaluate_startup_guard,
    evaluate_websocket_guard,
    infer_buy_fill_from_balance,
    resolve_auto_exit_order,
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
    assert decision.degraded_reason is None


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
    assert decision.degraded_reason is None
