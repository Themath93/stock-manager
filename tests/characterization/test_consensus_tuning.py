"""Tests for consensus gate tuning and A/B comparison."""

from stock_manager.trading.consensus.aggregator import VoteAggregator
from stock_manager.trading.consensus.ab_comparison import compare_configs
from stock_manager.trading.personas.models import PersonaVote, VoteAction, PersonaCategory


def _make_buy_vote(name: str, category: PersonaCategory, conviction: float = 0.7) -> PersonaVote:
    return PersonaVote(
        persona_name=name, action=VoteAction.BUY, conviction=conviction,
        reasoning="test", criteria_met={}, category=category,
    )


def _make_sell_vote(name: str, category: PersonaCategory) -> PersonaVote:
    return PersonaVote(
        persona_name=name, action=VoteAction.SELL, conviction=0.5,
        reasoning="test", criteria_met={}, category=category,
    )


class TestAggregatorDefaults:
    def test_new_defaults(self):
        agg = VoteAggregator()
        assert agg.threshold == 6
        assert agg.quorum_pct == 0.70
        assert agg.min_conviction == 0.60
        assert agg.min_category_diversity == 3


class TestABComparison:
    def test_compare_old_vs_new(self):
        old = VoteAggregator(threshold=7, quorum_pct=0.6, min_conviction=0.5, min_category_diversity=2)
        new = VoteAggregator()  # New defaults

        # 6 BUY votes from 3 categories
        votes = [
            _make_buy_vote("Graham", PersonaCategory.VALUE),
            _make_buy_vote("Buffett", PersonaCategory.VALUE),
            _make_buy_vote("Templeton", PersonaCategory.VALUE),
            _make_buy_vote("Lynch", PersonaCategory.GROWTH),
            _make_buy_vote("Fisher", PersonaCategory.GROWTH),
            _make_buy_vote("Dalio", PersonaCategory.QUANTITATIVE),
            _make_sell_vote("Simons", PersonaCategory.QUANTITATIVE),
            _make_sell_vote("Soros", PersonaCategory.MOMENTUM),
            _make_sell_vote("Livermore", PersonaCategory.MOMENTUM),
            _make_sell_vote("Munger", PersonaCategory.VALUE),
        ]

        result = compare_configs(votes, old, new)
        # Old config needs 7 BUY → fails (only 6)
        assert result.result_a.passes_threshold is False
        # New config needs 6 BUY → check other gates
        assert result.only_b_passes or result.neither_passes
        assert isinstance(result.summary(), str)
