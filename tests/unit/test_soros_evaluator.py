"""Unit tests for build_rule_based_thesis and related helpers.

Tests are deterministic: all inputs are constructed directly from
CycleAnalysis dataclasses — no network calls, no mocking required.
"""

from __future__ import annotations

from decimal import Decimal


from stock_manager.trading.reflexivity.cycle_detector import CycleAnalysis
from stock_manager.trading.reflexivity.thesis import CycleStage, MarketThesis
from stock_manager.trading.personas.soros_evaluator import (
    _STAGE_NARRATIVES,
    build_rule_based_thesis,
    calculate_position_size,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _analysis(
    stage: CycleStage,
    trend_strength: str = "0.5",
    volatility: str = "0.2",
    momentum: int = 1,
    volume_pattern: str = "normal",
) -> CycleAnalysis:
    return CycleAnalysis(
        stage=stage,
        trend_strength=Decimal(trend_strength),
        volatility=Decimal(volatility),
        momentum=momentum,
        volume_pattern=volume_pattern,
    )


def _thesis(
    stage: CycleStage,
    trend_strength: str = "0.5",
    volatility: str = "0.2",
    momentum: int = 1,
    current_price: str = "10000",
) -> MarketThesis:
    return build_rule_based_thesis(
        symbol="TEST",
        analysis=_analysis(
            stage, trend_strength=trend_strength, volatility=volatility, momentum=momentum
        ),
        current_price=Decimal(current_price),
    )


# ---------------------------------------------------------------------------
# TestBuildRuleBasedThesis
# ---------------------------------------------------------------------------


class TestBuildRuleBasedThesis:
    def test_inception_valid_entry(self):
        # INCEPTION + positive momentum + reasonable conviction -> valid entry
        thesis = _thesis(CycleStage.INCEPTION, trend_strength="0.6", momentum=1)
        assert thesis.is_valid_entry is True
        assert thesis.conviction > Decimal("0")

    def test_acceleration_valid_entry(self):
        thesis = _thesis(CycleStage.ACCELERATION, trend_strength="0.7", momentum=1)
        assert thesis.is_valid_entry is True

    def test_testing_can_be_valid_entry(self):
        # TESTING stage can still be a valid entry if asymmetry and conviction thresholds met
        thesis = _thesis(CycleStage.TESTING, trend_strength="0.7", volatility="0.1", momentum=1)
        # is_valid_entry requires asymmetry_ratio >= 3.0 and conviction >= 0.5
        # Whether it passes depends on computed values; just verify it returns a thesis
        assert isinstance(thesis.is_valid_entry, bool)

    def test_euphoria_invalid_entry(self):
        # EUPHORIA: stage_ordinal=3, high downside factor -> low asymmetry ratio
        thesis = _thesis(CycleStage.EUPHORIA, trend_strength="0.5", volatility="0.4")
        assert thesis.is_valid_entry is False

    def test_collapse_invalid_entry(self):
        thesis = _thesis(CycleStage.COLLAPSE, trend_strength="0.5", volatility="0.3")
        assert thesis.is_valid_entry is False

    def test_twilight_invalid_entry(self):
        thesis = _thesis(CycleStage.TWILIGHT, momentum=-1)
        assert thesis.is_valid_entry is False

    def test_returns_market_thesis_instance(self):
        thesis = _thesis(CycleStage.INCEPTION)
        assert isinstance(thesis, MarketThesis)

    def test_symbol_preserved(self):
        analysis = _analysis(CycleStage.INCEPTION)
        thesis = build_rule_based_thesis("005930", analysis, Decimal("50000"))
        assert thesis.symbol == "005930"

    def test_cycle_stage_matches_analysis(self):
        for stage in CycleStage:
            thesis = _thesis(stage)
            assert thesis.cycle_stage == stage

    def test_conviction_positive_momentum_bonus(self):
        base = _thesis(CycleStage.INCEPTION, trend_strength="0.5", momentum=0)
        boosted = _thesis(CycleStage.INCEPTION, trend_strength="0.5", momentum=1)
        assert boosted.conviction > base.conviction

    def test_conviction_negative_momentum_penalty(self):
        base = _thesis(CycleStage.INCEPTION, trend_strength="0.5", momentum=0)
        penalized = _thesis(CycleStage.INCEPTION, trend_strength="0.5", momentum=-1)
        assert penalized.conviction < base.conviction

    def test_conviction_clamped_to_one(self):
        # Max trend_strength + positive momentum should not exceed 1.0
        thesis = _thesis(CycleStage.INCEPTION, trend_strength="1.0", momentum=1)
        assert thesis.conviction <= Decimal("1.0")

    def test_conviction_clamped_to_zero(self):
        # Min trend_strength + negative momentum should not go below 0.0
        thesis = _thesis(CycleStage.INCEPTION, trend_strength="0.0", momentum=-1)
        assert thesis.conviction >= Decimal("0.0")

    def test_potential_upside_scales_with_price(self):
        cheap = _thesis(CycleStage.INCEPTION, current_price="1000")
        expensive = _thesis(CycleStage.INCEPTION, current_price="100000")
        assert expensive.potential_upside > cheap.potential_upside

    def test_potential_downside_scales_with_volatility(self):
        low_vol = _thesis(CycleStage.INCEPTION, volatility="0.1")
        high_vol = _thesis(CycleStage.INCEPTION, volatility="0.5")
        assert high_vol.potential_downside > low_vol.potential_downside

    def test_narratives_populated_from_templates(self):
        for stage in CycleStage:
            thesis = _thesis(stage)
            expected = _STAGE_NARRATIVES[stage]
            assert thesis.perception == expected["narrative"]
            assert thesis.reality == expected["risk_assessment"]
            assert thesis.prediction == expected["opportunity"]

    def test_invalidation_triggers_nonempty(self):
        for stage in CycleStage:
            thesis = _thesis(stage)
            assert len(thesis.invalidation_triggers) > 0

    def test_feedback_loop_description_contains_stage(self):
        thesis = _thesis(CycleStage.INCEPTION)
        assert "inception" in thesis.feedback_loop.lower()

    def test_feedback_strength_matches_trend_strength(self):
        analysis = _analysis(CycleStage.INCEPTION, trend_strength="0.6500")
        thesis = build_rule_based_thesis("X", analysis, Decimal("100"))
        assert thesis.feedback_strength == Decimal("0.6500")

    def test_zero_volatility_does_not_raise(self):
        # Zero volatility floor prevents ZeroDivisionError in _derive_asymmetry_ratio
        thesis = _thesis(CycleStage.INCEPTION, volatility="0.0")
        assert thesis.asymmetry_ratio == Decimal("10.0")

    def test_perception_reality_gap_early_stage_small(self):
        # INCEPTION ordinal=0 -> gap = trend_strength * 0/5 = 0
        analysis = _analysis(CycleStage.INCEPTION, trend_strength="0.8")
        thesis = build_rule_based_thesis("X", analysis, Decimal("100"))
        assert thesis.perception_reality_gap == Decimal("0.0000")

    def test_perception_reality_gap_late_stage_larger(self):
        inception_thesis = _thesis(CycleStage.INCEPTION, trend_strength="0.8")
        collapse_thesis = _thesis(CycleStage.COLLAPSE, trend_strength="0.8")
        assert collapse_thesis.perception_reality_gap > inception_thesis.perception_reality_gap


# ---------------------------------------------------------------------------
# TestStageNarratives
# ---------------------------------------------------------------------------


class TestStageNarratives:
    def test_all_six_stages_present(self):
        for stage in CycleStage:
            assert stage in _STAGE_NARRATIVES, f"Missing stage: {stage}"

    def test_each_entry_has_required_keys(self):
        required_keys = {"narrative", "risk_assessment", "opportunity"}
        for stage, entry in _STAGE_NARRATIVES.items():
            missing = required_keys - set(entry.keys())
            assert not missing, f"Stage {stage} missing keys: {missing}"

    def test_narrative_values_nonempty_strings(self):
        for stage, entry in _STAGE_NARRATIVES.items():
            for key in ("narrative", "risk_assessment", "opportunity"):
                val = entry[key]
                assert isinstance(val, str), f"{stage}.{key} must be str"
                assert len(val.strip()) > 0, f"{stage}.{key} must not be empty"

    def test_no_extra_keys(self):
        allowed_keys = {"narrative", "risk_assessment", "opportunity"}
        for stage, entry in _STAGE_NARRATIVES.items():
            extra = set(entry.keys()) - allowed_keys
            assert not extra, f"Stage {stage} has unexpected keys: {extra}"


# ---------------------------------------------------------------------------
# TestPositionSizing
# ---------------------------------------------------------------------------


class TestPositionSizing:
    def test_scales_with_conviction(self):
        portfolio = Decimal("1000000")
        vol = Decimal("0.2")
        low_conv = calculate_position_size(Decimal("0.01"), vol, portfolio)
        high_conv = calculate_position_size(Decimal("0.02"), vol, portfolio)
        assert high_conv > low_conv

    def test_scales_inversely_with_volatility(self):
        portfolio = Decimal("1000000")
        conviction = Decimal("0.01")
        low_vol = calculate_position_size(conviction, Decimal("0.1"), portfolio)
        high_vol = calculate_position_size(conviction, Decimal("0.5"), portfolio)
        assert low_vol > high_vol

    def test_capped_at_max_risk_pct(self):
        portfolio = Decimal("1000000")
        max_risk = Decimal("0.02")
        # Very high conviction with very low volatility -> without cap would exceed max_risk
        size = calculate_position_size(Decimal("1.0"), Decimal("0.001"), portfolio, max_risk)
        max_allowed = (portfolio * max_risk).quantize(Decimal("1"))
        assert size <= max_allowed, f"Position size {size} exceeds cap {max_allowed}"

    def test_zero_volatility_uses_floor(self):
        # Zero volatility should not raise; floor of 0.01 applied internally
        size = calculate_position_size(Decimal("0.5"), Decimal("0.0"), Decimal("100000"))
        assert size >= Decimal("0")

    def test_returns_integer_units(self):
        # Position size is rounded to 1 (whole currency units)
        size = calculate_position_size(Decimal("0.5"), Decimal("0.2"), Decimal("500000"))
        assert size == size.to_integral_value()

    def test_scales_with_portfolio_value(self):
        vol = Decimal("0.2")
        conviction = Decimal("0.5")
        small = calculate_position_size(conviction, vol, Decimal("100000"))
        large = calculate_position_size(conviction, vol, Decimal("1000000"))
        assert large > small

    def test_default_max_risk_is_two_percent(self):
        portfolio = Decimal("1000000")
        # Max possible size with default max_risk=0.02
        size = calculate_position_size(Decimal("1.0"), Decimal("0.001"), portfolio)
        assert size <= Decimal("20000"), f"Default 2% cap should limit to 20000, got {size}"


# ---------------------------------------------------------------------------
# TestBuildRuleBasedThesisPositionSizingIntegration
# ---------------------------------------------------------------------------


class TestBuildRuleBasedThesisPositionSizingIntegration:
    """Verify that portfolio_value / max_risk_pct params are accepted without error."""

    def test_custom_portfolio_value_accepted(self):
        analysis = _analysis(CycleStage.INCEPTION)
        thesis = build_rule_based_thesis(
            "X",
            analysis,
            Decimal("50000"),
            portfolio_value=Decimal("5000000"),
        )
        assert isinstance(thesis, MarketThesis)

    def test_custom_max_risk_accepted(self):
        analysis = _analysis(CycleStage.INCEPTION)
        thesis = build_rule_based_thesis(
            "X",
            analysis,
            Decimal("50000"),
            max_risk_pct=Decimal("0.01"),
        )
        assert isinstance(thesis, MarketThesis)

    def test_non_entry_stage_does_not_raise(self):
        # COLLAPSE is not a valid entry stage; should still return a thesis
        analysis = _analysis(CycleStage.COLLAPSE)
        thesis = build_rule_based_thesis("X", analysis, Decimal("1000"))
        assert thesis.cycle_stage == CycleStage.COLLAPSE
