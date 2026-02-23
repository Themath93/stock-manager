"""Consensus evaluator: orchestrates parallel persona evaluation.

Fetches a MarketSnapshot for a symbol, fans out evaluation to all
investor personas (and the optional Wood advisory) via a thread pool,
collects votes, and delegates to VoteAggregator for the final decision.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from stock_manager.trading.consensus.aggregator import VoteAggregator
from stock_manager.trading.indicators.fetcher import TechnicalDataFetcher
from stock_manager.trading.personas.base import InvestorPersona
from stock_manager.trading.personas.models import (
    AdvisoryVote,
    ConsensusResult,
    PersonaVote,
    VoteAction,
)
from stock_manager.trading.personas.wood_advisory import WoodAdvisory

logger = logging.getLogger(__name__)

_PERSONA_TIMEOUT_SECONDS = 60


class ConsensusEvaluator:
    """Orchestrates parallel persona evaluation for a single symbol.

    Workflow:
        1. Fetch a ``MarketSnapshot`` via ``TechnicalDataFetcher``.
        2. Submit each persona's ``evaluate(snapshot)`` to a thread pool.
        3. Optionally submit the Wood advisory evaluation.
        4. Collect results (timeout per persona, ABSTAIN on failure).
        5. Delegate to ``VoteAggregator`` for the consensus decision.

    Thread safety: ``MarketSnapshot`` is frozen (immutable) and each persona's
    ``screen_rule`` is stateless, so concurrent reads are safe.

    Args:
        personas: The 10 binding investor personas.
        advisory: Optional Wood advisory persona (non-binding).
        fetcher: Data fetcher that produces MarketSnapshot instances.
        aggregator: Vote aggregator for the final decision.
        max_workers: Maximum thread pool size for parallel evaluation.
    """

    def __init__(
        self,
        personas: list[InvestorPersona],
        advisory: WoodAdvisory | None,
        fetcher: TechnicalDataFetcher,
        aggregator: VoteAggregator,
        max_workers: int = 5,
    ) -> None:
        self.personas = personas
        self.advisory = advisory
        self.fetcher = fetcher
        self.aggregator = aggregator
        self.max_workers = max_workers

    def evaluate(self, symbol: str) -> ConsensusResult:
        """Run the full consensus pipeline for a single symbol.

        Args:
            symbol: Stock symbol to evaluate (e.g. '005930').

        Returns:
            ConsensusResult with votes, counts, and pass/fail decision.
        """
        # 1. Fetch market data
        snapshot = self.fetcher.fetch_snapshot(symbol)

        votes: list[PersonaVote] = []
        advisory_vote: AdvisoryVote | None = None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 2. Submit persona evaluations
            persona_futures = {
                executor.submit(persona.evaluate, snapshot): persona
                for persona in self.personas
            }

            # 3. Submit advisory evaluation (if configured)
            advisory_future = None
            if self.advisory is not None:
                advisory_future = executor.submit(self.advisory.evaluate, snapshot)

            # 4. Collect persona votes
            for future in as_completed(
                persona_futures, timeout=_PERSONA_TIMEOUT_SECONDS
            ):
                persona = persona_futures[future]
                try:
                    vote = future.result(timeout=_PERSONA_TIMEOUT_SECONDS)
                    votes.append(vote)
                except Exception:
                    logger.warning(
                        "Persona %s failed for %s; recording ABSTAIN",
                        persona.name,
                        symbol,
                        exc_info=True,
                    )
                    votes.append(
                        PersonaVote(
                            persona_name=persona.name,
                            action=VoteAction.ABSTAIN,
                            conviction=0.0,
                            reasoning=f"Evaluation failed for {symbol}",
                            criteria_met={},
                            category=persona.category,
                        )
                    )

            # 5. Collect advisory vote
            if advisory_future is not None:
                try:
                    advisory_vote = advisory_future.result(
                        timeout=_PERSONA_TIMEOUT_SECONDS
                    )
                except Exception:
                    logger.warning(
                        "Wood advisory failed for %s; skipping advisory",
                        symbol,
                        exc_info=True,
                    )

        # 6. Aggregate and return
        result = self.aggregator.aggregate(votes, advisory_vote)
        # Ensure the symbol is set on the result
        if not result.symbol:
            result = ConsensusResult(
                symbol=symbol,
                votes=result.votes,
                advisory_vote=result.advisory_vote,
                buy_count=result.buy_count,
                sell_count=result.sell_count,
                hold_count=result.hold_count,
                abstain_count=result.abstain_count,
                passes_threshold=result.passes_threshold,
                avg_conviction=result.avg_conviction,
                category_diversity=result.category_diversity,
            )
        return result
