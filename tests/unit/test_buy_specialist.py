"""Unit tests for BuySpecialist position sizing and buy execution."""

from __future__ import annotations

import threading
from decimal import Decimal


from stock_manager.trading.pipeline.buy_specialist import BuySpecialist
from stock_manager.trading.pipeline.state import PipelineEntry, PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(symbol: str = "AAPL") -> PipelineEntry:
    """Build a PipelineEntry in BUY_PENDING state."""
    e = PipelineEntry(symbol=symbol)
    # Advance to BUY_PENDING so transitions are valid
    e.transition(PipelineState.SCREENING)
    e.transition(PipelineState.EVALUATING)
    e.transition(PipelineState.CONSENSUS_APPROVED)
    e.transition(PipelineState.BUY_PENDING)
    return e


# ---------------------------------------------------------------------------
# calculate_quantity
# ---------------------------------------------------------------------------


class TestCalculateQuantity:
    def test_basic_quantity_calculation(self):
        specialist = BuySpecialist(max_positions=10, max_position_pct=0.1)
        # budget = 10_000 * 0.1 = 1_000; qty = int(1_000 / 50) = 20
        qty = specialist.calculate_quantity(
            current_price=Decimal("50"), available_capital=Decimal("10000")
        )
        assert qty == 20

    def test_quantity_truncates_to_whole_shares(self):
        specialist = BuySpecialist(max_positions=10, max_position_pct=0.1)
        # budget = 10_000 * 0.1 = 1_000; qty = int(1_000 / 33) = 30
        qty = specialist.calculate_quantity(
            current_price=Decimal("33"), available_capital=Decimal("10000")
        )
        assert qty == 30

    def test_zero_price_returns_zero(self):
        specialist = BuySpecialist()
        qty = specialist.calculate_quantity(
            current_price=Decimal("0"), available_capital=Decimal("100000")
        )
        assert qty == 0

    def test_negative_price_returns_zero(self):
        specialist = BuySpecialist()
        qty = specialist.calculate_quantity(
            current_price=Decimal("-10"), available_capital=Decimal("100000")
        )
        assert qty == 0

    def test_respects_max_position_pct(self):
        specialist = BuySpecialist(max_positions=10, max_position_pct=0.05)
        # budget = 100_000 * 0.05 = 5_000; qty = int(5_000 / 100) = 50
        qty = specialist.calculate_quantity(
            current_price=Decimal("100"), available_capital=Decimal("100000")
        )
        assert qty == 50

    def test_large_capital_large_position(self):
        specialist = BuySpecialist(max_position_pct=0.1)
        # budget = 1_000_000 * 0.1 = 100_000; qty = int(100_000 / 200) = 500
        qty = specialist.calculate_quantity(
            current_price=Decimal("200"), available_capital=Decimal("1000000")
        )
        assert qty == 500

    def test_tiny_capital_may_produce_zero(self):
        specialist = BuySpecialist(max_position_pct=0.1)
        # budget = 10 * 0.1 = 1; qty = int(1 / 1000) = 0
        qty = specialist.calculate_quantity(
            current_price=Decimal("1000"), available_capital=Decimal("10")
        )
        assert qty == 0


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


class TestExecute:
    def test_execute_succeeds_with_valid_params(self):
        specialist = BuySpecialist(max_positions=5, max_position_pct=0.1)
        entry = _entry()
        result = specialist.execute(
            entry,
            current_price=Decimal("100"),
            available_capital=Decimal("10000"),
        )
        assert result is True

    def test_execute_sets_buy_price_on_entry(self):
        specialist = BuySpecialist()
        entry = _entry()
        specialist.execute(entry, Decimal("150"), Decimal("50000"))
        assert entry.buy_price == Decimal("150")

    def test_execute_sets_buy_quantity_on_entry(self):
        specialist = BuySpecialist(max_position_pct=0.1)
        entry = _entry()
        specialist.execute(entry, Decimal("100"), Decimal("10000"))
        # budget = 1_000; qty = 10
        assert entry.buy_quantity == 10

    def test_execute_sets_current_price_on_entry(self):
        specialist = BuySpecialist()
        entry = _entry()
        specialist.execute(entry, Decimal("200"), Decimal("100000"))
        assert entry.current_price == Decimal("200")

    def test_execute_increments_open_positions(self):
        specialist = BuySpecialist(max_positions=5)
        assert specialist.open_positions == 0
        specialist.execute(_entry(), Decimal("100"), Decimal("50000"))
        assert specialist.open_positions == 1
        specialist.execute(_entry("GOOG"), Decimal("100"), Decimal("50000"))
        assert specialist.open_positions == 2

    def test_execute_returns_false_at_max_positions(self):
        specialist = BuySpecialist(max_positions=2, max_position_pct=0.1)
        specialist.execute(_entry("A"), Decimal("10"), Decimal("10000"))
        specialist.execute(_entry("B"), Decimal("10"), Decimal("10000"))
        result = specialist.execute(_entry("C"), Decimal("10"), Decimal("10000"))
        assert result is False
        assert specialist.open_positions == 2

    def test_execute_returns_false_when_zero_price(self):
        specialist = BuySpecialist()
        entry = _entry()
        result = specialist.execute(entry, Decimal("0"), Decimal("50000"))
        assert result is False

    def test_execute_returns_false_when_quantity_is_zero(self):
        # tiny capital => quantity == 0
        specialist = BuySpecialist(max_position_pct=0.01)
        entry = _entry()
        result = specialist.execute(entry, Decimal("9999"), Decimal("1"))
        assert result is False

    def test_execute_does_not_increment_on_failure(self):
        specialist = BuySpecialist(max_positions=3, max_position_pct=0.01)
        entry = _entry()
        specialist.execute(entry, Decimal("9999"), Decimal("1"))  # will fail (qty=0)
        assert specialist.open_positions == 0


# ---------------------------------------------------------------------------
# release_position
# ---------------------------------------------------------------------------


class TestReleasePosition:
    def test_release_decrements_counter(self):
        specialist = BuySpecialist(max_positions=5)
        specialist.execute(_entry("A"), Decimal("100"), Decimal("50000"))
        specialist.execute(_entry("B"), Decimal("100"), Decimal("50000"))
        assert specialist.open_positions == 2
        specialist.release_position()
        assert specialist.open_positions == 1

    def test_release_does_not_go_below_zero(self):
        specialist = BuySpecialist()
        specialist.release_position()
        assert specialist.open_positions == 0

    def test_release_allows_new_buy_after_capacity_full(self):
        specialist = BuySpecialist(max_positions=1, max_position_pct=0.1)
        specialist.execute(_entry("A"), Decimal("100"), Decimal("10000"))
        assert specialist.open_positions == 1

        # At max — new buy fails
        result = specialist.execute(_entry("B"), Decimal("100"), Decimal("10000"))
        assert result is False

        # Release one slot then retry
        specialist.release_position()
        result = specialist.execute(_entry("B"), Decimal("100"), Decimal("10000"))
        assert result is True


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestBuySpecialistThreadSafety:
    def test_concurrent_execute_respects_max_positions(self):
        max_pos = 5
        specialist = BuySpecialist(max_positions=max_pos, max_position_pct=0.1)
        successes = []
        lock = threading.Lock()

        def do_buy(symbol: str):
            entry = _entry(symbol)
            ok = specialist.execute(entry, Decimal("100"), Decimal("50000"))
            with lock:
                successes.append(ok)

        threads = [threading.Thread(target=do_buy, args=(f"SYM{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert specialist.open_positions == max_pos
        assert successes.count(True) == max_pos

    def test_concurrent_release_does_not_go_negative(self):
        specialist = BuySpecialist(max_positions=10)
        # Buy 3 positions first
        for i in range(3):
            specialist.execute(_entry(f"SYM{i}"), Decimal("100"), Decimal("50000"))

        # Release 10 times concurrently (7 extra releases)
        threads = [threading.Thread(target=specialist.release_position) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert specialist.open_positions == 0
