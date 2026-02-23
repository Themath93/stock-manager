"""Base class for investor personas in the consensus trading pipeline.

Each persona implements a deterministic rule-based screen. Phase 5 adds
optional LLM augmentation via HybridPersona, but the default path is
pure rule-based evaluation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import MarketSnapshot, PersonaCategory, PersonaVote


class InvestorPersona(ABC):
    """Abstract base for all investor personas.

    Subclasses must set ``name`` and ``category`` in __init__ and implement
    ``screen_rule`` which performs a deterministic evaluation of the snapshot.
    """

    name: str
    category: PersonaCategory

    @abstractmethod
    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        """Pure rule-based evaluation. Must be deterministic.

        Args:
            snapshot: Immutable market data for a single symbol.

        Returns:
            A fully populated PersonaVote.
        """
        ...

    @property
    def llm_trigger_rate(self) -> float:
        """Approximate percentage of evaluations that would trigger LLM.

        Override in subclasses to document expected trigger frequency.
        Default is 0.0 (never triggers).
        """
        return 0.0

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Whether this vote warrants LLM augmentation.

        Override in subclasses with persona-specific trigger logic.
        Default is False (pure rule-based).
        """
        return False

    def evaluate(self, snapshot: MarketSnapshot) -> PersonaVote:
        """Run evaluation pipeline.

        Default: just rule-based. HybridPersona overrides this in Phase 5.
        """
        return self.screen_rule(snapshot)
