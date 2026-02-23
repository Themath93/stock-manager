"""Vote aggregation logic for the consensus trading pipeline.

Counts votes from the 10 binding investor personas, checks quorum,
threshold, conviction, and category diversity to produce a ConsensusResult.
Advisory votes (Wood) are stored but excluded from all binding checks.
"""

from __future__ import annotations

import logging

from stock_manager.trading.personas.models import (
    AdvisoryVote,
    ConsensusResult,
    PersonaCategory,
    PersonaVote,
    VoteAction,
)

logger = logging.getLogger(__name__)


class VoteAggregator:
    """Aggregates PersonaVote instances into a single ConsensusResult.

    Decision criteria (all must pass for ``passes_threshold=True``):
        1. **Quorum** -- enough personas voted (non-abstain / total >= quorum_pct).
        2. **Threshold** -- at least *threshold* BUY votes.
        3. **Conviction** -- average conviction among BUY voters >= min_conviction.
        4. **Diversity** -- BUY votes span >= min_category_diversity distinct
           PersonaCategory values.

    Advisory votes are recorded in the result for logging but never
    participate in any of the four checks above.

    Args:
        threshold: Minimum BUY vote count required.
        quorum_pct: Fraction of non-abstain voters required (0.0-1.0).
        min_conviction: Minimum average conviction among BUY voters (0.0-1.0).
        min_category_diversity: Minimum distinct PersonaCategory values among
            BUY voters.
    """

    def __init__(
        self,
        threshold: int = 7,
        quorum_pct: float = 0.6,
        min_conviction: float = 0.5,
        min_category_diversity: int = 2,
    ) -> None:
        self.threshold = threshold
        self.quorum_pct = quorum_pct
        self.min_conviction = min_conviction
        self.min_category_diversity = min_category_diversity

    def aggregate(
        self,
        votes: list[PersonaVote],
        advisory_vote: AdvisoryVote | None = None,
    ) -> ConsensusResult:
        """Aggregate persona votes into a consensus decision.

        Args:
            votes: Binding votes from the 10 investor personas.
            advisory_vote: Optional non-binding advisory vote (Wood).

        Returns:
            A fully populated ConsensusResult.
        """
        total = len(votes)

        if total == 0:
            logger.warning("No votes to aggregate")
            return ConsensusResult(
                symbol="",
                votes=votes,
                advisory_vote=advisory_vote,
                buy_count=0,
                sell_count=0,
                hold_count=0,
                abstain_count=0,
                passes_threshold=False,
                avg_conviction=0.0,
                category_diversity=0,
            )

        symbol = votes[0].symbol if hasattr(votes[0], "symbol") else ""

        # --- Count by action ---
        buy_count = sum(1 for v in votes if v.action == VoteAction.BUY)
        sell_count = sum(1 for v in votes if v.action == VoteAction.SELL)
        hold_count = sum(1 for v in votes if v.action == VoteAction.HOLD)
        abstain_count = sum(1 for v in votes if v.action == VoteAction.ABSTAIN)

        # --- 1. Quorum check: sufficient non-abstain participation ---
        active_voters = total - abstain_count
        quorum_met = (active_voters / total) >= self.quorum_pct if total > 0 else False

        # --- 2. Threshold check: enough BUY votes ---
        threshold_met = buy_count >= self.threshold

        # --- 3. Conviction check: average conviction among BUY voters ---
        buy_votes = [v for v in votes if v.action == VoteAction.BUY]
        if buy_votes:
            avg_conviction = sum(v.conviction for v in buy_votes) / len(buy_votes)
        else:
            avg_conviction = 0.0
        conviction_met = avg_conviction >= self.min_conviction

        # --- 4. Diversity check: distinct categories among BUY voters ---
        buy_categories: set[PersonaCategory] = {v.category for v in buy_votes}
        category_diversity = len(buy_categories)
        diversity_met = category_diversity >= self.min_category_diversity

        # --- Final decision: all four gates must pass ---
        passes_threshold = (
            quorum_met and threshold_met and conviction_met and diversity_met
        )

        logger.debug(
            "Aggregation: buy=%d sell=%d hold=%d abstain=%d | "
            "quorum=%s threshold=%s conviction=%.2f(%s) diversity=%d(%s) => %s",
            buy_count,
            sell_count,
            hold_count,
            abstain_count,
            quorum_met,
            threshold_met,
            avg_conviction,
            conviction_met,
            category_diversity,
            diversity_met,
            passes_threshold,
        )

        return ConsensusResult(
            symbol=symbol,
            votes=votes,
            advisory_vote=advisory_vote,
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            abstain_count=abstain_count,
            passes_threshold=passes_threshold,
            avg_conviction=round(avg_conviction, 4),
            category_diversity=category_diversity,
        )
