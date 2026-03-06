"""Unit tests for consensus A/B comparison helpers."""

from __future__ import annotations

import pytest

from stock_manager.trading.consensus.ab_comparison import ABComparisonResult, compare_configs
from stock_manager.trading.consensus.aggregator import VoteAggregator
from stock_manager.trading.personas.models import (
    ConsensusResult,
    PersonaCategory,
    PersonaVote,
    VoteAction,
)


def _vote(
    *,
    action: VoteAction,
    conviction: float = 0.7,
    category: PersonaCategory = PersonaCategory.VALUE,
    name: str = "P",
) -> PersonaVote:
    return PersonaVote(
        persona_name=name,
        action=action,
        conviction=conviction,
        reasoning="test",
        criteria_met={},
        category=category,
    )


def _result(*, passes: bool, conviction: float) -> ConsensusResult:
    return ConsensusResult(
        symbol="005930",
        votes=[],
        advisory_vote=None,
        buy_count=7 if passes else 2,
        sell_count=1,
        hold_count=1,
        abstain_count=1,
        passes_threshold=passes,
        avg_conviction=conviction,
        category_diversity=3,
    )


def test_compare_configs_returns_side_by_side_summary() -> None:
    votes = [
        _vote(action=VoteAction.BUY, conviction=0.8, category=PersonaCategory.VALUE, name="A"),
        _vote(action=VoteAction.BUY, conviction=0.7, category=PersonaCategory.GROWTH, name="B"),
        _vote(action=VoteAction.BUY, conviction=0.6, category=PersonaCategory.MOMENTUM, name="C"),
        _vote(action=VoteAction.BUY, conviction=0.9, category=PersonaCategory.MACRO, name="D"),
        _vote(action=VoteAction.BUY, conviction=0.65, category=PersonaCategory.QUANTITATIVE, name="E"),
        _vote(action=VoteAction.BUY, conviction=0.75, category=PersonaCategory.VALUE, name="F"),
        _vote(action=VoteAction.BUY, conviction=0.8, category=PersonaCategory.GROWTH, name="G"),
    ]

    strict = VoteAggregator(threshold=8, quorum_pct=0.5, min_conviction=0.6, min_category_diversity=3)
    relaxed = VoteAggregator(threshold=6, quorum_pct=0.5, min_conviction=0.5, min_category_diversity=2)

    result = compare_configs(
        votes=votes,
        config_a=strict,
        config_b=relaxed,
        config_a_name="strict",
        config_b_name="relaxed",
    )

    assert result.config_a_name == "strict"
    assert result.config_b_name == "relaxed"
    assert result.only_b_passes is True
    assert "A (strict)" in result.summary()
    assert "B (relaxed)" in result.summary()


def test_ab_comparison_result_pass_state_properties() -> None:
    both = ABComparisonResult("a", "b", _result(passes=True, conviction=0.6), _result(passes=True, conviction=0.7))
    only_a = ABComparisonResult("a", "b", _result(passes=True, conviction=0.6), _result(passes=False, conviction=0.5))
    only_b = ABComparisonResult("a", "b", _result(passes=False, conviction=0.6), _result(passes=True, conviction=0.8))
    neither = ABComparisonResult("a", "b", _result(passes=False, conviction=0.6), _result(passes=False, conviction=0.4))

    assert both.both_pass is True
    assert only_a.only_a_passes is True
    assert only_b.only_b_passes is True
    assert neither.neither_passes is True


def test_ab_comparison_conviction_delta() -> None:
    result = ABComparisonResult(
        config_a_name="old",
        config_b_name="new",
        result_a=_result(passes=True, conviction=0.55),
        result_b=_result(passes=True, conviction=0.72),
    )

    assert result.conviction_delta == pytest.approx(0.17)
