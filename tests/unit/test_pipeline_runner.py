"""Unit tests for TradingPipelineRunner state machine orchestrator."""

from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import MagicMock


from stock_manager.trading.pipeline.buy_specialist import BuySpecialist
from stock_manager.trading.pipeline.monitor import PositionMonitor
from stock_manager.trading.pipeline.runner import TradingPipelineRunner
from stock_manager.trading.pipeline.sell_specialist import SellSpecialist
from stock_manager.trading.pipeline.state import PipelineState
from stock_manager.trading.strategies.consensus import ConsensusStrategy


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_score(passes: bool = True, buy_count: int = 3, total_votes: int = 5, avg_conviction: float = 0.8):
    """Build a mock ConsensusScore."""
    score = MagicMock()
    score.passes_all = passes
    score.criteria_passed = buy_count
    score.buy_count = buy_count
    score.total_votes = total_votes
    score.avg_conviction = avg_conviction
    consensus_result = MagicMock()
    consensus_result.passes_threshold = passes
    score.consensus_result = consensus_result
    return score


def _make_runner(
    score=None,
    buy_success: bool = True,
    sell_success: bool = True,
    exit_reason: str | None = None,
):
    """Build a TradingPipelineRunner with fully mocked dependencies."""
    strategy = MagicMock(spec=ConsensusStrategy)
    strategy.evaluate.return_value = score if score is not None else _make_score()

    buy = MagicMock(spec=BuySpecialist)
    buy.execute.return_value = buy_success

    sell = MagicMock(spec=SellSpecialist)
    sell.execute.return_value = sell_success

    monitor = MagicMock(spec=PositionMonitor)
    monitor.check.return_value = exit_reason

    runner = TradingPipelineRunner(
        consensus_strategy=strategy,
        buy_specialist=buy,
        sell_specialist=sell,
        monitor=monitor,
    )
    return runner, strategy, buy, sell, monitor


# ---------------------------------------------------------------------------
# add_to_watchlist
# ---------------------------------------------------------------------------


class TestAddToWatchlist:
    def test_adds_new_symbols(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL", "GOOG"])

        entries = runner.entries
        assert "AAPL" in entries
        assert "GOOG" in entries
        assert entries["AAPL"].state == PipelineState.WATCHLIST
        assert entries["GOOG"].state == PipelineState.WATCHLIST

    def test_skips_duplicate_symbols(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        original = runner.entries["AAPL"]

        runner.add_to_watchlist(["AAPL"])

        assert runner.entries["AAPL"] is original

    def test_adds_empty_list_without_error(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist([])
        assert runner.entries == {}

    def test_multiple_batches_accumulate(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.add_to_watchlist(["GOOG"])
        assert len(runner.entries) == 2

    def test_entries_property_returns_snapshot(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        snapshot = runner.entries
        runner.add_to_watchlist(["GOOG"])
        # Snapshot is independent of later mutations
        assert "GOOG" not in snapshot


# ---------------------------------------------------------------------------
# Individual state transitions (single run_cycle step)
# ---------------------------------------------------------------------------


class TestStateMachineTransitions:
    def test_watchlist_to_screening(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.SCREENING

    def test_screening_to_evaluating(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # WATCHLIST -> SCREENING
        runner.run_cycle()  # SCREENING -> EVALUATING
        assert runner.entries["AAPL"].state == PipelineState.EVALUATING

    def test_evaluating_to_consensus_approved(self):
        runner, strategy, *_ = _make_runner(score=_make_score(passes=True))
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_APPROVED
        assert runner.entries["AAPL"].state == PipelineState.CONSENSUS_APPROVED

    def test_evaluating_to_consensus_rejected(self):
        runner, strategy, *_ = _make_runner(score=_make_score(passes=False))
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_REJECTED
        assert runner.entries["AAPL"].state == PipelineState.CONSENSUS_REJECTED

    def test_consensus_rejected_returns_to_watchlist(self):
        runner, strategy, *_ = _make_runner(score=_make_score(passes=False))
        runner.add_to_watchlist(["AAPL"])
        for _ in range(4):
            runner.run_cycle()
        # CONSENSUS_REJECTED -> WATCHLIST
        assert runner.entries["AAPL"].state == PipelineState.WATCHLIST

    def test_consensus_rejected_clears_consensus_result(self):
        runner, strategy, *_ = _make_runner(score=_make_score(passes=False))
        runner.add_to_watchlist(["AAPL"])
        for _ in range(4):
            runner.run_cycle()
        assert runner.entries["AAPL"].consensus_result is None

    def test_consensus_approved_to_buy_pending(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        for _ in range(4):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.BUY_PENDING

    def test_buy_pending_to_bought_when_price_set(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=True)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("150.00")
        for _ in range(5):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.BOUGHT

    def test_bought_to_monitoring(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=True)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("150.00")
        for _ in range(6):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.MONITORING

    def test_monitoring_to_sell_pending_on_exit_signal(self):
        runner, strategy, buy, sell, monitor = _make_runner(
            buy_success=True, exit_reason="STOP_LOSS"
        )
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("150.00")
        for _ in range(7):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.SELL_PENDING

    def test_sell_pending_to_sold(self):
        runner, strategy, buy, sell, monitor = _make_runner(
            buy_success=True, sell_success=True, exit_reason="TAKE_PROFIT"
        )
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("150.00")
        for _ in range(8):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.SOLD


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    def test_full_happy_path_watchlist_to_sold(self):
        """Drive a symbol from WATCHLIST all the way to SOLD in one test."""
        runner, strategy, buy, sell, monitor = _make_runner(
            score=_make_score(passes=True),
            buy_success=True,
            sell_success=True,
            exit_reason="TAKE_PROFIT",
        )
        runner.add_to_watchlist(["MSFT"])
        runner.entries["MSFT"].current_price = Decimal("200.00")

        expected_states = [
            PipelineState.SCREENING,
            PipelineState.EVALUATING,
            PipelineState.CONSENSUS_APPROVED,
            PipelineState.BUY_PENDING,
            PipelineState.BOUGHT,
            PipelineState.MONITORING,
            PipelineState.SELL_PENDING,
            PipelineState.SOLD,
        ]

        for expected in expected_states:
            runner.run_cycle()
            assert runner.entries["MSFT"].state == expected, (
                f"Expected {expected.name}, got {runner.entries['MSFT'].state.name}"
            )

    def test_consensus_store_set_on_approved_path(self):
        score = _make_score(passes=True)
        runner, strategy, buy, sell, monitor = _make_runner(score=score, buy_success=True)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("100.00")
        for _ in range(3):
            runner.run_cycle()
        # After EVALUATING the consensus_result should be stored
        assert runner.entries["AAPL"].consensus_result is score.consensus_result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_error_state_on_zero_price_buy(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=True)
        runner.add_to_watchlist(["AAPL"])
        # Leave current_price as None -> zero price
        for _ in range(5):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.ERROR

    def test_error_state_when_buy_execute_returns_false(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=False)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("100.00")
        for _ in range(5):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.ERROR

    def test_error_recovery_to_watchlist(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=False)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("100.00")
        for _ in range(5):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.ERROR

        # Next cycle recovers to WATCHLIST
        runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.WATCHLIST

    def test_error_recovery_clears_error_message(self):
        runner, strategy, buy, sell, monitor = _make_runner(buy_success=False)
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("100.00")
        for _ in range(5):
            runner.run_cycle()
        # In ERROR state, error_message is set
        assert runner.entries["AAPL"].error_message is not None

        runner.run_cycle()  # ERROR -> WATCHLIST
        assert runner.entries["AAPL"].error_message is None

    def test_exception_during_step_sets_error_state(self):
        runner, strategy, buy, sell, monitor = _make_runner()
        strategy.evaluate.side_effect = RuntimeError("network failure")
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # evaluate raises -> ERROR
        assert runner.entries["AAPL"].state == PipelineState.ERROR

    def test_error_message_contains_exception_text(self):
        runner, strategy, buy, sell, monitor = _make_runner()
        strategy.evaluate.side_effect = RuntimeError("quota exceeded")
        runner.add_to_watchlist(["AAPL"])
        for _ in range(3):
            runner.run_cycle()
        assert "quota exceeded" in runner.entries["AAPL"].error_message

    def test_sell_failure_sends_to_error(self):
        runner, strategy, buy, sell, monitor = _make_runner(
            buy_success=True, sell_success=False, exit_reason="STOP_LOSS"
        )
        runner.add_to_watchlist(["AAPL"])
        runner.entries["AAPL"].current_price = Decimal("100.00")
        for _ in range(8):
            runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.ERROR


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_add_to_watchlist_no_data_loss(self):
        runner, *_ = _make_runner()
        symbols = [f"SYM{i}" for i in range(50)]

        threads = [
            threading.Thread(target=runner.add_to_watchlist, args=([s],))
            for s in symbols
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(runner.entries) == 50

    def test_concurrent_run_cycle_does_not_raise(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL", "GOOG", "MSFT"])
        errors = []

        def run():
            try:
                for _ in range(3):
                    runner.run_cycle()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ---------------------------------------------------------------------------
# Logger integration (with pipeline_logger)
# ---------------------------------------------------------------------------


class TestPipelineLogger:
    def test_logger_log_state_change_called_on_add(self):
        pipeline_logger = MagicMock()
        strategy = MagicMock(spec=ConsensusStrategy)
        buy = MagicMock(spec=BuySpecialist)
        sell = MagicMock(spec=SellSpecialist)
        monitor = MagicMock(spec=PositionMonitor)

        runner = TradingPipelineRunner(
            consensus_strategy=strategy,
            buy_specialist=buy,
            sell_specialist=sell,
            monitor=monitor,
            pipeline_logger=pipeline_logger,
        )
        runner.add_to_watchlist(["AAPL"])
        pipeline_logger.log_state_change.assert_called_once()

    def test_no_logger_does_not_raise(self):
        runner, *_ = _make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # Should not raise even without logger
