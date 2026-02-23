"""Rule-based MarketThesis builder for the Soros persona.

Derives a MarketThesis from CycleAnalysis using static template narratives.
Phase 5 allows these templates to be replaced by LLM-generated narratives.
"""

from decimal import Decimal, ROUND_HALF_UP

from stock_manager.trading.reflexivity.cycle_detector import CycleAnalysis
from stock_manager.trading.reflexivity.thesis import CycleStage, MarketThesis


# ---------------------------------------------------------------------------
# Stage narrative templates
# Each stage contains three narrative keys consumed directly by MarketThesis:
#   - narrative    → MarketThesis.perception  (current market narrative)
#   - risk_assessment → MarketThesis.reality  (actual fundamental conditions)
#   - opportunity  → MarketThesis.prediction  (expected outcome)
#
# Phase 5 note: replace any entry in _STAGE_NARRATIVES at runtime with
# LLM-generated text before calling build_rule_based_thesis().
# ---------------------------------------------------------------------------

_STAGE_NARRATIVES: dict[CycleStage, dict[str, str]] = {
    CycleStage.INCEPTION: {
        "narrative": (
            "A new trend is forming but remains largely unrecognized by the "
            "broader market. Early adopters are accumulating positions while "
            "the crowd remains skeptical or indifferent."
        ),
        "risk_assessment": (
            "Fundamentals are improving but not yet reflected in consensus "
            "estimates. Low institutional ownership reduces forced-selling risk. "
            "Main risk is a failure to achieve escape velocity."
        ),
        "opportunity": (
            "As perception catches up with improving reality the mispricing "
            "should compress, generating outsized returns for early entrants. "
            "The reflexive feedback loop has not yet self-reinforced."
        ),
    },
    CycleStage.ACCELERATION: {
        "narrative": (
            "The trend is now broadly recognized and positive feedback is "
            "strengthening. Institutional interest is rising and the narrative "
            "is becoming self-reinforcing."
        ),
        "risk_assessment": (
            "Fundamentals still support the move but valuation is beginning to "
            "stretch. Momentum traders are joining, increasing crowding risk. "
            "A correction is possible but the primary trend remains intact."
        ),
        "opportunity": (
            "The reflexive boom-phase accelerates as more capital chases "
            "performance. Continued trend following offers strong risk/reward "
            "until signs of exhaustion appear."
        ),
    },
    CycleStage.TESTING: {
        "narrative": (
            "The market is experiencing a period of consolidation or minor "
            "correction after rapid gains. Bulls and bears are contesting "
            "control; sentiment has become mixed."
        ),
        "risk_assessment": (
            "Volatility is elevated, reflecting genuine uncertainty about "
            "whether the primary trend will reassert. Fundamental support "
            "remains but technical signals are ambiguous."
        ),
        "opportunity": (
            "A successful test of support confirms trend resilience and often "
            "precedes the next leg higher. Risk/reward improves for patient "
            "buyers who wait for the test to resolve bullishly."
        ),
    },
    CycleStage.EUPHORIA: {
        "narrative": (
            "Unsustainable exuberance dominates. The narrative has become "
            "detached from fundamentals; everyone expects prices to keep rising "
            "indefinitely. Retail participation is at a peak."
        ),
        "risk_assessment": (
            "Valuations are extreme relative to any reasonable fundamental "
            "scenario. Smart money is distributing to latecomers. The "
            "perception-reality gap is at its widest and most fragile."
        ),
        "opportunity": (
            "The primary opportunity is on the short side or in exiting longs. "
            "When the reflexive boom reverses, the collapse tends to be rapid "
            "and severe as the feedback loop inverts."
        ),
    },
    CycleStage.TWILIGHT: {
        "narrative": (
            "The trend is visibly weakening. Smart money is quietly exiting "
            "while the crowd remains bullish. Deteriorating breadth and "
            "momentum warn that the cycle peak has passed."
        ),
        "risk_assessment": (
            "Fundamentals are no longer supporting current prices. Momentum "
            "is negative and institutional distribution is ongoing. The window "
            "to exit long positions cleanly is narrowing."
        ),
        "opportunity": (
            "Short positions or defensive repositioning offer the best "
            "risk/reward. The reflexive unwind is beginning; holding longs "
            "risks capturing the full downside of the bust phase."
        ),
    },
    CycleStage.COLLAPSE: {
        "narrative": (
            "The boom-bust feedback loop has fully reversed. Forced selling, "
            "margin calls, and panic dominate price action. The prior narrative "
            "is discredited and pessimism is self-reinforcing."
        ),
        "risk_assessment": (
            "Prices may overshoot fair value to the downside as liquidity "
            "evaporates. Catching a falling knife carries substantial risk. "
            "Stabilization requires a fundamental catalyst or policy response."
        ),
        "opportunity": (
            "Deep-value opportunities begin to form for investors with long "
            "horizons and capital to deploy. The reflexive bust creates the "
            "conditions for the next inception phase."
        ),
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")

# Stages where entering a position makes sense (mirrors MarketThesis.is_valid_entry logic)
_VALID_ENTRY_STAGES = {CycleStage.INCEPTION, CycleStage.ACCELERATION, CycleStage.TESTING}

# Approximate stage ordinal (0 = earliest, 5 = latest) used in asymmetry calc
_STAGE_ORDINAL: dict[CycleStage, int] = {
    CycleStage.INCEPTION: 0,
    CycleStage.ACCELERATION: 1,
    CycleStage.TESTING: 2,
    CycleStage.EUPHORIA: 3,
    CycleStage.TWILIGHT: 4,
    CycleStage.COLLAPSE: 5,
}


def _derive_conviction(trend_strength: Decimal, momentum: int) -> Decimal:
    """Derive conviction score (0.0 - 1.0) from trend strength and momentum.

    - Trend strength provides the base score.
    - Positive momentum adds a bonus; negative momentum applies a penalty.
    - Result is clamped to [0.0, 1.0].
    """
    MOMENTUM_DELTA = Decimal("0.1")
    base = trend_strength
    if momentum > 0:
        base = base + MOMENTUM_DELTA
    elif momentum < 0:
        base = base - MOMENTUM_DELTA
    return max(Decimal("0.0"), min(Decimal("1.0"), base)).quantize(
        _FOUR_PLACES, rounding=ROUND_HALF_UP
    )


def _derive_asymmetry_ratio(
    volatility: Decimal,
    stage: CycleStage,
    conviction: Decimal,
) -> Decimal:
    """Derive asymmetry ratio from volatility and cycle stage position.

    Early stages with high conviction and lower volatility produce a better
    asymmetry ratio (more upside relative to downside).

    Formula rationale:
      - Base potential upside: conviction * 2.0  (e.g. 0.7 -> 1.4x move)
      - Base potential downside: volatility * (1 + stage_ordinal * 0.2)
        Later stages have higher downside because trend is more extended.
      - asymmetry_ratio = upside / downside, floored at 0.
    """
    stage_ordinal = Decimal(str(_STAGE_ORDINAL[stage]))
    potential_upside = conviction * Decimal("2.0")
    downside_factor = Decimal("1") + stage_ordinal * Decimal("0.2")
    potential_downside = volatility * downside_factor

    if potential_downside == Decimal("0"):
        # Avoid division by zero; return a high ratio for zero-risk scenarios
        return Decimal("10.0")

    ratio = (potential_upside / potential_downside).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return max(Decimal("0.0"), ratio)


def _derive_perception_reality_gap(
    trend_strength: Decimal,
    stage: CycleStage,
) -> Decimal:
    """Estimate perception-reality gap magnitude.

    In early stages the gap is small (market hasn't noticed yet).
    In EUPHORIA/TWILIGHT/COLLAPSE the gap is large (crowd is wrong).
    """
    stage_ordinal = _STAGE_ORDINAL[stage]
    # Map ordinal 0-5 to a factor 0.0-1.0
    gap = trend_strength * Decimal(str(stage_ordinal)) / Decimal("5")
    return gap.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)


def _build_feedback_loop_description(stage: CycleStage, momentum: int) -> str:
    """Build a short human-readable feedback loop description."""
    direction = "positive" if momentum >= 0 else "negative"
    return (
        f"Stage {stage.value}: {direction} reflexive feedback loop active. "
        "Perception is influencing reality through capital flows, sentiment "
        "shifts, and self-fulfilling expectations."
    )


def _build_invalidation_triggers(stage: CycleStage) -> list[str]:
    """Return a list of stage-appropriate invalidation triggers."""
    common = [
        "Significant earnings miss or guidance cut",
        "Macro regime shift (rapid rate change, recession signal)",
        "Regulatory action or sector-wide scandal",
    ]
    stage_specific: dict[CycleStage, list[str]] = {
        CycleStage.INCEPTION: [
            "Trend fails to gain institutional adoption within 30 days",
            "Volume remains below average for 3 consecutive weeks",
        ],
        CycleStage.ACCELERATION: [
            "Price closes below 20-day moving average on elevated volume",
            "Momentum divergence: price higher but relative strength declining",
        ],
        CycleStage.TESTING: [
            "Support level breaks on above-average volume",
            "Failed rally attempt with declining volume",
        ],
        CycleStage.EUPHORIA: [
            "Any sustained price weakness (bull thesis already fragile)",
            "Insider selling spike or lockup expiration",
        ],
        CycleStage.TWILIGHT: [
            "Failure to reclaim prior highs within 2 weeks",
            "Increased short interest with declining borrow cost",
        ],
        CycleStage.COLLAPSE: [
            "No fundamental catalyst for stabilization",
            "Continued deterioration in credit spreads or funding markets",
        ],
    }
    return stage_specific.get(stage, []) + common


def calculate_position_size(
    conviction: Decimal,
    volatility: Decimal,
    portfolio_value: Decimal,
    max_risk_pct: Decimal = Decimal("0.02"),
) -> Decimal:
    """Calculate recommended position size as a fraction of portfolio.

    Uses a simplified Kelly-inspired approach:
      - Scales with conviction (higher conviction -> larger size)
      - Scales inversely with volatility (more volatile -> smaller size)
      - Capped at max_risk_pct of portfolio value

    Args:
        conviction: 0.0-1.0 thesis conviction score.
        volatility: 0.0-1.0 normalized volatility.
        portfolio_value: Total portfolio value in base currency.
        max_risk_pct: Maximum fraction of portfolio to risk (default 2%).

    Returns:
        Recommended position size in base currency units.
    """
    if volatility == Decimal("0"):
        volatility = Decimal("0.01")  # floor to avoid division by zero

    # Kelly fraction: conviction / volatility, capped at max_risk_pct
    kelly_fraction = conviction / (volatility * Decimal("10"))
    capped_fraction = min(kelly_fraction, max_risk_pct)
    position_size = (portfolio_value * capped_fraction).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return position_size


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_rule_based_thesis(
    symbol: str,
    analysis: CycleAnalysis,
    current_price: Decimal,
    portfolio_value: Decimal = Decimal("1000000"),
    max_risk_pct: Decimal = Decimal("0.02"),
) -> MarketThesis:
    """Build a rule-based MarketThesis from a CycleAnalysis.

    All numeric fields are derived deterministically from the CycleAnalysis
    metrics. Narrative fields are populated from _STAGE_NARRATIVES templates,
    which can be overridden at the module level before calling this function
    (Phase 5 LLM integration point).

    Args:
        symbol: Ticker symbol (e.g. "005930").
        analysis: CycleAnalysis produced by BoomBustCycleDetector.
        current_price: Current market price of the asset.
        portfolio_value: Total portfolio size for position sizing (default 1M).
        max_risk_pct: Maximum fraction of portfolio to risk per trade.

    Returns:
        A populated MarketThesis dataclass instance.
    """
    stage = analysis.stage
    narratives = _STAGE_NARRATIVES[stage]

    # --- Derive numeric reflexivity metrics ---
    conviction = _derive_conviction(analysis.trend_strength, analysis.momentum)
    asymmetry_ratio = _derive_asymmetry_ratio(analysis.volatility, stage, conviction)
    perception_reality_gap = _derive_perception_reality_gap(
        analysis.trend_strength, stage
    )

    # Feedback strength mirrors trend_strength (how strongly perception
    # is looping back into reality via capital flows and sentiment).
    feedback_strength = analysis.trend_strength.quantize(
        _FOUR_PLACES, rounding=ROUND_HALF_UP
    )

    # Asymmetric payoff estimates expressed as price multiples
    # upside = current_price * (conviction * 2)
    # downside = current_price * volatility
    potential_upside = (current_price * conviction * Decimal("2")).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )
    potential_downside = (current_price * analysis.volatility).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )

    # Position sizing (Kelly-inspired, capped at max_risk_pct of portfolio_value).
    # Only calculated for valid entry stages; stored as context but not in MarketThesis
    # fields (Phase 5 will surface this via LLM recommendations).
    _ = (
        calculate_position_size(conviction, analysis.volatility, portfolio_value, max_risk_pct)
        if stage in _VALID_ENTRY_STAGES
        else Decimal("0")
    )

    return MarketThesis(
        symbol=symbol,
        # Narrative fields from stage templates
        perception=narratives["narrative"],
        reality=narratives["risk_assessment"],
        feedback_loop=_build_feedback_loop_description(stage, analysis.momentum),
        prediction=narratives["opportunity"],
        # Reflexivity metrics
        perception_reality_gap=perception_reality_gap,
        feedback_strength=feedback_strength,
        cycle_stage=stage,
        # Invalidation
        invalidation_triggers=_build_invalidation_triggers(stage),
        # Asymmetric payoff
        potential_upside=potential_upside,
        potential_downside=potential_downside,
        asymmetry_ratio=asymmetry_ratio,
        conviction=conviction,
    )
