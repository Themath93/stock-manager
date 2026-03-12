"""Integration tests for the broker-confirmed engine state machine.

These tests intentionally avoid optimistic executor side-effects.
Orders are only submitted through the executor mock, while fills arrive
through execution events or reconciliation snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stock_manager.engine import TradingEngine
from stock_manager.monitoring.reconciler import BrokerPositionSnapshot
from stock_manager.persistence.recovery import RecoveryReport, RecoveryResult
from stock_manager.trading.executor import OrderResult
from stock_manager.trading.models import PositionStatus, TradingConfig

pytestmark = pytest.mark.integration


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg_cd": "0",
        "output": {"stck_prpr": "70000"},
        "output1": [],
        "output2": [{"dnca_tot_amt": "10000000", "tot_evlu_amt": "10000000"}],
    }
    return client


def _config() -> TradingConfig:
    return TradingConfig(
        polling_interval_sec=9999.0,
        rate_limit_per_sec=100,
        market_hours_enabled=False,
        default_stop_loss_pct=Decimal("0.05"),
        default_take_profit_pct=Decimal("0.10"),
    )


def _make_engine(tmp_path) -> TradingEngine:
    return TradingEngine(
        client=_mock_client(),
        config=_config(),
        account_number="12345678",
        account_product_code="01",
        state_path=tmp_path / "sim_state.json",
        is_paper_trading=True,
    )


def _start(engine: TradingEngine) -> None:
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


def _buy_event(*, broker_order_id: str, quantity: int, price: int) -> SimpleNamespace:
    return SimpleNamespace(
        symbol="005930",
        broker_order_id=broker_order_id,
        order_id=broker_order_id,
        side="buy",
        executed_price=Decimal(str(price)),
        price=Decimal(str(price)),
        executed_quantity=Decimal(str(quantity)),
        quantity=Decimal(str(quantity)),
        cumulative_quantity=Decimal(str(quantity)),
        remaining_quantity=Decimal("0"),
        event_status="filled",
        timestamp=datetime.now(timezone.utc),
        tr_id="H0STCNI9",
        raw_payload={"pdno": "005930", "odno": broker_order_id},
    )


def _sell_event(*, broker_order_id: str, quantity: int, price: int) -> SimpleNamespace:
    return SimpleNamespace(
        symbol="005930",
        broker_order_id=broker_order_id,
        order_id=broker_order_id,
        side="sell",
        executed_price=Decimal(str(price)),
        price=Decimal(str(price)),
        executed_quantity=Decimal(str(quantity)),
        quantity=Decimal(str(quantity)),
        cumulative_quantity=Decimal(str(quantity)),
        remaining_quantity=Decimal("0"),
        event_status="filled",
        timestamp=datetime.now(timezone.utc),
        tr_id="H0STCNI9",
        raw_payload={"pdno": "005930", "odno": broker_order_id},
    )


@pytest.fixture
def engine(tmp_path):
    eng = _make_engine(tmp_path)
    _start(eng)
    yield eng
    if eng._running:
        eng.stop()


def test_buy_submit_then_execution_opens_position_and_arms_exit_targets(engine: TradingEngine) -> None:
    engine._executor.buy = MagicMock(
        return_value=OrderResult(
            success=True,
            order_id="BUY-1",
            broker_order_id="B-1",
        )
    )

    result = engine.buy("005930", 10, 70000, stop_loss=66500, take_profit=77000, origin="strategy")

    assert result.success is True
    assert engine.get_position("005930") is None
    assert "BUY-1" in engine._state.pending_orders

    engine._apply_execution_event(_buy_event(broker_order_id="B-1", quantity=10, price=70000))

    position = engine.get_position("005930")
    assert position is not None
    assert position.quantity == 10
    assert position.entry_price == Decimal("70000")
    assert position.stop_loss == Decimal("66500")
    assert position.take_profit == Decimal("77000")
    assert position.status == PositionStatus.OPEN
    assert engine._state.pending_orders == {}


def test_sell_submit_then_execution_closes_position_and_clears_pending(engine: TradingEngine) -> None:
    engine._executor.buy = MagicMock(
        return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="B-1")
    )
    engine._executor.sell = MagicMock(
        return_value=OrderResult(success=True, order_id="SELL-1", broker_order_id="S-1")
    )

    engine.buy("005930", 10, 70000)
    engine._apply_execution_event(_buy_event(broker_order_id="B-1", quantity=10, price=70000))

    sell_result = engine.sell("005930", 10, price=None, origin="manual", exit_reason="MANUAL")

    assert sell_result.success is True
    assert engine.get_position("005930") is not None
    assert "SELL-1" in engine._state.pending_orders

    engine._apply_execution_event(_sell_event(broker_order_id="S-1", quantity=10, price=72000))

    assert engine.get_position("005930") is None
    assert engine._state.pending_orders == {}
    assert engine._daily_realized_pnl == Decimal("20000")


def test_reconciliation_converges_pending_buy_without_execution_notice(engine: TradingEngine) -> None:
    engine._executor.buy = MagicMock(
        return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="B-1")
    )
    engine.buy("005930", 10, 70000)

    engine._safe_inquire_daily_orders = MagicMock(
        return_value={
            "output1": [
                {
                    "odno": "B-1",
                    "pdno": "005930",
                    "sll_buy_dvsn_cd": "02",
                    "tot_ccld_qty": "10",
                    "avg_prc": "70000",
                    "ord_stts": "filled",
                }
            ]
        }
    )
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
        local_positions={},
    )

    engine._on_reconciliation_cycle(result)

    position = engine.get_position("005930")
    assert position is not None
    assert position.quantity == 10
    assert position.entry_price == Decimal("70000")
    assert position.status == PositionStatus.OPEN_RECONCILED
    assert engine._state.pending_orders == {}


def test_reconciliation_does_not_auto_close_sell_from_balance_only(engine: TradingEngine) -> None:
    engine._executor.buy = MagicMock(
        return_value=OrderResult(success=True, order_id="BUY-1", broker_order_id="B-1")
    )
    engine._executor.sell = MagicMock(
        return_value=OrderResult(success=True, order_id="SELL-1", broker_order_id="S-1")
    )
    engine.buy("005930", 10, 70000)
    engine._apply_execution_event(_buy_event(broker_order_id="B-1", quantity=10, price=70000))
    engine.sell("005930", 10, price=None, origin="manual", exit_reason="MANUAL")

    engine._safe_inquire_daily_orders = MagicMock(return_value={"output1": []})
    result = SimpleNamespace(
        is_clean=False,
        discrepancies=["Missing at broker: 005930"],
        orphan_positions=[],
        missing_positions=["005930"],
        quantity_mismatches={},
        broker_positions={},
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

    position = engine.get_position("005930")
    pending_order = engine._state.pending_orders["SELL-1"]
    assert position is not None
    assert position.quantity == 10
    assert pending_order.unresolved_reason == "sell_requires_execution_or_daily_order_confirmation"
    assert pending_order.status.value == "submitted"
