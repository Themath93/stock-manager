"""Charlie Munger persona: quality-focused contrarian with mental model checklist.

Applies inversion thinking -- starts by identifying what would make an
investment *bad*, then checks whether the stock avoids those pitfalls.

Criteria (all must pass for BUY):
    1. No accounting red flags (receivables not growing faster than revenue proxy)
    2. Competitive moat (sustained ROE > 15%)
    3. Management alignment (sector proxy -- understandable business)
    4. Reasonable price (P/E < 25 AND P/B < 3.0)
    5. Understandable business (sector not blank/unknown)
    6. Low debt (D/E < 1.0)

LLM trigger ~35%: qualitative moat assessment in borderline cases.
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_ROE_MOAT_MIN = 15.0          # Sustained ROE threshold for competitive moat
_PE_MAX = 25.0                 # Maximum acceptable P/E ratio
_PB_MAX = 3.0                  # Maximum acceptable P/B ratio
_DEBT_EQUITY_MAX = 1.0         # Maximum debt-to-equity ratio
_CONVICTION_PER_CRITERIA = 1 / 6  # 6 criteria -> each worth ~0.167


class MungerPersona(InvestorPersona):
    """Charlie Munger: quality at a reasonable price via inversion thinking."""

    def __init__(self) -> None:
        self.name = "Munger"
        self.category = PersonaCategory.VALUE

    @property
    def llm_trigger_rate(self) -> float:
        return 0.35

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {}

        # 1. No accounting red flags
        #    Proxy: receivables should not be disproportionately large
        #    relative to total assets (a rough heuristic without multi-year data).
        if snapshot.total_assets > 0:
            receivable_ratio = float(snapshot.accounts_receivable) / float(snapshot.total_assets)
            criteria["no_accounting_red_flags"] = receivable_ratio < 0.30
        else:
            criteria["no_accounting_red_flags"] = False

        # 2. Competitive moat -- sustained ROE > 15%
        criteria["competitive_moat"] = snapshot.roe > _ROE_MOAT_MIN

        # 3. Understandable business -- sector is known
        criteria["understandable_business"] = bool(
            snapshot.sector and snapshot.sector.strip().lower() not in ("", "unknown")
        )

        # 4. Reasonable price -- P/E < 25 AND P/B < 3.0
        pe_ok = 0 < snapshot.per < _PE_MAX
        pb_ok = 0 < snapshot.pbr < _PB_MAX
        criteria["reasonable_price"] = pe_ok and pb_ok

        # 5. Management alignment -- proxy: positive margins + positive earnings
        criteria["management_alignment"] = (
            snapshot.operating_margin > 0 and snapshot.net_margin > 0
        )

        # 6. Low debt
        criteria["low_debt"] = 0 <= snapshot.debt_to_equity < _DEBT_EQUITY_MAX

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

        # --- Reasoning (inversion style) ---
        failed = [k for k, v in criteria.items() if not v]
        if not failed:
            reasoning = (
                "Passes all Munger mental model checks: quality business at a "
                "reasonable price with no accounting red flags."
            )
        else:
            reasoning = (
                f"Fails inversion test on: {', '.join(failed)}. "
                "Munger would avoid until these concerns are resolved."
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
        """Trigger when no clear red flags but not clearly good either."""
        passed = sum(1 for v in vote.criteria_met.values() if v)
        return 3 <= passed <= 4
