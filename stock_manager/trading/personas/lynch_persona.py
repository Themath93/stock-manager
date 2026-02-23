"""Peter Lynch investor persona.

Growth At a Reasonable Price (GARP) approach centred on PEG ratio,
earnings growth rate, revenue momentum, and stock classification
(stalwart, fast grower, turnaround, cyclical).
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Lynch stock classifications
# ---------------------------------------------------------------------------

def _classify_stock(snapshot: MarketSnapshot) -> str:
    """Classify into one of Lynch's categories based on growth profile.

    - fast_grower:  earnings growth > 20 %
    - stalwart:     earnings growth 10-20 %
    - turnaround:   negative earnings growth but positive revenue growth
    - cyclical:     everything else (catch-all)
    """
    eg = snapshot.earnings_growth_yoy
    rg = snapshot.revenue_growth_yoy

    if eg > 20.0:
        return "fast_grower"
    if eg >= 10.0:
        return "stalwart"
    if eg < 0 and rg > 0:
        return "turnaround"
    return "cyclical"


class LynchPersona(InvestorPersona):
    """GARP investor: PEG ratio + growth quality screen."""

    def __init__(self) -> None:
        self.name = "Lynch"
        self.category = PersonaCategory.GROWTH

    # -- criteria helpers --------------------------------------------------

    @staticmethod
    def _check_peg(snapshot: MarketSnapshot) -> bool:
        """PEG < 1.0 (P/E divided by earnings growth rate)."""
        if snapshot.earnings_growth_yoy <= 0 or snapshot.per <= 0:
            return False
        peg = snapshot.per / snapshot.earnings_growth_yoy
        return peg < 1.0

    @staticmethod
    def _check_earnings_growth_range(snapshot: MarketSnapshot) -> bool:
        """Ideal growth: 20-50 % (fast but not unsustainably hot)."""
        return 20.0 <= snapshot.earnings_growth_yoy <= 50.0

    @staticmethod
    def _check_pe_below_avg(snapshot: MarketSnapshot) -> bool:
        """P/E below market average (use KOSPI P/E if available, else 15)."""
        if snapshot.per <= 0:
            return False
        market_pe = snapshot.kospi_per if snapshot.kospi_per else 15.0
        return snapshot.per < market_pe

    @staticmethod
    def _check_revenue_growth(snapshot: MarketSnapshot) -> bool:
        """Revenue growth > 10 %."""
        return snapshot.revenue_growth_yoy > 10.0

    @staticmethod
    def _check_classification_favorable(snapshot: MarketSnapshot) -> bool:
        """Fast growers and stalwarts are favorable classifications."""
        classification = _classify_stock(snapshot)
        return classification in ("fast_grower", "stalwart")

    # -- InvestorPersona interface -----------------------------------------

    @property
    def llm_trigger_rate(self) -> float:
        return 0.15

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger for turnaround candidates (HOLD with some criteria met)."""
        passed = sum(1 for v in vote.criteria_met.values() if v)
        return vote.action == VoteAction.HOLD and passed >= 3

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        classification = _classify_stock(snapshot)

        criteria: dict[str, bool] = {
            "peg_below_1": self._check_peg(snapshot),
            "earnings_growth_20_50": self._check_earnings_growth_range(snapshot),
            "pe_below_market_avg": self._check_pe_below_avg(snapshot),
            "revenue_growth_above_10": self._check_revenue_growth(snapshot),
            "favorable_classification": self._check_classification_favorable(snapshot),
        }
        met = sum(criteria.values())

        if met >= 4:
            action = VoteAction.BUY
            conviction = 0.8
            reasoning = (
                f"{met}/5 Lynch GARP criteria met (classified as {classification}). "
                "Attractive PEG and growth profile with reasonable valuation."
            )
        elif met >= 3:
            action = VoteAction.BUY
            conviction = 0.55
            reasoning = (
                f"{met}/5 Lynch criteria met (classified as {classification}). "
                "Growth is present but valuation or classification warrants caution."
            )
        elif met >= 2:
            action = VoteAction.HOLD
            conviction = 0.4
            reasoning = (
                f"Only {met}/5 Lynch criteria met (classified as {classification}). "
                "Growth story is incomplete or valuation is stretched."
            )
        else:
            action = VoteAction.SELL
            conviction = 0.65
            reasoning = (
                f"Only {met}/5 Lynch criteria met (classified as {classification}). "
                "Neither growth nor valuation supports a GARP thesis."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )
