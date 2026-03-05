"""A/B comparison framework for consensus parameter tuning.

Runs two VoteAggregator configurations side-by-side on the same data
to compare pass rates, vote distributions, and conviction levels.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from stock_manager.trading.consensus.aggregator import VoteAggregator
from stock_manager.trading.personas.models import (
    AdvisoryVote,
    ConsensusResult,
    PersonaVote,
)


@dataclass(frozen=True)
class ABComparisonResult:
    """Side-by-side comparison of two aggregator configurations."""

    config_a_name: str
    config_b_name: str
    result_a: ConsensusResult
    result_b: ConsensusResult

    @property
    def both_pass(self) -> bool:
        return self.result_a.passes_threshold and self.result_b.passes_threshold

    @property
    def only_a_passes(self) -> bool:
        return self.result_a.passes_threshold and not self.result_b.passes_threshold

    @property
    def only_b_passes(self) -> bool:
        return not self.result_a.passes_threshold and self.result_b.passes_threshold

    @property
    def neither_passes(self) -> bool:
        return not self.result_a.passes_threshold and not self.result_b.passes_threshold

    @property
    def conviction_delta(self) -> float:
        """Difference in average conviction (B - A)."""
        return self.result_b.avg_conviction - self.result_a.avg_conviction

    def summary(self) -> str:
        """Human-readable comparison summary."""
        a = self.result_a
        b = self.result_b
        return (
            f"A ({self.config_a_name}): pass={a.passes_threshold} "
            f"buy={a.buy_count} conviction={a.avg_conviction:.2f} "
            f"diversity={a.category_diversity}\n"
            f"B ({self.config_b_name}): pass={b.passes_threshold} "
            f"buy={b.buy_count} conviction={b.avg_conviction:.2f} "
            f"diversity={b.category_diversity}"
        )


def compare_configs(
    votes: list[PersonaVote],
    config_a: VoteAggregator,
    config_b: VoteAggregator,
    config_a_name: str = "old",
    config_b_name: str = "new",
    advisory_vote: AdvisoryVote | None = None,
) -> ABComparisonResult:
    """Run two aggregator configs against the same votes.

    Args:
        votes: The persona votes to evaluate.
        config_a: First aggregator configuration (typically "old").
        config_b: Second aggregator configuration (typically "new").
        config_a_name: Label for config A.
        config_b_name: Label for config B.
        advisory_vote: Optional advisory vote (passed to both).

    Returns:
        ABComparisonResult with side-by-side results.
    """
    result_a = config_a.aggregate(votes, advisory_vote)
    result_b = config_b.aggregate(votes, advisory_vote)
    return ABComparisonResult(
        config_a_name=config_a_name,
        config_b_name=config_b_name,
        result_a=result_a,
        result_b=result_b,
    )
