"""Consensus-based trading strategy (Strategy adapter for the consensus pipeline).

Wraps ConsensusEvaluator behind the Strategy / StrategyScore interface so the
screening engine can treat consensus voting like any other strategy.

The base ``Strategy.screen()`` method handles iteration and filtering --
this class only implements ``evaluate()`` for a single symbol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from stock_manager.trading.consensus.evaluator import ConsensusEvaluator
from stock_manager.trading.personas.models import ConsensusResult
from stock_manager.trading.strategies.base import Strategy, StrategyScore


@dataclass
class ConsensusScore(StrategyScore):
    """Score produced by the consensus voting pipeline.

    Attributes:
        symbol: Stock symbol evaluated.
        consensus_result: Full ConsensusResult with votes and metadata.
        buy_count: Number of BUY votes received.
        total_votes: Total number of binding votes cast.
        avg_conviction: Average conviction among BUY voters (0.0-1.0).
    """

    consensus_result: ConsensusResult
    buy_count: int
    total_votes: int
    avg_conviction: float

    @property
    def passes_all(self) -> bool:
        """Whether the consensus pipeline approved this symbol."""
        return self.consensus_result.passes_threshold

    @property
    def criteria_passed(self) -> int:
        """Number of BUY votes (used as the criteria-passed count)."""
        return self.buy_count


class ConsensusStrategy(Strategy):
    """Strategy adapter that delegates to ConsensusEvaluator.

    The screening engine calls ``evaluate(symbol)`` for each candidate and
    uses the inherited ``screen()`` to filter by ``passes_all``.

    Args:
        evaluator: Fully configured ConsensusEvaluator instance.
    """

    def __init__(self, evaluator: ConsensusEvaluator) -> None:
        self.evaluator = evaluator

    def evaluate(self, symbol: str) -> Optional[ConsensusScore]:
        """Evaluate a single symbol through the consensus pipeline.

        Args:
            symbol: Stock symbol to evaluate.

        Returns:
            ConsensusScore wrapping the full ConsensusResult,
            or None if evaluation fails entirely.
        """
        try:
            result = self.evaluator.evaluate(symbol)
        except Exception:
            return None

        total_votes = result.buy_count + result.sell_count + result.hold_count + result.abstain_count

        return ConsensusScore(
            symbol=symbol,
            consensus_result=result,
            buy_count=result.buy_count,
            total_votes=total_votes,
            avg_conviction=result.avg_conviction,
        )
