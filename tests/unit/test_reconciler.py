from __future__ import annotations

from types import SimpleNamespace

from stock_manager.monitoring.reconciler import PositionReconciler


def test_reconciler_clean_when_positions_match() -> None:
    position_manager = SimpleNamespace(
        get_all_positions=lambda: {"005930": SimpleNamespace(quantity=10)}
    )

    reconciler = PositionReconciler(
        position_manager=position_manager,
        inquire_balance_func=lambda: {
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "10"}],
        },
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is True
    assert result.discrepancies == []
    assert result.quantity_mismatches == {}


def test_reconciler_supports_uppercase_response_keys() -> None:
    position_manager = SimpleNamespace(
        get_all_positions=lambda: {"005930": SimpleNamespace(quantity=10)}
    )

    reconciler = PositionReconciler(
        position_manager=position_manager,
        inquire_balance_func=lambda: {
            "rt_cd": "0",
            "output1": [{"PDNO": "005930", "HLDG_QTY": "12"}],
        },
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is False
    assert result.quantity_mismatches["005930"] == (10, 12)


def test_reconciler_returns_discrepancy_on_broker_error() -> None:
    position_manager = SimpleNamespace(get_all_positions=lambda: {})

    reconciler = PositionReconciler(
        position_manager=position_manager,
        inquire_balance_func=lambda: {"rt_cd": "1", "msg1": "temporary failure"},
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is False
    assert "Failed to query broker" in result.discrepancies[0]


def test_reconciler_handles_local_position_dict_shape() -> None:
    position_manager = SimpleNamespace(
        get_all_positions=lambda: {"005930": {"quantity": 7}}
    )

    reconciler = PositionReconciler(
        position_manager=position_manager,
        inquire_balance_func=lambda: {
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "7"}],
        },
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is True


def test_reconciler_calls_inquire_balance_func_without_args() -> None:
    calls = {"count": 0}

    def _inquire_balance() -> dict:
        calls["count"] += 1
        return {"rt_cd": "0", "output1": []}

    position_manager = SimpleNamespace(get_all_positions=lambda: {})
    reconciler = PositionReconciler(
        position_manager=position_manager,
        inquire_balance_func=_inquire_balance,
    )

    reconciler.reconcile_now()

    assert calls["count"] == 1
