"""George Soros investor persona.

Reflexivity-based evaluation using BoomBustCycleDetector and the
rule-based thesis builder.  Favours early-cycle entries where the
perception-reality gap creates asymmetric payoff.
"""

from __future__ import annotations

from decimal import Decimal

from stock_manager.trading.reflexivity.cycle_detector import (
    BoomBustCycleDetector,
    CycleAnalysis,
)
from stock_manager.trading.reflexivity.thesis import CycleStage, MarketThesis
from stock_manager.trading.personas.soros_evaluator import build_rule_based_thesis

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


class SorosPersona(InvestorPersona):
    """Reflexivity trader: boom-bust cycle positioning."""

    def __init__(self, detector: BoomBustCycleDetector) -> None:
        self.name = "Soros"
        self.category = PersonaCategory.MACRO
        self._detector = detector

    # -- criteria helpers --------------------------------------------------

    @staticmethod
    def _check_entry_stage(stage: CycleStage) -> bool:
        """INCEPTION or ACCELERATION are valid entry stages."""
        return stage in (CycleStage.INCEPTION, CycleStage.ACCELERATION)

    @staticmethod
    def _check_perception_gap(thesis: MarketThesis) -> bool:
        """Perception-reality gap must be non-trivial."""
        return thesis.perception_reality_gap > Decimal("0")

    @staticmethod
    def _check_asymmetry(thesis: MarketThesis) -> bool:
        """Asymmetry ratio >= 3.0 for favourable risk/reward."""
        return thesis.asymmetry_ratio >= Decimal("3.0")

    @staticmethod
    def _check_conviction(thesis: MarketThesis) -> bool:
        """Conviction >= 0.5."""
        return thesis.conviction >= Decimal("0.5")

    @staticmethod
    def _check_feedback_strength(thesis: MarketThesis) -> bool:
        """Feedback loop strength > 0.3."""
        return thesis.feedback_strength > Decimal("0.3")

    # -- InvestorPersona interface -----------------------------------------

    @property
    def llm_trigger_rate(self) -> float:
        return 0.25

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger when cycle stage is ambiguous (HOLD with mid-range conviction)."""
        return vote.action == VoteAction.HOLD and 0.3 <= vote.conviction <= 0.6

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        # Run cycle detection
        analysis: CycleAnalysis = self._detector.detect_stage_full(
            snapshot.symbol,
        )

        # Build thesis from cycle analysis
        thesis: MarketThesis = build_rule_based_thesis(
            symbol=snapshot.symbol,
            analysis=analysis,
            current_price=snapshot.current_price,
        )

        stage = analysis.stage

        criteria: dict[str, bool] = {
            "entry_stage": self._check_entry_stage(stage),
            "perception_gap": self._check_perception_gap(thesis),
            "asymmetry_gte_3": self._check_asymmetry(thesis),
            "conviction_gte_05": self._check_conviction(thesis),
            "feedback_strength_gt_03": self._check_feedback_strength(thesis),
            # Extra flag consumed by should_trigger_llm
            "testing_stage": stage == CycleStage.TESTING,
        }
        met = sum(criteria.values()) - (1 if criteria["testing_stage"] else 0)
        # testing_stage is informational, not scored

        if met == 5:
            action = VoteAction.BUY
            conviction = 0.85
            reasoning = (
                f"All 5 Soros reflexivity criteria met at {stage.value} stage. "
                f"Asymmetry ratio {thesis.asymmetry_ratio}, feedback strength "
                f"{thesis.feedback_strength}. Strong entry signal."
            )
        elif met >= 3:
            action = VoteAction.BUY
            conviction = 0.55
            reasoning = (
                f"{met}/5 Soros criteria met at {stage.value} stage. "
                "Reflexive dynamics present but not fully aligned."
            )
        elif met >= 2:
            action = VoteAction.HOLD
            conviction = 0.35
            reasoning = (
                f"Only {met}/5 Soros criteria met at {stage.value} stage. "
                "Cycle dynamics are ambiguous; wait for clearer signal."
            )
        else:
            if stage in (CycleStage.EUPHORIA, CycleStage.TWILIGHT, CycleStage.COLLAPSE):
                action = VoteAction.SELL
                conviction = 0.75
                reasoning = (
                    f"Late cycle ({stage.value}) with only {met}/5 criteria met. "
                    "Reflexive feedback loop is inverting; exit recommended."
                )
            else:
                action = VoteAction.ABSTAIN
                conviction = 0.2
                reasoning = (
                    f"Only {met}/5 Soros criteria met at {stage.value} stage. "
                    "Insufficient reflexive signal to form a thesis."
                )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )
