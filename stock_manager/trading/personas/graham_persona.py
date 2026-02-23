"""Benjamin Graham investor persona.

Reuses the 7 defensive-investor criteria from GrahamScreener but operates
on a MarketSnapshot instead of making live API calls.  Conviction is
graduated by how many of the 7 criteria pass.
"""

from __future__ import annotations

from decimal import Decimal

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# Minimum market-cap thresholds (same as GrahamScreener)
_MIN_MARKET_CAP_KOSPI = Decimal("2400000000000")   # 2.4 trillion KRW
_MIN_MARKET_CAP_KOSDAQ = Decimal("500000000000")    # 500 billion KRW


class GrahamPersona(InvestorPersona):
    """Defensive investor: all 7 Graham criteria on a MarketSnapshot."""

    def __init__(self) -> None:
        self.name = "Graham"
        self.category = PersonaCategory.VALUE

    # -- criteria helpers --------------------------------------------------

    @staticmethod
    def _check_size(snapshot: MarketSnapshot) -> bool:
        threshold = (
            _MIN_MARKET_CAP_KOSPI
            if snapshot.market.upper() == "KOSPI"
            else _MIN_MARKET_CAP_KOSDAQ
        )
        return snapshot.market_cap >= threshold

    @staticmethod
    def _check_financial(snapshot: MarketSnapshot) -> bool:
        return snapshot.current_ratio >= 2.0 and snapshot.debt_to_equity < 1.0

    @staticmethod
    def _check_stability(snapshot: MarketSnapshot) -> bool:
        return snapshot.years_positive_earnings >= 10

    @staticmethod
    def _check_dividends(snapshot: MarketSnapshot) -> bool:
        return snapshot.years_dividends_paid >= 20

    @staticmethod
    def _check_growth(snapshot: MarketSnapshot) -> bool:
        return snapshot.earnings_growth_yoy > 0

    @staticmethod
    def _check_pe(snapshot: MarketSnapshot) -> bool:
        return 0 < snapshot.per <= 15.0

    @staticmethod
    def _check_pb(snapshot: MarketSnapshot) -> bool:
        return snapshot.pbr <= 1.5

    # -- InvestorPersona interface -----------------------------------------

    @property
    def llm_trigger_rate(self) -> float:
        return 0.05  # ~5 %

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger LLM when borderline: 5-6 criteria met."""
        met = sum(vote.criteria_met.values())
        return met in (5, 6)

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {
            "size": self._check_size(snapshot),
            "financial": self._check_financial(snapshot),
            "stability": self._check_stability(snapshot),
            "dividends": self._check_dividends(snapshot),
            "growth": self._check_growth(snapshot),
            "pe": self._check_pe(snapshot),
            "pb": self._check_pb(snapshot),
        }
        met = sum(criteria.values())

        if met == 7:
            action = VoteAction.BUY
            conviction = 0.9
            reasoning = (
                "All 7 Graham defensive criteria satisfied. "
                "Classic deep-value opportunity with full margin of safety."
            )
        elif met >= 5:
            action = VoteAction.BUY
            conviction = 0.6
            reasoning = (
                f"{met}/7 Graham criteria met. Near-miss on defensive screen; "
                "LLM review recommended for qualitative assessment of gaps."
            )
        elif met >= 3:
            action = VoteAction.HOLD
            conviction = 0.4
            reasoning = (
                f"Only {met}/7 Graham criteria met. Insufficient margin of "
                "safety for a defensive position but not a clear sell."
            )
        else:
            action = VoteAction.SELL
            conviction = 0.7
            reasoning = (
                f"Only {met}/7 Graham criteria met. Stock fails the defensive "
                "investor screen on most dimensions."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )
