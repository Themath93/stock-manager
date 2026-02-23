"""Warren Buffett investor persona.

Focuses on durable competitive advantages: high ROE, low leverage,
wide margins, earnings stability, positive free cash flow, dividend
history, and sustained profitability.
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction

# Thresholds
_MIN_ROE = 15.0            # %
_MAX_DEBT_TO_EQUITY = 0.5
_MIN_NET_MARGIN = 20.0     # %
_MIN_YEARS_EARNINGS = 10
_MIN_YEARS_DIVIDENDS = 5
_MIN_OPERATING_MARGIN = 15.0  # % (sustained margins proxy)


class BuffettPersona(InvestorPersona):
    """Quality compounder: durable competitive advantages."""

    def __init__(self) -> None:
        self.name = "Buffett"
        self.category = PersonaCategory.VALUE

    # -- criteria helpers --------------------------------------------------

    @staticmethod
    def _check_roe(snapshot: MarketSnapshot) -> bool:
        return snapshot.roe > _MIN_ROE

    @staticmethod
    def _check_low_leverage(snapshot: MarketSnapshot) -> bool:
        return snapshot.debt_to_equity < _MAX_DEBT_TO_EQUITY

    @staticmethod
    def _check_net_margin(snapshot: MarketSnapshot) -> bool:
        return snapshot.net_margin > _MIN_NET_MARGIN

    @staticmethod
    def _check_earnings_stability(snapshot: MarketSnapshot) -> bool:
        return snapshot.years_positive_earnings >= _MIN_YEARS_EARNINGS

    @staticmethod
    def _check_fcf_positive(snapshot: MarketSnapshot) -> bool:
        return snapshot.free_cash_flow > 0

    @staticmethod
    def _check_dividend_growth(snapshot: MarketSnapshot) -> bool:
        return snapshot.years_dividends_paid >= _MIN_YEARS_DIVIDENDS

    @staticmethod
    def _check_sustained_margins(snapshot: MarketSnapshot) -> bool:
        return snapshot.operating_margin > _MIN_OPERATING_MARGIN

    # -- InvestorPersona interface -----------------------------------------

    @property
    def llm_trigger_rate(self) -> float:
        return 0.20  # ~20 %

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger LLM on borderline cases: 4-5 of 7 criteria."""
        met = sum(vote.criteria_met.values())
        return met in (4, 5)

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {
            "roe_above_15": self._check_roe(snapshot),
            "low_leverage": self._check_low_leverage(snapshot),
            "net_margin_above_20": self._check_net_margin(snapshot),
            "earnings_stability_10yr": self._check_earnings_stability(snapshot),
            "fcf_positive": self._check_fcf_positive(snapshot),
            "dividend_growth": self._check_dividend_growth(snapshot),
            "sustained_margins": self._check_sustained_margins(snapshot),
        }
        met = sum(criteria.values())

        if met >= 6:
            action = VoteAction.BUY
            conviction = 0.85
            reasoning = (
                f"{met}/7 Buffett criteria met. Strong durable competitive "
                "advantage with high returns on equity and conservative balance sheet."
            )
        elif met >= 4:
            action = VoteAction.BUY
            conviction = 0.55
            reasoning = (
                f"{met}/7 Buffett criteria met. Promising quality indicators "
                "but gaps remain; LLM review recommended for moat assessment."
            )
        elif met >= 2:
            action = VoteAction.HOLD
            conviction = 0.4
            reasoning = (
                f"Only {met}/7 Buffett criteria met. Competitive advantage "
                "is not clearly demonstrated across key dimensions."
            )
        else:
            action = VoteAction.SELL
            conviction = 0.7
            reasoning = (
                f"Only {met}/7 Buffett criteria met. Lacks the hallmarks of "
                "a durable competitive advantage. Capital better deployed elsewhere."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )
