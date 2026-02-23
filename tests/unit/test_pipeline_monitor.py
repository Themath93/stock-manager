"""Unit tests for PositionMonitor exit signal detection."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from stock_manager.trading.pipeline.monitor import PositionMonitor
from stock_manager.trading.pipeline.state import PipelineEntry, PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_in_monitoring(
    symbol: str = "AAPL",
    buy_price: Decimal = Decimal("100.00"),
    buy_quantity: int = 10,
    entered_days_ago: int = 0,
) -> PipelineEntry:
    """Return a PipelineEntry in MONITORING state with an open position."""
    e = PipelineEntry(symbol=symbol)
    e.transition(PipelineState.SCREENING)
    e.transition(PipelineState.EVALUATING)
    e.transition(PipelineState.CONSENSUS_APPROVED)
    e.transition(PipelineState.BUY_PENDING)
    e.transition(PipelineState.BOUGHT)
    e.transition(PipelineState.MONITORING)
    e.buy_price = buy_price
    e.buy_quantity = buy_quantity
    e.current_price = buy_price
    if entered_days_ago:
        e.entered_at = datetime.now() - timedelta(days=entered_days_ago)
    return e


def _default_monitor() -> PositionMonitor:
    return PositionMonitor(
        stop_loss_pct=0.07,
        take_profit_pct=0.20,
        trailing_stop_pct=0.05,
        max_holding_days=90,
    )


# ---------------------------------------------------------------------------
# Guard: missing buy_price / buy_quantity
# ---------------------------------------------------------------------------


class TestMonitorGuards:
    def test_returns_none_when_buy_price_is_none(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring()
        entry.buy_price = None
        result = monitor.check(entry, Decimal("100.00"))
        assert result is None

    def test_returns_none_when_buy_quantity_is_none(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring()
        entry.buy_quantity = None
        result = monitor.check(entry, Decimal("100.00"))
        assert result is None


# ---------------------------------------------------------------------------
# Stop loss
# ---------------------------------------------------------------------------


class TestStopLoss:
    def test_stop_loss_triggers_at_exact_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # 100 * (1 - 0.07) = 93.00 — exactly at threshold
        result = monitor.check(entry, Decimal("93.00"))
        assert result == "STOP_LOSS"

    def test_stop_loss_triggers_below_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        result = monitor.check(entry, Decimal("92.99"))
        assert result == "STOP_LOSS"

    def test_stop_loss_does_not_trigger_above_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # 93.01 > 93.00 → no stop loss
        result = monitor.check(entry, Decimal("93.01"))
        assert result != "STOP_LOSS"

    def test_stop_loss_with_custom_pct(self):
        monitor = PositionMonitor(stop_loss_pct=0.10, take_profit_pct=0.50)
        entry = _entry_in_monitoring(buy_price=Decimal("200.00"))
        # 200 * 0.90 = 180.00
        result = monitor.check(entry, Decimal("179.99"))
        assert result == "STOP_LOSS"

    def test_stop_loss_takes_priority_over_take_profit(self):
        """Pathological: if stop fires first in priority order it wins."""
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # Price below stop loss
        result = monitor.check(entry, Decimal("90.00"))
        assert result == "STOP_LOSS"


# ---------------------------------------------------------------------------
# Take profit
# ---------------------------------------------------------------------------


class TestTakeProfit:
    def test_take_profit_triggers_at_exact_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # 100 * 1.20 = 120.00
        result = monitor.check(entry, Decimal("120.00"))
        assert result == "TAKE_PROFIT"

    def test_take_profit_triggers_above_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        result = monitor.check(entry, Decimal("125.00"))
        assert result == "TAKE_PROFIT"

    def test_take_profit_does_not_trigger_below_threshold(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        result = monitor.check(entry, Decimal("119.99"))
        assert result != "TAKE_PROFIT"

    def test_take_profit_with_custom_pct(self):
        monitor = PositionMonitor(stop_loss_pct=0.07, take_profit_pct=0.30)
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # 100 * 1.30 = 130
        result = monitor.check(entry, Decimal("130.00"))
        assert result == "TAKE_PROFIT"


# ---------------------------------------------------------------------------
# Trailing stop
# ---------------------------------------------------------------------------


class TestTrailingStop:
    def test_trailing_stop_initialised_on_first_check(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # price = 110 (above take profit threshold 120? no — 110 < 120, above stop 93)
        monitor.check(entry, Decimal("110.00"))
        # trailing = 110 * (1 - 0.05) = 104.50
        assert entry.trailing_stop == Decimal("110.00") * Decimal("0.95")

    def test_trailing_stop_ratchets_up_with_price_increase(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        monitor.check(entry, Decimal("105.00"))  # trailing = 105 * 0.95 = 99.75
        first_trailing = entry.trailing_stop
        monitor.check(entry, Decimal("110.00"))  # trailing = 110 * 0.95 = 104.50
        assert entry.trailing_stop > first_trailing

    def test_trailing_stop_never_decreases(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # Set a high trailing stop
        monitor.check(entry, Decimal("110.00"))  # trailing = 104.50
        high_trailing = entry.trailing_stop
        # Price drops (but not to trigger stop)
        monitor.check(entry, Decimal("107.00"))  # new candidate = 101.65
        # Trailing stop must remain at the higher value
        assert entry.trailing_stop == high_trailing

    def test_trailing_stop_triggers_when_price_drops_from_peak(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        # Push price up to set trailing stop high
        monitor.check(entry, Decimal("110.00"))   # trailing = 104.50
        # Now price drops below trailing stop
        result = monitor.check(entry, Decimal("104.00"))
        assert result == "TRAILING_STOP"

    def test_trailing_stop_does_not_trigger_above_trailing_level(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        monitor.check(entry, Decimal("110.00"))   # trailing = 104.50
        # Price at 105 — above trailing stop 104.50
        result = monitor.check(entry, Decimal("105.00"))
        assert result != "TRAILING_STOP"

    def test_trailing_stop_with_custom_pct(self):
        monitor = PositionMonitor(
            stop_loss_pct=0.07, take_profit_pct=0.50, trailing_stop_pct=0.10
        )
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        monitor.check(entry, Decimal("110.00"))  # trailing = 110 * 0.90 = 99.0
        # Price drops below 99.0
        result = monitor.check(entry, Decimal("98.00"))
        assert result == "TRAILING_STOP"


# ---------------------------------------------------------------------------
# Max holding period
# ---------------------------------------------------------------------------


class TestMaxHoldingPeriod:
    def test_max_holding_triggers_at_90_days(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=90
        )
        # Price in neutral zone (no other triggers)
        result = monitor.check(entry, Decimal("100.00"))
        assert result == "MAX_HOLDING"

    def test_max_holding_triggers_beyond_90_days(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=120
        )
        result = monitor.check(entry, Decimal("100.00"))
        assert result == "MAX_HOLDING"

    def test_max_holding_does_not_trigger_before_90_days(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=89
        )
        result = monitor.check(entry, Decimal("100.00"))
        assert result != "MAX_HOLDING"

    def test_max_holding_with_custom_days(self):
        monitor = PositionMonitor(max_holding_days=30)
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=30
        )
        result = monitor.check(entry, Decimal("100.00"))
        assert result == "MAX_HOLDING"


# ---------------------------------------------------------------------------
# No exit signal
# ---------------------------------------------------------------------------


class TestNoExitSignal:
    def test_returns_none_when_no_conditions_met(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=1
        )
        # Price in safe zone: above stop (93), below take profit (120)
        result = monitor.check(entry, Decimal("100.00"))
        assert result is None

    def test_returns_none_for_slight_gain(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=5
        )
        result = monitor.check(entry, Decimal("105.00"))
        assert result is None

    def test_returns_none_for_slight_loss_above_stop(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(
            buy_price=Decimal("100.00"), entered_days_ago=5
        )
        result = monitor.check(entry, Decimal("95.00"))
        assert result is None


# ---------------------------------------------------------------------------
# unrealized_pnl updates
# ---------------------------------------------------------------------------


class TestUnrealizedPnlUpdates:
    def test_pnl_updated_on_gain(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"), buy_quantity=10)
        monitor.check(entry, Decimal("105.00"))
        # (105 - 100) * 10 = 50
        assert entry.unrealized_pnl == Decimal("50.00")

    def test_pnl_updated_on_loss(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"), buy_quantity=10)
        monitor.check(entry, Decimal("95.00"))
        # (95 - 100) * 10 = -50
        assert entry.unrealized_pnl == Decimal("-50.00")

    def test_current_price_updated_on_each_check(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"))
        monitor.check(entry, Decimal("105.00"))
        assert entry.current_price == Decimal("105.00")
        monitor.check(entry, Decimal("107.00"))
        assert entry.current_price == Decimal("107.00")

    def test_pnl_zero_at_breakeven(self):
        monitor = _default_monitor()
        entry = _entry_in_monitoring(buy_price=Decimal("100.00"), buy_quantity=5)
        monitor.check(entry, Decimal("100.00"))
        assert entry.unrealized_pnl == Decimal("0.00")
