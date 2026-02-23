"""John Templeton persona: contrarian value-hunter seeking maximum pessimism.

"The time of maximum pessimism is the best time to buy."

Criteria (all must pass for BUY):
    1. Stock down > 30% from 52-week high
    2. P/E < 10
    3. P/B < 1.0
    4. Positive earnings (EPS > 0)
    5. Sector pessimism (proxy: stock far below 52w high while earnings positive)
    6. Dividend yield > market average (proxy: > 2.0%)

LLM trigger ~15%: distinguishing genuine value from value traps.
"""

from __future__ import annotations

from decimal import Decimal

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_DRAWDOWN_MIN = 0.30           # Minimum drawdown from 52w high (30%)
_PE_MAX = 10.0                 # Maximum P/E for deep value
_PB_MAX = 1.0                  # Maximum P/B (trading below book value)
_DIVIDEND_YIELD_MIN = 2.0      # Minimum dividend yield (market avg proxy)
_CONVICTION_PER_CRITERIA = 1 / 6


class TempletonPersona(InvestorPersona):
    """John Templeton: buy at the point of maximum pessimism."""

    def __init__(self) -> None:
        self.name = "Templeton"
        self.category = PersonaCategory.VALUE

    @property
    def llm_trigger_rate(self) -> float:
        return 0.15

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {}

        # 1. Stock down > 30% from 52-week high
        if snapshot.price_52w_high > 0:
            drawdown = (
                float(snapshot.price_52w_high - snapshot.current_price)
                / float(snapshot.price_52w_high)
            )
            criteria["down_from_52w_high"] = drawdown >= _DRAWDOWN_MIN
        else:
            criteria["down_from_52w_high"] = False

        # 2. P/E < 10
        criteria["low_pe"] = 0 < snapshot.per < _PE_MAX

        # 3. P/B < 1.0
        criteria["low_pb"] = 0 < snapshot.pbr < _PB_MAX

        # 4. Positive earnings
        criteria["positive_earnings"] = snapshot.eps > Decimal("0")

        # 5. Sector pessimism proxy: significant drawdown + still earning
        #    (deep drawdown despite positive fundamentals implies pessimism)
        criteria["sector_pessimism"] = (
            criteria["down_from_52w_high"] and criteria["positive_earnings"]
        )

        # 6. Dividend yield > market average
        criteria["dividend_above_avg"] = snapshot.dividend_yield > _DIVIDEND_YIELD_MIN

        # --- Conviction ---
        met_count = sum(criteria.values())
        conviction = round(met_count * _CONVICTION_PER_CRITERIA, 4)

        # --- Action ---
        if met_count == len(criteria):
            action = VoteAction.BUY
        elif met_count >= 4:
            action = VoteAction.HOLD
        elif met_count <= 1:
            action = VoteAction.SELL
        else:
            action = VoteAction.HOLD

        # --- Reasoning ---
        failed = [k for k, v in criteria.items() if not v]
        if not failed:
            reasoning = (
                "Maximum pessimism conditions met: deep drawdown, low "
                "valuation, positive earnings, and solid dividend. "
                "Classic Templeton contrarian buy."
            )
        else:
            reasoning = (
                f"Not at maximum pessimism. Fails: {', '.join(failed)}. "
                "Templeton would wait for cheaper entry or stronger fundamentals."
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
        """Trigger to distinguish value from value trap."""
        return vote.action == VoteAction.BUY and vote.conviction < 0.7
