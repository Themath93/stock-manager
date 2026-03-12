from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from stock_manager.adapters.broker.kis.websocket_client import KISWebSocketClient
from stock_manager.engine import TradingEngine
from stock_manager.monitoring.reconciler import BrokerPositionSnapshot
from stock_manager.persistence.recovery import RecoveryReport, RecoveryResult
from stock_manager.trading.executor import OrderResult
from stock_manager.trading.models import OrderStatus, Position, PositionStatus, TradingConfig

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "kis_live" / "domestic"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _make_engine(tmp_path) -> TradingEngine:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg_cd": "0",
        "output": {"stck_prpr": "70000"},
        "output1": [],
        "output2": [{"dnca_tot_amt": "10000000"}],
    }
    engine = TradingEngine(
        client=client,
        config=TradingConfig(polling_interval_sec=9999.0, market_hours_enabled=False),
        account_number="12345678",
        account_product_code="01",
        state_path=tmp_path / "state.json",
        is_paper_trading=True,
    )
    with (
        patch("stock_manager.engine.load_state", return_value=None),
        patch(
            "stock_manager.engine.startup_reconciliation",
            return_value=RecoveryReport(result=RecoveryResult.CLEAN),
        ),
        patch.object(engine._price_monitor, "start"),
        patch.object(engine._price_monitor, "stop"),
        patch.object(engine._reconciler, "start"),
        patch.object(engine._reconciler, "stop"),
    ):
        engine.start()
    return engine


def test_execution_notice_fixture_parses_buy_fill() -> None:
    client = KISWebSocketClient(websocket_url="ws://test")
    received = []
    client.register_execution_callback(received.append)

    client._on_message(None, json.dumps(_load_fixture("execution_notice_buy.json")))

    assert len(received) == 1
    event = received[0]
    assert event.symbol == "005930"
    assert event.broker_order_id == "71012345"
    assert event.side == "buy"
    assert event.executed_price == Decimal("70100")
    assert event.executed_quantity == Decimal("3")
    assert event.cumulative_quantity == Decimal("3")
    assert event.remaining_quantity == Decimal("0")
    assert event.event_status == "filled"


def test_execution_notice_fixture_parses_partial_sell() -> None:
    client = KISWebSocketClient(websocket_url="ws://test")
    received = []
    client.register_execution_callback(received.append)

    client._on_message(None, json.dumps(_load_fixture("execution_notice_partial_sell.json")))

    assert len(received) == 1
    event = received[0]
    assert event.side == "sell"
    assert event.executed_price == Decimal("71900")
    assert event.executed_quantity == Decimal("2")
    assert event.remaining_quantity == Decimal("8")
    assert event.event_status == "partial_fill"


def test_balance_fixture_reconciles_pending_buy_without_execution(tmp_path) -> None:
    engine = _make_engine(tmp_path)
    try:
        engine._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="71012345")
        )
        engine.buy("005930", 3, 70100)

        engine._safe_inquire_daily_orders = MagicMock(
            return_value=_load_fixture("daily_order_buy_filled.json")
        )
        balance_fixture = _load_fixture("balance_after_buy.json")
        result = SimpleNamespace(
            is_clean=True,
            discrepancies=[],
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            broker_positions={
                "005930": BrokerPositionSnapshot(
                    symbol="005930",
                    quantity=3,
                    entry_price=Decimal("70100"),
                    current_price=Decimal("70100"),
                )
            },
            local_positions={},
        )

        engine._on_reconciliation_cycle(result)

        position = engine.get_position("005930")
        assert position is not None
        assert position.quantity == 3
        assert position.entry_price == Decimal("70100")
        assert engine._state.pending_orders == {}
        assert balance_fixture["output1"][0]["pdno"] == "005930"
    finally:
        engine.stop()


def test_balance_fixture_does_not_false_positive_pending_buy_for_existing_position(tmp_path) -> None:
    engine = _make_engine(tmp_path)
    try:
        engine._position_manager.open_position(
            Position(
                symbol="005930",
                quantity=10,
                entry_price=Decimal("70000"),
                current_price=Decimal("70000"),
                status=PositionStatus.OPEN,
            )
        )
        engine._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="71012345")
        )
        buy_result = engine.buy("005930", 10, 70100)

        engine._safe_inquire_daily_orders = MagicMock(return_value={"output1": []})
        result = SimpleNamespace(
            is_clean=True,
            discrepancies=[],
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            broker_positions={
                "005930": BrokerPositionSnapshot(
                    symbol="005930",
                    quantity=10,
                    entry_price=Decimal("70000"),
                    current_price=Decimal("70000"),
                )
            },
            local_positions={
                "005930": BrokerPositionSnapshot(
                    symbol="005930",
                    quantity=10,
                    entry_price=Decimal("70000"),
                    current_price=Decimal("70000"),
                )
            },
        )

        engine._on_reconciliation_cycle(result)

        order = engine._state.pending_orders[buy_result.order_id]
        assert order.status == OrderStatus.SUBMITTED
        assert order.filled_quantity == 0
        assert order.unresolved_reason == "buy_fill_requires_quantity_increase"
    finally:
        engine.stop()


def test_ambiguous_daily_order_fixture_keeps_sell_pending_unresolved(tmp_path) -> None:
    engine = _make_engine(tmp_path)
    try:
        engine._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="B-1")
        )
        engine._executor.sell = MagicMock(
            return_value=OrderResult(success=True, order_id="SELL-1", broker_order_id=None)
        )
        engine.buy("005930", 3, 70100)
        engine._apply_execution_event(
            SimpleNamespace(
                symbol="005930",
                broker_order_id="B-1",
                order_id="B-1",
                side="buy",
                executed_price=Decimal("70100"),
                price=Decimal("70100"),
                executed_quantity=Decimal("3"),
                quantity=Decimal("3"),
                cumulative_quantity=Decimal("3"),
                remaining_quantity=Decimal("0"),
                event_status="filled",
                raw_payload={"pdno": "005930", "odno": "B-1"},
            )
        )
        sell_result = engine.sell("005930", 2, price=None, origin="manual", exit_reason="MANUAL")

        engine._safe_inquire_daily_orders = MagicMock(
            return_value=_load_fixture("ambiguous_daily_orders.json")
        )
        result = SimpleNamespace(
            is_clean=False,
            discrepancies=["ambiguous"],
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            broker_positions={
                "005930": BrokerPositionSnapshot(
                    symbol="005930",
                    quantity=3,
                    entry_price=Decimal("70100"),
                    current_price=Decimal("70100"),
                )
            },
            local_positions={
                "005930": BrokerPositionSnapshot(
                    symbol="005930",
                    quantity=3,
                    entry_price=Decimal("70100"),
                    current_price=Decimal("70100"),
                )
            },
        )

        engine._on_reconciliation_cycle(result)

        order = engine._state.pending_orders[sell_result.order_id]
        assert order.status == OrderStatus.SUBMITTED
        assert order.unresolved_reason == "ambiguous_daily_order_match"
    finally:
        engine.stop()
