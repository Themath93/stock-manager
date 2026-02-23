"""Philip Fisher persona: growth investor focusing on management quality.

"The stock market is filled with individuals who know the price of
everything, but the value of nothing."

Criteria (all must pass for BUY):
    1. Revenue growth > 15% YoY
    2. R&D spending proxy (operating expenses indicate investment)
    3. Profit margins expanding (operating_margin > net_margin -- reinvesting)
    4. Low D/E < 0.3 (conservative balance sheet)
    5. ROE > 20% (superior capital allocation)
    6. Consistent earnings beats (positive earnings growth as proxy)

LLM trigger ~35%: management quality assessment requires qualitative judgment.
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_REVENUE_GROWTH_MIN = 15.0     # Minimum revenue growth YoY (%)
_DEBT_EQUITY_MAX = 0.3         # Conservative balance sheet
_ROE_MIN = 20.0                # Superior capital allocation
_MARGIN_MIN = 5.0              # Minimum operating margin (%)
_EARNINGS_GROWTH_MIN = 0.0     # Positive earnings growth
_CONVICTION_PER_CRITERIA = 1 / 6


class FisherPersona(InvestorPersona):
    """Philip Fisher: scuttlebutt growth investing with management quality focus."""

    def __init__(self) -> None:
        self.name = "Fisher"
        self.category = PersonaCategory.GROWTH

    @property
    def llm_trigger_rate(self) -> float:
        return 0.35

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {}

        # 1. Revenue growth > 15% YoY
        criteria["revenue_growth"] = snapshot.revenue_growth_yoy > _REVENUE_GROWTH_MIN

        # 2. R&D spending proxy: operating margin is positive but not
        #    excessively high relative to net margin (company is investing)
        #    A company investing in R&D will have operating_margin > 0 but the
        #    gap between operating_margin and net_margin indicates reinvestment.
        criteria["rd_investment"] = (
            snapshot.operating_margin > _MARGIN_MIN
            and snapshot.operating_margin > snapshot.net_margin
        )

        # 3. Profit margins expanding proxy: positive operating margin with
        #    positive revenue growth suggests margin expansion trajectory
        criteria["margins_healthy"] = (
            snapshot.operating_margin > _MARGIN_MIN
            and snapshot.net_margin > 0
        )

        # 4. Low D/E (conservative balance sheet)
        criteria["low_debt"] = 0 <= snapshot.debt_to_equity < _DEBT_EQUITY_MAX

        # 5. ROE > 20% (superior capital allocation)
        criteria["high_roe"] = snapshot.roe > _ROE_MIN

        # 6. Consistent earnings beats proxy: positive earnings growth
        criteria["earnings_growth"] = (
            snapshot.earnings_growth_yoy > _EARNINGS_GROWTH_MIN
        )

        # --- Conviction ---
        met_count = sum(criteria.values())
        conviction = round(met_count * _CONVICTION_PER_CRITERIA, 4)

        # --- Action ---
        if met_count >= 5:
            action = VoteAction.BUY
        elif met_count >= 3:
            action = VoteAction.HOLD
        elif met_count <= 1:
            action = VoteAction.SELL
        else:
            action = VoteAction.HOLD

        # --- Reasoning ---
        failed = [k for k, v in criteria.items() if not v]
        if met_count >= 5:
            reasoning = (
                "Exceptional growth profile with strong management indicators. "
                "Fisher would hold this for decades -- the scuttlebutt is positive."
            )
        elif met_count >= 3:
            reasoning = (
                f"Promising growth story with gaps: {', '.join(failed)}. "
                "Fisher would dig deeper into management before committing."
            )
        else:
            reasoning = (
                f"Insufficient growth characteristics. Fails: {', '.join(failed)}. "
                "Fisher would pass -- not enough evidence of superior management."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger for management quality assessment on borderline cases."""
        passed = sum(1 for v in vote.criteria_met.values() if v)
        return 3 <= passed <= 4
