"""End-to-end trading simulation tests.

Verifies the complete trading engine flow under real-world conditions.
Only the KIS API boundary (OrderExecutor.buy/sell) is mocked;
all internal components (RiskManager, PositionManager, etc.) use real objects.

Scenarios:
  1. Normal buy -> take-profit exit (happy path)
  2. Buy -> stop-loss exit
  3. Risk limit: 6th position rejected (max_positions=5, enforce mode)
  4. Daily loss kill switch activation and subsequent buy rejection
  5. Market hours: buy blocked outside hours, sell always allowed
  6. Preflight check failure blocks engine start

Run:
    pytest tests/integration/test_trading_simulation.py -v
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from stock_manager.engine import TradingEngine
from stock_manager.trading.models import (
    TradingConfig,
    Position,
    PositionStatus,
)
from stock_manager.trading.executor import OrderResult
from stock_manager.persistence.recovery import RecoveryReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    """KIS API client mock returning standard balance/price responses."""
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "0",
        "msg_cd": "0",
        "output": {"stck_prpr": "70000"},
        "output1": [],
        "output2": [{"dnca_tot_amt": "10000000", "tot_evlu_amt": "10000000"}],
    }
    return client


def _config(market_hours_enabled: bool = False) -> TradingConfig:
    return TradingConfig(
        max_positions=5,
        polling_interval_sec=9999.0,  # suppress background polling
        rate_limit_per_sec=100,
        max_position_size_pct=Decimal("0.10"),
        default_stop_loss_pct=Decimal("0.05"),
        default_take_profit_pct=Decimal("0.10"),
        risk_enforcement_mode="enforce",
        market_hours_enabled=market_hours_enabled,
        daily_loss_limit_pct=Decimal("0.01"),
    )


def _buy_side_effect(pm):
    """Executor.buy mock that also opens a position (simulates broker fill)."""
    n = [0]

    def _buy(symbol, quantity, price, idempotency_key=None):  # noqa: ARG001
        n[0] += 1
        oid = f"ORD{n[0]:04d}"
        try:
            pm.open_position(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=Decimal(str(price)),
                    current_price=Decimal(str(price)),
                    status=PositionStatus.OPEN,
                )
            )
        except ValueError as e:
            if "already exists" not in str(e):
                raise
        return OrderResult(
            success=True,
            order_id=oid,
            broker_order_id=f"B{oid}",
            filled_quantity=quantity,
            filled_price=price,
        )

    return _buy


def _sell_side_effect(pm):
    """Executor.sell mock that also closes a position (simulates broker fill)."""
    n = [0]

    def _sell(symbol, quantity, price=None, idempotency_key=None):  # noqa: ARG001
        n[0] += 1
        oid = f"SORD{n[0]:04d}"
        pm.close_position(symbol)
        return OrderResult(
            success=True,
            order_id=oid,
            broker_order_id=f"S{oid}",
            filled_quantity=quantity,
            filled_price=price,
        )

    return _sell


def _make_engine(tmp_path, market_hours_enabled=False):
    """Create a TradingEngine with standard test configuration."""
    return TradingEngine(
        client=_mock_client(),
        config=_config(market_hours_enabled=market_hours_enabled),
        account_number="12345678",
        state_path=tmp_path / "sim_state.json",
        is_paper_trading=True,
    )


def _start(engine):
    """Patch external deps, start engine, wire executor mocks."""
    with (
        patch("stock_manager.engine.load_state", return_value=None),
        patch(
            "stock_manager.engine.startup_reconciliation",
            return_value=RecoveryReport(),
        ),
    ):
        engine.start()
    engine._executor.buy = MagicMock(
        side_effect=_buy_side_effect(engine._position_manager),
    )
    engine._executor.sell = MagicMock(
        side_effect=_sell_side_effect(engine._position_manager),
    )


# ===========================================================================
# Scenarios 1-4  (shared engine: enforce mode, market hours disabled)
# ===========================================================================


class TestTradingDaySimulation:
    """Full trading day simulation with enforce mode, 10M KRW portfolio."""

    @pytest.fixture
    def engine(self, tmp_path):
        eng = _make_engine(tmp_path)
        _start(eng)
        yield eng
        if eng._running:
            eng.stop()

    # -- Scenario 1: Buy -> Take Profit ------------------------------------

    def test_scenario1_buy_and_take_profit(self, engine):
        """Buy Samsung 10@70,000 -> price hits 77,000 -> take-profit sell.

        Expected realized PnL: +70,000 (10 shares x 7,000 gain).
        """
        result = engine.buy("005930", 10, 70000, stop_loss=66500, take_profit=77000)
        assert result.success is True

        pos = engine.get_position("005930")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.entry_price == Decimal("70000")
        assert pos.stop_loss == Decimal("66500")
        assert pos.take_profit == Decimal("77000")

        # Simulate price reaching take-profit level
        engine._get_current_price = MagicMock(return_value=77000)
        engine._position_manager.update_price("005930", Decimal("77000"))

        # Position closed via take-profit callback -> sell executed
        assert engine.get_position("005930") is None
        engine._executor.sell.assert_called_once_with(
            symbol="005930", quantity=10, price=77000,
        )
        assert engine._daily_realized_pnl == Decimal("70000")

    # -- Scenario 2: Buy -> Stop Loss --------------------------------------

    def test_scenario2_buy_and_stop_loss(self, engine):
        """Buy SK Hynix 5@150,000 -> price drops to 142,500 -> stop-loss sell.

        Expected realized PnL: -37,500 (5 shares x 7,500 loss).
        """
        result = engine.buy("000660", 5, 150000, stop_loss=142500, take_profit=165000)
        assert result.success is True

        pos = engine.get_position("000660")
        assert pos is not None
        assert pos.stop_loss == Decimal("142500")

        # Simulate price dropping to stop-loss level
        engine._get_current_price = MagicMock(return_value=142500)
        engine._position_manager.update_price("000660", Decimal("142500"))

        # Position closed via stop-loss callback -> sell executed
        assert engine.get_position("000660") is None
        engine._executor.sell.assert_called_once_with(
            symbol="000660", quantity=5, price=142500,
        )
        assert engine._daily_realized_pnl == Decimal("-37500")

    # -- Scenario 3: Risk Limit (max positions) ----------------------------

    def test_scenario3_max_positions_rejected_in_enforce_mode(self, engine):
        """5 positions filled -> 6th buy rejected by RiskManager."""
        symbols = ["005930", "000660", "035420", "051910", "006400"]
        for sym in symbols:
            r = engine.buy(sym, 10, 50000)
            assert r.success is True, f"Failed to buy {sym}: {r.message}"

        assert engine._position_manager.position_count == 5

        # 6th position -> rejected
        result = engine.buy("035720", 10, 50000)
        assert result.success is False
        assert "Maximum positions" in result.message
        # Executor was only called for the 5 successful buys
        assert engine._executor.buy.call_count == 5

    # -- Scenario 4: Daily Kill Switch -------------------------------------

    def test_scenario4_daily_kill_switch_blocks_buys(self, engine):
        """Realized daily loss of 1.5% (> 1% limit) triggers kill switch.

        Portfolio: 10,000,000 KRW
        Realized loss: -150,000 KRW (-1.5%)
        Threshold: -1% -> kill switch fires.
        """
        today = datetime.now(timezone.utc).date().isoformat()
        engine._daily_pnl_date = today
        engine._daily_baseline_equity = Decimal("10000000")
        engine._daily_realized_pnl = Decimal("-150000")  # -1.5%

        # buy() calls _refresh_risk_state -> _evaluate_daily_loss_killswitch
        result = engine.buy("005930", 10, 70000)
        assert engine._daily_kill_switch_active is True
        assert result.success is False
        assert "daily_loss_killswitch" in result.message

        # All subsequent buys also rejected
        result2 = engine.buy("000660", 5, 150000)
        assert result2.success is False
        assert "daily_loss_killswitch" in result2.message


# ===========================================================================
# Scenario 5: Market Hours
# ===========================================================================


class TestMarketHoursSimulation:
    """Buy blocked outside market hours, sell always allowed."""

    @pytest.fixture
    def engine(self, tmp_path):
        eng = _make_engine(tmp_path, market_hours_enabled=True)
        _start(eng)
        yield eng
        if eng._running:
            eng.stop()

    def test_scenario5_buy_blocked_sell_allowed_outside_hours(self, engine):
        """16:00 KST (after 15:20 close): buy rejected, sell permitted."""
        # Monday 16:00 KST — after market close at 15:20
        after_hours = datetime(2026, 3, 2, 16, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=after_hours)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            # Buy blocked outside market hours
            buy_result = engine.buy("005930", 10, 70000)
            assert buy_result.success is False
            assert "Market is closed" in buy_result.message

            # Pre-register a position for the sell test
            engine._position_manager.open_position(
                Position(
                    symbol="000660",
                    quantity=5,
                    entry_price=Decimal("150000"),
                    current_price=Decimal("150000"),
                    status=PositionStatus.OPEN,
                )
            )

            # Sell always allowed (stop-loss must execute anytime)
            sell_result = engine.sell("000660", 5, 142500)
            assert sell_result.success is True


# ===========================================================================
# Scenario 6: Preflight Failure
# ===========================================================================


class TestPreflightFailureSimulation:
    """Balance inquiry failure during preflight blocks engine start."""

    def test_scenario6_balance_inquiry_failure_blocks_start(self, tmp_path):
        """API error on balance inquiry -> RuntimeError('Preflight checks failed')."""
        engine = _make_engine(tmp_path)
        engine.client.make_request.side_effect = ConnectionError("API unavailable")

        with (
            patch("stock_manager.engine.load_state", return_value=None),
            patch(
                "stock_manager.engine.startup_reconciliation",
                return_value=RecoveryReport(),
            ),
            pytest.raises(RuntimeError, match="Preflight checks failed"),
        ):
            engine.start()

        assert engine._running is False
