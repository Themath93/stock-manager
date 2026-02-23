"""Unit tests for the consensus trading pipeline (Phases 1-5).

Covers: PipelineState, PipelineEntry, VoteAggregator, ConsensusStrategy,
BuySpecialist, SellSpecialist, PositionMonitor, TradingPipelineRunner,
ConsensusEvaluator, CircuitBreaker, VoteParser, HybridPersona, PipelineJsonLogger.
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from stock_manager.trading.consensus.aggregator import VoteAggregator
from stock_manager.trading.consensus.evaluator import ConsensusEvaluator
from stock_manager.trading.consensus.vote_parser import VoteParser
from stock_manager.trading.llm.circuit_breaker import CircuitBreaker, CircuitState
from stock_manager.trading.llm.config import InvocationCounter, LLMConfig
from stock_manager.trading.logging.pipeline_logger import PipelineJsonLogger
from stock_manager.trading.personas.base import InvestorPersona
from stock_manager.trading.personas.models import (
    AdvisoryVote,
    ConsensusResult,
    MarketSnapshot,
    PersonaCategory,
    PersonaVote,
    VoteAction,
)
from stock_manager.trading.pipeline.buy_specialist import BuySpecialist
from stock_manager.trading.pipeline.monitor import PositionMonitor
from stock_manager.trading.pipeline.runner import TradingPipelineRunner
from stock_manager.trading.pipeline.sell_specialist import SellSpecialist
from stock_manager.trading.pipeline.state import (
    VALID_TRANSITIONS,
    PipelineEntry,
    PipelineState,
)
from stock_manager.trading.strategies.consensus import ConsensusScore, ConsensusStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vote(
    action: VoteAction = VoteAction.BUY,
    conviction: float = 0.8,
    category: PersonaCategory = PersonaCategory.VALUE,
    persona_name: str = "TestPersona",
) -> PersonaVote:
    return PersonaVote(
        persona_name=persona_name,
        action=action,
        conviction=conviction,
        reasoning="test",
        criteria_met={},
        category=category,
    )


def _make_snapshot(symbol: str = "005930") -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        name="Samsung",
        market="KOSPI",
        sector="Electronics",
        current_price=Decimal("70000"),
        per=10.0,
        pbr=1.5,
        roe=12.0,
        eps=Decimal("7000"),
        dividend_yield=2.0,
        debt_to_equity=0.5,
        current_ratio=1.8,
        operating_margin=15.0,
        net_margin=10.0,
        revenue_growth_yoy=5.0,
        earnings_growth_yoy=8.0,
        sma_20=69000.0,
        sma_200=65000.0,
        rsi_14=55.0,
        macd_signal=0.001,
        adx_14=25.0,
        atr_14=1500.0,
        price_52w_high=Decimal("80000"),
        price_52w_low=Decimal("55000"),
    )


def _make_consensus_result(passes: bool = True, buy_count: int = 8) -> ConsensusResult:
    return ConsensusResult(
        symbol="AAPL",
        votes=[],
        advisory_vote=None,
        buy_count=buy_count,
        sell_count=1,
        hold_count=1,
        abstain_count=0,
        passes_threshold=passes,
        avg_conviction=0.75,
        category_diversity=3,
    )


# ===========================================================================
# 1. PipelineState and PipelineEntry
# ===========================================================================


class TestPipelineState:
    """Test PipelineState transitions and PipelineEntry defaults."""

    def test_all_valid_transitions_succeed(self):
        for from_state, to_states in VALID_TRANSITIONS.items():
            for to_state in to_states:
                entry = PipelineEntry(symbol="TEST")
                entry.state = from_state
                entry.transition(to_state)
                assert entry.state == to_state

    def test_invalid_transition_raises_value_error(self):
        entry = PipelineEntry(symbol="TEST")
        assert entry.state == PipelineState.WATCHLIST
        try:
            entry.transition(PipelineState.BOUGHT)
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "Invalid transition" in str(exc)

    def test_sold_is_terminal_no_transitions(self):
        entry = PipelineEntry(symbol="TEST")
        entry.state = PipelineState.SOLD
        try:
            entry.transition(PipelineState.WATCHLIST)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_entry_default_values(self):
        entry = PipelineEntry(symbol="AAPL")
        assert entry.symbol == "AAPL"
        assert entry.state == PipelineState.WATCHLIST
        assert entry.buy_price is None
        assert entry.buy_quantity is None
        assert entry.current_price is None
        assert entry.unrealized_pnl is None
        assert entry.trailing_stop is None
        assert entry.consensus_result is None
        assert entry.error_message is None
        assert entry.history == []

    def test_history_tracking_on_transition(self):
        entry = PipelineEntry(symbol="TEST")
        original_state = entry.state
        original_time = entry.entered_at
        entry.transition(PipelineState.SCREENING)
        assert len(entry.history) == 1
        assert entry.history[0][0] == original_state
        assert entry.history[0][1] == original_time
        assert entry.state == PipelineState.SCREENING

    def test_multiple_transitions_build_history(self):
        entry = PipelineEntry(symbol="TEST")
        entry.transition(PipelineState.SCREENING)
        entry.transition(PipelineState.EVALUATING)
        entry.transition(PipelineState.CONSENSUS_APPROVED)
        assert len(entry.history) == 3
        assert entry.history[0][0] == PipelineState.WATCHLIST
        assert entry.history[1][0] == PipelineState.SCREENING
        assert entry.history[2][0] == PipelineState.EVALUATING

    def test_error_recovery_to_watchlist(self):
        entry = PipelineEntry(symbol="TEST")
        entry.transition(PipelineState.ERROR)
        assert entry.state == PipelineState.ERROR
        entry.transition(PipelineState.WATCHLIST)
        assert entry.state == PipelineState.WATCHLIST

    def test_transition_updates_entered_at(self):
        entry = PipelineEntry(symbol="TEST")
        before = entry.entered_at
        time.sleep(0.01)
        entry.transition(PipelineState.SCREENING)
        assert entry.entered_at >= before


# ===========================================================================
# 2. VoteAggregator
# ===========================================================================


class TestVoteAggregator:
    """Test the 4-gate vote aggregation logic."""

    def test_all_four_gates_pass(self):
        agg = VoteAggregator(threshold=3, quorum_pct=0.5, min_conviction=0.5, min_category_diversity=2)
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.7, PersonaCategory.GROWTH),
            _make_vote(VoteAction.BUY, 0.9, PersonaCategory.MOMENTUM),
            _make_vote(VoteAction.HOLD, 0.3, PersonaCategory.MACRO),
        ]
        result = agg.aggregate(votes)
        assert result.passes_threshold is True
        assert result.buy_count == 3
        assert result.hold_count == 1

    def test_quorum_fails(self):
        agg = VoteAggregator(threshold=1, quorum_pct=0.8, min_conviction=0.0, min_category_diversity=1)
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.ABSTAIN, 0.0, PersonaCategory.GROWTH),
            _make_vote(VoteAction.ABSTAIN, 0.0, PersonaCategory.MOMENTUM),
            _make_vote(VoteAction.ABSTAIN, 0.0, PersonaCategory.MACRO),
            _make_vote(VoteAction.ABSTAIN, 0.0, PersonaCategory.QUANTITATIVE),
        ]
        result = agg.aggregate(votes)
        # Only 1 of 5 non-abstain = 0.2 < 0.8
        assert result.passes_threshold is False

    def test_threshold_fails(self):
        agg = VoteAggregator(threshold=5, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=1)
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.7, PersonaCategory.GROWTH),
            _make_vote(VoteAction.SELL, 0.5, PersonaCategory.MOMENTUM),
            _make_vote(VoteAction.HOLD, 0.3, PersonaCategory.MACRO),
        ]
        result = agg.aggregate(votes)
        # 2 BUY < threshold 5
        assert result.passes_threshold is False
        assert result.buy_count == 2

    def test_conviction_fails(self):
        agg = VoteAggregator(threshold=2, quorum_pct=0.5, min_conviction=0.9, min_category_diversity=1)
        votes = [
            _make_vote(VoteAction.BUY, 0.3, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.4, PersonaCategory.GROWTH),
            _make_vote(VoteAction.HOLD, 0.5, PersonaCategory.MOMENTUM),
        ]
        result = agg.aggregate(votes)
        # avg conviction 0.35 < 0.9
        assert result.passes_threshold is False

    def test_diversity_fails(self):
        agg = VoteAggregator(threshold=2, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=3)
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.7, PersonaCategory.VALUE),
            _make_vote(VoteAction.HOLD, 0.5, PersonaCategory.MOMENTUM),
        ]
        result = agg.aggregate(votes)
        # Only 1 distinct category among BUY voters < 3
        assert result.passes_threshold is False
        assert result.category_diversity == 1

    def test_empty_votes(self):
        agg = VoteAggregator()
        result = agg.aggregate([])
        assert result.passes_threshold is False
        assert result.buy_count == 0
        assert result.sell_count == 0
        assert result.hold_count == 0
        assert result.abstain_count == 0
        assert result.avg_conviction == 0.0
        assert result.category_diversity == 0

    def test_advisory_vote_stored_but_excluded_from_binding(self):
        agg = VoteAggregator(threshold=1, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=1)
        advisory = AdvisoryVote(
            persona_name="Wood",
            action=VoteAction.ADVISORY,
            innovation_score=0.9,
            disruption_assessment="High disruption",
            category=PersonaCategory.INNOVATION,
        )
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.HOLD, 0.5, PersonaCategory.GROWTH),
        ]
        result = agg.aggregate(votes, advisory_vote=advisory)
        assert result.advisory_vote is advisory
        # Advisory vote does NOT affect buy_count
        assert result.buy_count == 1
        # Total votes is 2, not 3
        assert len(result.votes) == 2

    def test_category_diversity_with_different_categories(self):
        agg = VoteAggregator(threshold=4, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=4)
        votes = [
            _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.7, PersonaCategory.GROWTH),
            _make_vote(VoteAction.BUY, 0.6, PersonaCategory.MOMENTUM),
            _make_vote(VoteAction.BUY, 0.9, PersonaCategory.MACRO),
            _make_vote(VoteAction.HOLD, 0.3, PersonaCategory.QUANTITATIVE),
        ]
        result = agg.aggregate(votes)
        assert result.category_diversity == 4
        assert result.passes_threshold is True

    def test_avg_conviction_rounded(self):
        agg = VoteAggregator(threshold=2, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=1)
        votes = [
            _make_vote(VoteAction.BUY, 0.333, PersonaCategory.VALUE),
            _make_vote(VoteAction.BUY, 0.666, PersonaCategory.GROWTH),
        ]
        result = agg.aggregate(votes)
        # (0.333 + 0.666) / 2 = 0.4995 -> rounded to 4 decimals = 0.4995
        assert result.avg_conviction == round(0.4995, 4)


# ===========================================================================
# 3. ConsensusStrategy and ConsensusScore
# ===========================================================================


class TestConsensusScore:
    """Test ConsensusScore properties."""

    def test_passes_all_delegates_to_consensus_result(self):
        cr = _make_consensus_result(passes=True)
        score = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=8, total_votes=10, avg_conviction=0.75
        )
        assert score.passes_all is True

    def test_passes_all_false_when_result_fails(self):
        cr = _make_consensus_result(passes=False)
        score = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=3, total_votes=10, avg_conviction=0.5
        )
        assert score.passes_all is False

    def test_criteria_passed_returns_buy_count(self):
        cr = _make_consensus_result(passes=True, buy_count=7)
        score = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=7, total_votes=10, avg_conviction=0.8
        )
        assert score.criteria_passed == 7


class TestConsensusStrategy:
    """Test ConsensusStrategy.evaluate."""

    def test_evaluate_returns_consensus_score_on_success(self):
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = ConsensusResult(
            symbol="AAPL",
            votes=[],
            advisory_vote=None,
            buy_count=8,
            sell_count=1,
            hold_count=1,
            abstain_count=0,
            passes_threshold=True,
            avg_conviction=0.8,
            category_diversity=3,
        )
        strategy = ConsensusStrategy(evaluator=mock_evaluator)
        score = strategy.evaluate("AAPL")
        assert score is not None
        assert isinstance(score, ConsensusScore)
        assert score.symbol == "AAPL"
        assert score.buy_count == 8
        assert score.total_votes == 10
        assert score.passes_all is True

    def test_evaluate_returns_none_on_exception(self):
        mock_evaluator = Mock()
        mock_evaluator.evaluate.side_effect = RuntimeError("LLM down")
        strategy = ConsensusStrategy(evaluator=mock_evaluator)
        result = strategy.evaluate("AAPL")
        assert result is None


# ===========================================================================
# 4. BuySpecialist
# ===========================================================================


class TestBuySpecialist:
    """Test buy execution, position sizing, and limits."""

    def test_successful_buy_sets_entry_fields(self):
        buy = BuySpecialist(max_positions=10, max_position_pct=0.1)
        entry = PipelineEntry(symbol="AAPL")
        price = Decimal("150.00")
        capital = Decimal("100000")
        success = buy.execute(entry, price, capital)
        assert success is True
        assert entry.buy_price == price
        assert entry.current_price == price
        # position_budget = 100000 * 0.1 = 10000; 10000 / 150 = 66
        assert entry.buy_quantity == 66
        assert buy.open_positions == 1

    def test_max_positions_limit_blocks_buy(self):
        buy = BuySpecialist(max_positions=1, max_position_pct=0.1)
        entry1 = PipelineEntry(symbol="AAPL")
        buy.execute(entry1, Decimal("100"), Decimal("100000"))
        assert buy.open_positions == 1

        entry2 = PipelineEntry(symbol="GOOG")
        success = buy.execute(entry2, Decimal("100"), Decimal("100000"))
        assert success is False
        assert entry2.buy_price is None
        assert buy.open_positions == 1

    def test_calculate_quantity_with_valid_values(self):
        buy = BuySpecialist(max_position_pct=0.2)
        qty = buy.calculate_quantity(Decimal("50"), Decimal("10000"))
        # 10000 * 0.2 = 2000; 2000 / 50 = 40
        assert qty == 40

    def test_calculate_quantity_zero_price_returns_zero(self):
        buy = BuySpecialist()
        qty = buy.calculate_quantity(Decimal("0"), Decimal("100000"))
        assert qty == 0

    def test_calculate_quantity_negative_price_returns_zero(self):
        buy = BuySpecialist()
        qty = buy.calculate_quantity(Decimal("-10"), Decimal("100000"))
        assert qty == 0

    def test_release_position_decrements_counter(self):
        buy = BuySpecialist(max_positions=10)
        entry = PipelineEntry(symbol="AAPL")
        buy.execute(entry, Decimal("100"), Decimal("100000"))
        assert buy.open_positions == 1
        buy.release_position()
        assert buy.open_positions == 0

    def test_release_position_does_not_go_below_zero(self):
        buy = BuySpecialist()
        buy.release_position()
        assert buy.open_positions == 0

    def test_buy_fails_when_quantity_is_zero(self):
        buy = BuySpecialist(max_positions=10, max_position_pct=0.01)
        entry = PipelineEntry(symbol="BRK")
        # price so high that quantity = 0
        success = buy.execute(entry, Decimal("500000"), Decimal("1000"))
        assert success is False


# ===========================================================================
# 5. SellSpecialist
# ===========================================================================


class TestSellSpecialist:
    """Test sell execution and validation."""

    def test_successful_sell_updates_entry(self):
        sell = SellSpecialist()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 50
        success = sell.execute(entry, "TAKE_PROFIT", Decimal("120"))
        assert success is True
        assert entry.current_price == Decimal("120")
        # PnL = (120 - 100) * 50 = 1000
        assert entry.unrealized_pnl == Decimal("1000")
        assert entry.error_message == "TAKE_PROFIT"

    def test_sell_fails_when_buy_price_is_none(self):
        sell = SellSpecialist()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_quantity = 50
        success = sell.execute(entry, "STOP_LOSS", Decimal("90"))
        assert success is False

    def test_sell_fails_when_buy_quantity_is_none(self):
        sell = SellSpecialist()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        success = sell.execute(entry, "STOP_LOSS", Decimal("90"))
        assert success is False

    def test_sell_fails_when_buy_quantity_is_zero(self):
        sell = SellSpecialist()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 0
        success = sell.execute(entry, "STOP_LOSS", Decimal("90"))
        assert success is False

    def test_sell_records_negative_pnl(self):
        sell = SellSpecialist()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        sell.execute(entry, "STOP_LOSS", Decimal("80"))
        # (80 - 100) * 10 = -200
        assert entry.unrealized_pnl == Decimal("-200")


# ===========================================================================
# 6. PositionMonitor
# ===========================================================================


class TestPositionMonitor:
    """Test exit signal detection."""

    def test_stop_loss_triggers_below_threshold(self):
        monitor = PositionMonitor(stop_loss_pct=0.07)
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        # Stop loss at 100 * (1 - 0.07) = 93. Price 92 triggers.
        result = monitor.check(entry, Decimal("92"))
        assert result == "STOP_LOSS"

    def test_take_profit_triggers_above_threshold(self):
        monitor = PositionMonitor(take_profit_pct=0.20)
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        # Take profit at 100 * 1.20 = 120. Price 121 triggers.
        result = monitor.check(entry, Decimal("121"))
        assert result == "TAKE_PROFIT"

    def test_trailing_stop_ratchets_up_and_triggers(self):
        monitor = PositionMonitor(
            stop_loss_pct=0.50,
            take_profit_pct=0.90,
            trailing_stop_pct=0.05,
        )
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10

        # Price rises to 115, trailing stop = 115 * 0.95 = 109.25
        result = monitor.check(entry, Decimal("115"))
        assert result is None
        assert entry.trailing_stop == Decimal("115") * Decimal("0.95")

        # Price rises to 120, trailing stop ratchets to 120 * 0.95 = 114
        result = monitor.check(entry, Decimal("120"))
        assert result is None
        assert entry.trailing_stop == Decimal("120") * Decimal("0.95")

        # Price drops to 113 < 114 trailing stop -> triggers
        result = monitor.check(entry, Decimal("113"))
        assert result == "TRAILING_STOP"

    def test_trailing_stop_never_decreases(self):
        monitor = PositionMonitor(
            stop_loss_pct=0.50,
            take_profit_pct=0.90,
            trailing_stop_pct=0.05,
        )
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10

        monitor.check(entry, Decimal("120"))
        high_stop = entry.trailing_stop
        monitor.check(entry, Decimal("110"))
        # Stop should not decrease
        assert entry.trailing_stop >= high_stop

    def test_max_holding_triggers_after_max_days(self):
        monitor = PositionMonitor(
            stop_loss_pct=0.50,
            take_profit_pct=0.90,
            trailing_stop_pct=0.50,
            max_holding_days=30,
        )
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        # Set entered_at to 31 days ago
        entry.entered_at = datetime.now() - timedelta(days=31)
        result = monitor.check(entry, Decimal("100"))
        assert result == "MAX_HOLDING"

    def test_returns_none_when_no_exit_signal(self):
        monitor = PositionMonitor()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        # Price within safe range
        result = monitor.check(entry, Decimal("105"))
        assert result is None

    def test_none_buy_price_returns_none(self):
        monitor = PositionMonitor()
        entry = PipelineEntry(symbol="AAPL")
        result = monitor.check(entry, Decimal("100"))
        assert result is None

    def test_updates_current_price_and_pnl(self):
        monitor = PositionMonitor()
        entry = PipelineEntry(symbol="AAPL")
        entry.buy_price = Decimal("100")
        entry.buy_quantity = 10
        monitor.check(entry, Decimal("110"))
        assert entry.current_price == Decimal("110")
        assert entry.unrealized_pnl == Decimal("100")  # (110-100)*10


# ===========================================================================
# 7. TradingPipelineRunner
# ===========================================================================


class TestTradingPipelineRunner:
    """Test pipeline runner state machine orchestration."""

    def _make_runner(self, strategy=None, buy=None, sell=None, monitor=None, logger=None):
        return TradingPipelineRunner(
            consensus_strategy=strategy or Mock(),
            buy_specialist=buy or BuySpecialist(),
            sell_specialist=sell or SellSpecialist(),
            monitor=monitor or PositionMonitor(),
            pipeline_logger=logger,
        )

    def test_add_to_watchlist_adds_entries(self):
        runner = self._make_runner()
        runner.add_to_watchlist(["AAPL", "GOOG"])
        assert "AAPL" in runner.entries
        assert "GOOG" in runner.entries
        assert runner.entries["AAPL"].state == PipelineState.WATCHLIST

    def test_add_to_watchlist_skips_duplicates(self):
        runner = self._make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.add_to_watchlist(["AAPL", "GOOG"])
        assert len(runner.entries) == 2

    def test_run_cycle_watchlist_to_screening(self):
        runner = self._make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()
        assert runner.entries["AAPL"].state == PipelineState.SCREENING

    def test_run_cycle_screening_to_evaluating(self):
        runner = self._make_runner()
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # WATCHLIST -> SCREENING
        runner.run_cycle()  # SCREENING -> EVALUATING
        assert runner.entries["AAPL"].state == PipelineState.EVALUATING

    def test_evaluating_approved_consensus(self):
        mock_strategy = Mock()
        cr = _make_consensus_result(passes=True, buy_count=8)
        mock_strategy.evaluate.return_value = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=8, total_votes=10, avg_conviction=0.8
        )
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_APPROVED
        assert runner.entries["AAPL"].state == PipelineState.CONSENSUS_APPROVED

    def test_evaluating_rejected_consensus(self):
        mock_strategy = Mock()
        cr = _make_consensus_result(passes=False, buy_count=2)
        mock_strategy.evaluate.return_value = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=2, total_votes=10, avg_conviction=0.3
        )
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_REJECTED
        assert runner.entries["AAPL"].state == PipelineState.CONSENSUS_REJECTED

    def test_consensus_rejected_returns_to_watchlist(self):
        mock_strategy = Mock()
        cr = _make_consensus_result(passes=False)
        mock_strategy.evaluate.return_value = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=2, total_votes=10, avg_conviction=0.3
        )
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_REJECTED
        runner.run_cycle()  # -> WATCHLIST
        assert runner.entries["AAPL"].state == PipelineState.WATCHLIST

    def test_buy_pending_with_valid_price_to_bought(self):
        mock_strategy = Mock()
        cr = _make_consensus_result(passes=True)
        mock_strategy.evaluate.return_value = ConsensusScore(
            symbol="AAPL", consensus_result=cr, buy_count=8, total_votes=10, avg_conviction=0.8
        )
        buy = BuySpecialist(max_positions=10, max_position_pct=0.1)
        runner = self._make_runner(strategy=mock_strategy, buy=buy)
        runner.add_to_watchlist(["AAPL"])

        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> CONSENSUS_APPROVED

        # Set current_price for buy execution
        runner.entries["AAPL"].current_price = Decimal("150")
        runner.run_cycle()  # -> BUY_PENDING
        runner.run_cycle()  # -> BOUGHT (buy executes)
        assert runner.entries["AAPL"].state == PipelineState.BOUGHT

    def test_error_handling_transitions_to_error(self):
        mock_strategy = Mock()
        mock_strategy.evaluate.side_effect = RuntimeError("boom")
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # evaluate raises -> ERROR
        assert runner.entries["AAPL"].state == PipelineState.ERROR

    def test_error_recovery_to_watchlist(self):
        mock_strategy = Mock()
        mock_strategy.evaluate.side_effect = RuntimeError("boom")
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # -> ERROR
        assert runner.entries["AAPL"].state == PipelineState.ERROR
        runner.run_cycle()  # -> WATCHLIST (recovery)
        assert runner.entries["AAPL"].state == PipelineState.WATCHLIST

    def test_entries_property_returns_snapshot(self):
        runner = self._make_runner()
        runner.add_to_watchlist(["AAPL"])
        snapshot = runner.entries
        assert isinstance(snapshot, dict)
        assert "AAPL" in snapshot
        # Modify snapshot, original should be unchanged
        snapshot["NEW"] = PipelineEntry(symbol="NEW")
        assert "NEW" not in runner.entries

    def test_evaluating_with_none_score(self):
        mock_strategy = Mock()
        mock_strategy.evaluate.return_value = None
        runner = self._make_runner(strategy=mock_strategy)
        runner.add_to_watchlist(["AAPL"])
        runner.run_cycle()  # -> SCREENING
        runner.run_cycle()  # -> EVALUATING
        runner.run_cycle()  # evaluate returns None -> CONSENSUS_REJECTED
        assert runner.entries["AAPL"].state == PipelineState.CONSENSUS_REJECTED


# ===========================================================================
# 8. ConsensusEvaluator
# ===========================================================================


class TestConsensusEvaluator:
    """Test parallel persona evaluation orchestration."""

    def test_evaluate_runs_all_personas(self):
        persona1 = Mock(spec=InvestorPersona)
        persona1.name = "Buffett"
        persona1.category = PersonaCategory.VALUE
        persona1.evaluate.return_value = _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE, "Buffett")

        persona2 = Mock(spec=InvestorPersona)
        persona2.name = "Soros"
        persona2.category = PersonaCategory.MACRO
        persona2.evaluate.return_value = _make_vote(VoteAction.HOLD, 0.5, PersonaCategory.MACRO, "Soros")

        fetcher = Mock()
        fetcher.fetch_snapshot.return_value = _make_snapshot("005930")

        aggregator = VoteAggregator(threshold=1, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=1)
        evaluator = ConsensusEvaluator(
            personas=[persona1, persona2],
            advisory=None,
            fetcher=fetcher,
            aggregator=aggregator,
            max_workers=2,
        )
        result = evaluator.evaluate("005930")
        assert result.symbol == "005930"
        assert result.buy_count == 1
        assert result.hold_count == 1
        persona1.evaluate.assert_called_once()
        persona2.evaluate.assert_called_once()

    def test_failed_persona_records_abstain(self):
        persona1 = Mock(spec=InvestorPersona)
        persona1.name = "Failing"
        persona1.category = PersonaCategory.VALUE
        persona1.evaluate.side_effect = RuntimeError("timeout")

        fetcher = Mock()
        fetcher.fetch_snapshot.return_value = _make_snapshot()

        aggregator = VoteAggregator(threshold=1, quorum_pct=0.0, min_conviction=0.0, min_category_diversity=1)
        evaluator = ConsensusEvaluator(
            personas=[persona1],
            advisory=None,
            fetcher=fetcher,
            aggregator=aggregator,
        )
        result = evaluator.evaluate("005930")
        assert result.abstain_count == 1
        assert result.buy_count == 0

    def test_advisory_vote_collected(self):
        persona1 = Mock(spec=InvestorPersona)
        persona1.name = "Buffett"
        persona1.category = PersonaCategory.VALUE
        persona1.evaluate.return_value = _make_vote(VoteAction.BUY, 0.8, PersonaCategory.VALUE, "Buffett")

        advisory = Mock()
        advisory.evaluate.return_value = AdvisoryVote(
            persona_name="Wood",
            action=VoteAction.ADVISORY,
            innovation_score=0.9,
            disruption_assessment="High potential",
            category=PersonaCategory.INNOVATION,
        )

        fetcher = Mock()
        fetcher.fetch_snapshot.return_value = _make_snapshot()

        aggregator = VoteAggregator(threshold=1, quorum_pct=0.5, min_conviction=0.0, min_category_diversity=1)
        evaluator = ConsensusEvaluator(
            personas=[persona1],
            advisory=advisory,
            fetcher=fetcher,
            aggregator=aggregator,
        )
        result = evaluator.evaluate("005930")
        assert result.advisory_vote is not None
        assert result.advisory_vote.innovation_score == 0.9

    def test_result_symbol_is_set(self):
        fetcher = Mock()
        fetcher.fetch_snapshot.return_value = _make_snapshot("TSLA")

        aggregator = VoteAggregator()
        evaluator = ConsensusEvaluator(
            personas=[],
            advisory=None,
            fetcher=fetcher,
            aggregator=aggregator,
        )
        result = evaluator.evaluate("TSLA")
        assert result.symbol == "TSLA"


# ===========================================================================
# 9. CircuitBreaker
# ===========================================================================


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_closed_allows_requests(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_sec=60.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_transitions_to_open_after_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_sec=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_requests(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_sec=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is False

    def test_half_open_allows_one_request(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_sec=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_success_in_half_open_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_sec=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_in_half_open_returns_to_open(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


# ===========================================================================
# 10. VoteParser
# ===========================================================================


class TestVoteParser:
    """Test parsing LLM text responses into PersonaVote."""

    def test_parse_valid_buy_response(self):
        response = "ACTION: BUY\nCONVICTION: 0.85\nREASONING: Strong fundamentals"
        vote = VoteParser.parse(response, "Buffett", PersonaCategory.VALUE)
        assert vote.action == VoteAction.BUY
        assert vote.conviction == 0.85
        assert "Strong fundamentals" in vote.reasoning

    def test_parse_valid_sell_response(self):
        response = "ACTION: SELL\nCONVICTION: 0.9\nREASONING: Overvalued"
        vote = VoteParser.parse(response, "Soros", PersonaCategory.MACRO)
        assert vote.action == VoteAction.SELL
        assert vote.conviction == 0.9

    def test_parse_valid_hold_response(self):
        response = "ACTION: HOLD\nCONVICTION: 0.5\nREASONING: Wait for data"
        vote = VoteParser.parse(response, "Lynch", PersonaCategory.GROWTH)
        assert vote.action == VoteAction.HOLD

    def test_default_to_abstain_on_empty_input(self):
        vote = VoteParser.parse("", "Test", PersonaCategory.VALUE)
        assert vote.action == VoteAction.ABSTAIN
        assert vote.conviction == 0.0

    def test_default_to_abstain_on_unparseable_input(self):
        vote = VoteParser.parse("random gibberish without keywords", "Test", PersonaCategory.VALUE)
        assert vote.action == VoteAction.ABSTAIN

    def test_conviction_clamped_to_max_1(self):
        response = "ACTION: BUY\nCONVICTION: 5.0\nREASONING: Very confident"
        vote = VoteParser.parse(response, "Test", PersonaCategory.VALUE)
        assert vote.conviction == 1.0

    def test_conviction_clamped_to_min_0(self):
        response = "ACTION: BUY\nCONVICTION: -0.5\nREASONING: Negative test"
        vote = VoteParser.parse(response, "Test", PersonaCategory.VALUE)
        # Regex won't match negative, so defaults to 0.0
        assert vote.conviction == 0.0

    def test_korean_buy_keyword(self):
        response = "ACTION: 매수\nCONVICTION: 0.7\nREASONING: 좋은 기업"
        vote = VoteParser.parse(response, "Korean", PersonaCategory.VALUE)
        assert vote.action == VoteAction.BUY

    def test_korean_sell_keyword(self):
        response = "행동: 매도\n확신도: 0.6\n분석: 고평가"
        vote = VoteParser.parse(response, "Korean", PersonaCategory.MACRO)
        assert vote.action == VoteAction.SELL
        assert vote.conviction == 0.6


# ===========================================================================
# 11. HybridPersona
# ===========================================================================


class TestHybridPersona:
    """Test HybridPersona 2-stage evaluation."""

    def _make_hybrid(self, cb=None, llm_config=None, counter=None):
        """Create a concrete HybridPersona subclass for testing."""
        from stock_manager.trading.personas.hybrid import HybridPersona

        class ConcreteHybrid(HybridPersona):
            name = "TestHybrid"
            category = PersonaCategory.VALUE

            def screen_rule(self, snapshot):
                return _make_vote(VoteAction.BUY, 0.7, PersonaCategory.VALUE, "TestHybrid")

            def should_trigger_llm(self, vote):
                return True

        return ConcreteHybrid(
            circuit_breaker=cb or CircuitBreaker(failure_threshold=5, cooldown_sec=60.0),
            llm_config=llm_config or LLMConfig(),
            invocation_counter=counter,
        )

    def _make_hybrid_no_llm(self, cb=None):
        """Create a HybridPersona that does not trigger LLM."""
        from stock_manager.trading.personas.hybrid import HybridPersona

        class ConcreteNoLLM(HybridPersona):
            name = "NoLLM"
            category = PersonaCategory.GROWTH

            def screen_rule(self, snapshot):
                return _make_vote(VoteAction.HOLD, 0.5, PersonaCategory.GROWTH, "NoLLM")

            def should_trigger_llm(self, vote):
                return False

        return ConcreteNoLLM(
            circuit_breaker=cb or CircuitBreaker(failure_threshold=5, cooldown_sec=60.0),
        )

    def test_evaluate_returns_rule_vote_when_no_llm_trigger(self):
        persona = self._make_hybrid_no_llm()
        snapshot = _make_snapshot()
        vote = persona.evaluate(snapshot)
        assert vote.action == VoteAction.HOLD
        assert vote.persona_name == "NoLLM"

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_evaluate_with_llm_agreement_boosts_conviction(self, mock_prompt, mock_query):
        mock_prompt.return_value = "System prompt"
        mock_query.return_value = "ACTION: BUY\nCONVICTION: 0.8\nREASONING: Agree with rule"
        persona = self._make_hybrid()
        snapshot = _make_snapshot()
        vote = persona.evaluate(snapshot)
        # Rule conviction 0.7 + 0.1 = 0.8
        assert vote.action == VoteAction.BUY
        assert abs(vote.conviction - 0.8) < 1e-9
        assert "[Hybrid]" in vote.reasoning

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_evaluate_with_llm_disagreement_uses_llm_action(self, mock_prompt, mock_query):
        mock_prompt.return_value = "System prompt"
        mock_query.return_value = "ACTION: SELL\nCONVICTION: 0.6\nREASONING: Overpriced"
        persona = self._make_hybrid()
        snapshot = _make_snapshot()
        vote = persona.evaluate(snapshot)
        # LLM says SELL, rule said BUY
        assert vote.action == VoteAction.SELL
        # min(0.6, 0.7) * 0.8 = 0.48
        assert abs(vote.conviction - 0.48) < 0.01
        assert "LLM override" in vote.reasoning

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_screen_llm_falls_back_when_circuit_breaker_open(self, mock_prompt, mock_query):
        cb = CircuitBreaker(failure_threshold=1, cooldown_sec=60.0)
        cb.record_failure()  # trips to OPEN
        persona = self._make_hybrid(cb=cb)
        snapshot = _make_snapshot()
        rule_vote = persona.screen_rule(snapshot)
        result = persona.screen_llm(snapshot, rule_vote)
        assert result is rule_vote
        mock_query.assert_not_called()

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_screen_llm_falls_back_when_invocation_limit_reached(self, mock_prompt, mock_query):
        counter = InvocationCounter()
        # Simulate limit reached
        config = LLMConfig(daily_invocation_limit=2)
        counter.increment()
        counter.increment()
        persona = self._make_hybrid(llm_config=config, counter=counter)
        snapshot = _make_snapshot()
        rule_vote = persona.screen_rule(snapshot)
        result = persona.screen_llm(snapshot, rule_vote)
        assert result is rule_vote
        mock_query.assert_not_called()

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_screen_llm_falls_back_on_query_exception(self, mock_prompt, mock_query):
        mock_prompt.return_value = "System prompt"
        mock_query.side_effect = RuntimeError("LLM unavailable")
        persona = self._make_hybrid()
        snapshot = _make_snapshot()
        rule_vote = persona.screen_rule(snapshot)
        result = persona.screen_llm(snapshot, rule_vote)
        assert result is rule_vote

    @patch("stock_manager.trading.personas.hybrid.sync_persona_query")
    @patch("stock_manager.trading.personas.hybrid.load_persona_prompt")
    def test_screen_llm_falls_back_on_none_response(self, mock_prompt, mock_query):
        mock_prompt.return_value = "System prompt"
        mock_query.return_value = None
        persona = self._make_hybrid()
        snapshot = _make_snapshot()
        rule_vote = persona.screen_rule(snapshot)
        result = persona.screen_llm(snapshot, rule_vote)
        assert result is rule_vote


# ===========================================================================
# 12. PipelineJsonLogger
# ===========================================================================


class TestPipelineJsonLogger:
    """Test NDJSON pipeline logging."""

    def test_log_state_change_writes_valid_ndjson(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            logger.log_state_change("AAPL", "WATCHLIST", "SCREENING", "starting")

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            assert filepath.exists()

            with open(filepath) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["event"] == "state_change"
                assert data["symbol"] == "AAPL"
                assert data["from_state"] == "WATCHLIST"
                assert data["to_state"] == "SCREENING"
                assert data["reason"] == "starting"
                assert "timestamp" in data
                assert "session_id" in data

    def test_log_buy_decision_writes_correct_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            logger.log_buy_decision(
                symbol="AAPL",
                price=Decimal("150.50"),
                quantity=100,
                order_type="MARKET",
                stop_loss=Decimal("140.00"),
            )

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            with open(filepath) as f:
                data = json.loads(f.readline())
                assert data["event"] == "buy_decision"
                assert data["symbol"] == "AAPL"
                assert data["price"] == "150.50"
                assert data["quantity"] == 100
                assert data["order_type"] == "MARKET"
                assert data["stop_loss"] == "140.00"

    def test_daily_rotation_creates_correct_filename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir), prefix="trading")
            logger.log_state_change("TEST", "A", "B", "test")

            today = datetime.now().strftime("%Y%m%d")
            expected = Path(tmp_dir) / f"trading-{today}.ndjson"
            assert expected.exists()

    def test_thread_safety_rlock_usage(self):
        """Verify multiple writes from same thread don't deadlock (RLock)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            # Multiple writes in sequence from same thread
            for i in range(10):
                logger.log_state_change(f"SYM{i}", "A", "B", f"reason{i}")

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            with open(filepath) as f:
                lines = f.readlines()
                assert len(lines) == 10

    def test_log_error_writes_error_event(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            logger.log_error("AAPL", RuntimeError("test error"), {"state": "EVALUATING"})

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            with open(filepath) as f:
                data = json.loads(f.readline())
                assert data["event"] == "error"
                assert data["error_type"] == "RuntimeError"
                assert data["error_message"] == "test error"
                assert data["context"]["state"] == "EVALUATING"

    def test_log_consensus_result_writes_event(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            logger.log_consensus_result(
                symbol="GOOG",
                passed=True,
                buy_count=8,
                total_count=10,
                avg_conviction=0.75,
                categories={"value": 3, "growth": 2},
            )

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            with open(filepath) as f:
                data = json.loads(f.readline())
                assert data["event"] == "consensus_result"
                assert data["passed"] is True
                assert data["buy_count"] == 8

    def test_log_trade_complete_writes_event(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = PipelineJsonLogger(log_dir=Path(tmp_dir))
            logger.log_trade_complete(
                symbol="AAPL",
                entry_price=Decimal("100"),
                exit_price=Decimal("120"),
                pnl=Decimal("2000"),
                holding_days=45,
                return_pct=20.0,
            )

            today = datetime.now().strftime("%Y%m%d")
            filepath = Path(tmp_dir) / f"pipeline-{today}.ndjson"
            with open(filepath) as f:
                data = json.loads(f.readline())
                assert data["event"] == "trade_complete"
                assert data["holding_days"] == 45
                assert data["return_pct"] == 20.0
