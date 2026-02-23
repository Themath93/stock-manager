"""Unit tests for SellSpecialist exit execution."""

from __future__ import annotations

from decimal import Decimal

from stock_manager.trading.pipeline.sell_specialist import SellSpecialist
from stock_manager.trading.pipeline.state import PipelineEntry, PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_with_position(
    symbol: str = "AAPL",
    buy_price: Decimal | None = Decimal("100.00"),
    buy_quantity: int | None = 10,
) -> PipelineEntry:
    """Build a PipelineEntry that is in SELL_PENDING state with an open position."""
    e = PipelineEntry(symbol=symbol)
    e.transition(PipelineState.SCREENING)
    e.transition(PipelineState.EVALUATING)
    e.transition(PipelineState.CONSENSUS_APPROVED)
    e.transition(PipelineState.BUY_PENDING)
    e.transition(PipelineState.BOUGHT)
    e.transition(PipelineState.MONITORING)
    e.transition(PipelineState.SELL_PENDING)
    e.buy_price = buy_price
    e.buy_quantity = buy_quantity
    e.current_price = buy_price  # start at cost basis
    return e


# ---------------------------------------------------------------------------
# execute — happy path
# ---------------------------------------------------------------------------


class TestSellSpecialistExecute:
    def test_execute_returns_true_with_valid_position(self):
        specialist = SellSpecialist()
        entry = _entry_with_position()
        result = specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert result is True

    def test_execute_updates_current_price(self):
        specialist = SellSpecialist()
        entry = _entry_with_position()
        sell_price = Decimal("120.00")
        specialist.execute(entry, "TAKE_PROFIT", sell_price)
        assert entry.current_price == sell_price

    def test_execute_stores_exit_reason_on_error_message(self):
        specialist = SellSpecialist()
        entry = _entry_with_position()
        specialist.execute(entry, "TRAILING_STOP", Decimal("95.00"))
        assert entry.error_message == "TRAILING_STOP"

    def test_execute_stores_manual_reason(self):
        specialist = SellSpecialist()
        entry = _entry_with_position()
        specialist.execute(entry, "MANUAL", Decimal("105.00"))
        assert entry.error_message == "MANUAL"

    def test_execute_stores_max_holding_reason(self):
        specialist = SellSpecialist()
        entry = _entry_with_position()
        specialist.execute(entry, "MAX_HOLDING", Decimal("100.00"))
        assert entry.error_message == "MAX_HOLDING"


# ---------------------------------------------------------------------------
# PnL calculation
# ---------------------------------------------------------------------------


class TestSellSpecialistPnL:
    def test_pnl_positive_on_gain(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=10)
        specialist.execute(entry, "TAKE_PROFIT", Decimal("120.00"))
        # (120 - 100) * 10 = 200
        assert entry.unrealized_pnl == Decimal("200.00")

    def test_pnl_negative_on_loss(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=10)
        specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        # (90 - 100) * 10 = -100
        assert entry.unrealized_pnl == Decimal("-100.00")

    def test_pnl_zero_at_breakeven(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=5)
        specialist.execute(entry, "MANUAL", Decimal("100.00"))
        assert entry.unrealized_pnl == Decimal("0.00")

    def test_pnl_scales_with_quantity(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("50.00"), buy_quantity=100)
        specialist.execute(entry, "TAKE_PROFIT", Decimal("55.00"))
        # (55 - 50) * 100 = 500
        assert entry.unrealized_pnl == Decimal("500.00")

    def test_pnl_with_fractional_price_difference(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.50"), buy_quantity=4)
        specialist.execute(entry, "MANUAL", Decimal("101.75"))
        # (101.75 - 100.50) * 4 = 1.25 * 4 = 5.00
        assert entry.unrealized_pnl == Decimal("5.00")


# ---------------------------------------------------------------------------
# execute — failure cases
# ---------------------------------------------------------------------------


class TestSellSpecialistFailureCases:
    def test_returns_false_when_buy_price_is_none(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=None, buy_quantity=10)
        result = specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert result is False

    def test_returns_false_when_buy_quantity_is_none(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=None)
        result = specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert result is False

    def test_returns_false_when_buy_quantity_is_zero(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=0)
        result = specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert result is False

    def test_no_side_effects_when_buy_price_is_none(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=None, buy_quantity=10)
        original_pnl = entry.unrealized_pnl
        specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert entry.unrealized_pnl == original_pnl

    def test_no_side_effects_when_quantity_is_zero(self):
        specialist = SellSpecialist()
        entry = _entry_with_position(buy_price=Decimal("100.00"), buy_quantity=0)
        original_price = entry.current_price
        specialist.execute(entry, "STOP_LOSS", Decimal("90.00"))
        assert entry.current_price == original_price

    def test_stateless_across_multiple_calls(self):
        """SellSpecialist is stateless — two independent entries work independently."""
        specialist = SellSpecialist()
        entry_a = _entry_with_position("AAPL", Decimal("100.00"), 10)
        entry_b = _entry_with_position("GOOG", Decimal("200.00"), 5)

        specialist.execute(entry_a, "STOP_LOSS", Decimal("90.00"))
        specialist.execute(entry_b, "TAKE_PROFIT", Decimal("240.00"))

        assert entry_a.unrealized_pnl == Decimal("-100.00")  # (90-100)*10
        assert entry_b.unrealized_pnl == Decimal("200.00")   # (240-200)*5
