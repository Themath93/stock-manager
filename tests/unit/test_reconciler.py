from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from stock_manager.monitoring.reconciler import PositionReconciler, ReconciliationResult
from stock_manager.trading.models import Position, PositionStatus


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


def test_reconcile_now_updates_last_result_and_calls_on_cycle_complete() -> None:
    completed: list[ReconciliationResult] = []
    reconciler = PositionReconciler(
        position_manager=SimpleNamespace(get_all_positions=lambda: {}),
        inquire_balance_func=lambda: {"rt_cd": "0", "output1": {}},
        on_cycle_complete=completed.append,
    )

    result = reconciler.reconcile_now()

    assert reconciler.last_result is result
    assert completed == [result]
    assert result.broker_positions == {}


def test_reconciler_requires_client_and_account_number_without_injected_func() -> None:
    reconciler = PositionReconciler(position_manager=SimpleNamespace(get_all_positions=lambda: {}))

    result = reconciler.reconcile_now()

    assert result.is_clean is False
    assert "client and account_number are required" in result.discrepancies[0]


def test_reconciler_uses_client_request_path_when_no_injected_balance_func(monkeypatch) -> None:
    monkeypatch.setattr(
        "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.inquire_balance",
        lambda **_: {
            "url_path": "/uapi/domestic-stock/v1/trading/inquire-balance",
            "params": {"CANO": "12345678"},
            "tr_id": "TTTC8434R",
        },
    )

    calls: list[dict[str, object]] = []

    class FakeClient:
        def make_request(self, **kwargs):
            calls.append(kwargs)
            return {"rt_cd": "0", "output1": []}

    reconciler = PositionReconciler(
        client=FakeClient(),
        position_manager=SimpleNamespace(get_all_positions=lambda: {}),
        account_number="12345678",
        account_product_code="01",
        is_paper_trading=False,
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is True
    assert calls == [
        {
            "method": "GET",
            "path": "/uapi/domestic-stock/v1/trading/inquire-balance",
            "params": {"CANO": "12345678"},
            "headers": {"tr_id": "TTTC8434R"},
        }
    ]


def test_reconciler_apply_state_closes_opens_and_updates_positions() -> None:
    class FakePositionManager:
        def __init__(self) -> None:
            self.positions = {
                "005930": Position(
                    symbol="005930",
                    quantity=1,
                    entry_price=Decimal("0"),
                    status=PositionStatus.STALE,
                ),
                "035720": Position(
                    symbol="035720",
                    quantity=2,
                    entry_price=Decimal("1000"),
                    status=PositionStatus.OPEN,
                ),
            }
            self.closed: list[str] = []
            self.opened: list[Position] = []

        def get_all_positions(self):
            return self.positions

        def get_position(self, symbol: str):
            return self.positions.get(symbol)

        def open_position(self, position: Position) -> None:
            self.positions[position.symbol] = position
            self.opened.append(position)

        def close_position(self, symbol: str) -> None:
            self.closed.append(symbol)
            self.positions.pop(symbol, None)

    position_manager = FakePositionManager()
    reconciler = PositionReconciler(
        position_manager=position_manager,
        apply_state=True,
        inquire_balance_func=lambda: {
            "rt_cd": "0",
            "output1": [
                {
                    "pdno": "005930",
                    "hldg_qty": "3",
                    "pchs_avg_pric": "70000",
                    "prpr": "71000",
                },
                {
                    "pdno": "000660",
                    "hldg_qty": "2",
                    "pchs_avg_pric": "100000",
                    "prpr": "102000",
                },
            ],
        },
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is False
    assert position_manager.closed == ["035720"]
    assert [position.symbol for position in position_manager.opened] == ["000660"]

    updated = position_manager.positions["005930"]
    assert updated.quantity == 3
    assert updated.entry_price == Decimal("70000")
    assert updated.current_price == Decimal("71000")
    assert updated.unrealized_pnl == Decimal("3000")
    assert updated.status == PositionStatus.OPEN_RECONCILED

    opened = position_manager.positions["000660"]
    assert opened.status == PositionStatus.OPEN_RECONCILED
    assert opened.entry_price == Decimal("100000")


def test_reconciler_apply_state_noops_when_manager_missing_methods() -> None:
    position_manager = SimpleNamespace(get_all_positions=lambda: {"005930": {"quantity": 1}})
    reconciler = PositionReconciler(
        position_manager=position_manager,
        apply_state=True,
        inquire_balance_func=lambda: {"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "1"}]},
    )

    result = reconciler.reconcile_now()

    assert result.is_clean is True


def test_reconciler_start_stop_and_second_start_guard(monkeypatch) -> None:
    created: dict[str, object] = {}

    class DummyThread:
        def __init__(self, **kwargs) -> None:
            created.update(kwargs)
            self.started = False
            self.joined_with: float | None = None

        def start(self) -> None:
            self.started = True

        def join(self, timeout: float) -> None:
            self.joined_with = timeout

        def is_alive(self) -> bool:
            return self.started

    monkeypatch.setattr("stock_manager.monitoring.reconciler.threading.Thread", DummyThread)

    reconciler = PositionReconciler(
        position_manager=SimpleNamespace(get_all_positions=lambda: {}),
        inquire_balance_func=lambda: {"rt_cd": "0", "output1": []},
    )
    reconciler.start()
    started_thread = reconciler._thread
    reconciler.start()
    reconciler.stop(timeout=1.5)

    assert isinstance(started_thread, DummyThread)
    assert started_thread.started is True
    assert created["name"] == "PositionReconciler"
    assert started_thread.joined_with == 1.5
    assert reconciler._thread is None


def test_reconcile_loop_invokes_on_discrepancy_once(monkeypatch) -> None:
    completed: list[ReconciliationResult] = []
    discrepancies: list[ReconciliationResult] = []
    result = ReconciliationResult(is_clean=False, discrepancies=["mismatch"])
    reconciler = PositionReconciler(
        on_cycle_complete=completed.append,
        on_discrepancy=discrepancies.append,
    )

    monkeypatch.setattr(reconciler, "_do_reconcile", lambda: result)
    states = iter([False, True])
    monkeypatch.setattr(reconciler._stop_event, "is_set", lambda: next(states))
    monkeypatch.setattr(reconciler._stop_event, "wait", lambda interval: True)

    reconciler._reconcile_loop()

    assert reconciler.last_result is result
    assert completed == [result]
    assert discrepancies == [result]


def test_reconciler_helper_parsing_covers_invalid_values() -> None:
    reconciler = PositionReconciler()

    assert reconciler._extract_symbol(None) == ""
    assert reconciler._extract_symbol({"PDNO": "005930"}) == "005930"
    assert reconciler._extract_symbol({"foo": "bar"}) == ""
    assert reconciler._to_decimal("1,234.5") == Decimal("1234.5")
    assert reconciler._to_decimal("-") is None
    assert reconciler._to_decimal("bad") is None

    broker_positions = reconciler._build_broker_positions(
        [
            {"pdno": "005930", "hldg_qty": "bad", "pchs_avg_pric": "70000", "prpr": "71000"},
            {"foo": "bar"},
        ]
    )
    assert broker_positions["005930"].quantity == 0
    assert broker_positions["005930"].entry_price == Decimal("70000")
    assert broker_positions["005930"].current_price == Decimal("71000")

    local_positions = reconciler._build_local_positions(
        {"005930": {"quantity": 2, "entry_price": "70000", "current_price": "71000"}}
    )
    assert local_positions["005930"].entry_price == Decimal("70000")
    assert local_positions["005930"].current_price == Decimal("71000")
