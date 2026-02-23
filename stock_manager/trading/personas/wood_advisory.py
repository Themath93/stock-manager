"""Cathie Wood advisory persona (10+1 non-binding innovation lens).

Provides an AdvisoryVote -- does NOT participate in the binding consensus.
Does NOT extend InvestorPersona.

Evaluates disruption potential through:
    - Innovation sector detection (technology, biotech, fintech, clean energy)
    - Revenue growth > 30% as disruption velocity proxy
    - Market adoption curve positioning (early / growth / mature)
    - Innovation score: 0.0-1.0 composite

Action is ALWAYS VoteAction.ADVISORY.
"""

from __future__ import annotations


from .models import (
    AdvisoryVote,
    MarketSnapshot,
    PersonaCategory,
    VoteAction,
)


# ---------------------------------------------------------------------------
# Innovation sector classification
# ---------------------------------------------------------------------------

_INNOVATION_SECTORS: set[str] = {
    # Technology
    "technology", "it", "software", "semiconductor", "electronics",
    "internet", "communication", "telecom", "platform",
    # Biotech / Healthcare
    "biotech", "biotechnology", "healthcare", "pharmaceutical", "pharma",
    "medical", "life sciences", "bio",
    # Fintech
    "fintech", "financial technology", "digital finance",
    # Clean Energy
    "energy", "clean energy", "solar", "renewable", "ev",
    "electric vehicle", "battery", "hydrogen",
    # Emerging
    "ai", "artificial intelligence", "robotics", "autonomous",
    "space", "quantum", "blockchain", "metaverse",
}

_REVENUE_GROWTH_DISRUPTION = 30.0  # Disruption velocity threshold (%)


def _classify_sector(sector: str) -> tuple[bool, float]:
    """Check if sector is innovation-related and return a sector score.

    Returns:
        (is_innovation, sector_score) where sector_score is 0.0-1.0.
    """
    if not sector:
        return False, 0.0
    sector_lower = sector.strip().lower()
    for keyword in _INNOVATION_SECTORS:
        if keyword in sector_lower:
            return True, 1.0
    return False, 0.0


def _assess_adoption_curve(snapshot: MarketSnapshot) -> tuple[str, float]:
    """Estimate where the company is on the market adoption curve.

    Returns:
        (stage_name, stage_score) where stage_score contributes to innovation.
    """
    growth = snapshot.revenue_growth_yoy
    margin = snapshot.operating_margin

    if growth > 50:
        # Hypergrowth: early stage disruption
        return "early", 1.0
    elif growth > 20:
        # Strong growth: growth stage
        return "growth", 0.7
    elif growth > 5:
        # Moderate: approaching maturity
        return "late_growth", 0.4
    else:
        # Mature or declining
        return "mature", 0.1


class WoodAdvisory:
    """Cathie Wood: innovation-focused advisory lens (non-binding).

    This is the +1 in the 10+1 persona model. The advisory vote does
    not count toward the binding consensus but provides innovation context.
    """

    name: str = "Wood"
    category: PersonaCategory = PersonaCategory.INNOVATION

    def evaluate(self, snapshot: MarketSnapshot) -> AdvisoryVote:
        """Evaluate disruption potential and return an advisory vote.

        The innovation_score is a weighted composite of:
            - Sector relevance (30%)
            - Revenue growth velocity (30%)
            - Adoption curve position (20%)
            - Margin trajectory (10%)
            - Earnings growth (10%)
        """
        # 1. Sector relevance
        is_innovation, sector_score = _classify_sector(snapshot.sector)

        # 2. Revenue growth velocity
        if snapshot.revenue_growth_yoy > _REVENUE_GROWTH_DISRUPTION:
            growth_score = min(snapshot.revenue_growth_yoy / 60.0, 1.0)
        elif snapshot.revenue_growth_yoy > 15:
            growth_score = snapshot.revenue_growth_yoy / 60.0
        else:
            growth_score = max(snapshot.revenue_growth_yoy / 60.0, 0.0)

        # 3. Adoption curve
        adoption_stage, adoption_score = _assess_adoption_curve(snapshot)

        # 4. Margin trajectory (positive margin = execution capability)
        margin_score = 0.0
        if snapshot.operating_margin > 20:
            margin_score = 1.0
        elif snapshot.operating_margin > 0:
            margin_score = snapshot.operating_margin / 20.0
        # Negative margins acceptable for early-stage disruptors
        elif is_innovation and snapshot.revenue_growth_yoy > 30:
            margin_score = 0.3  # Burning cash but growing fast

        # 5. Earnings growth
        earnings_score = 0.0
        if snapshot.earnings_growth_yoy > 30:
            earnings_score = 1.0
        elif snapshot.earnings_growth_yoy > 0:
            earnings_score = snapshot.earnings_growth_yoy / 30.0

        # --- Composite innovation score ---
        innovation_score = (
            sector_score * 0.30
            + growth_score * 0.30
            + adoption_score * 0.20
            + margin_score * 0.10
            + earnings_score * 0.10
        )
        innovation_score = round(min(max(innovation_score, 0.0), 1.0), 4)

        # --- Disruption assessment ---
        if innovation_score >= 0.7:
            disruption_assessment = (
                f"High disruption potential ({adoption_stage} stage). "
                f"Innovation sector with {snapshot.revenue_growth_yoy:.1f}% "
                f"revenue growth. Wood would allocate significantly."
            )
        elif innovation_score >= 0.4:
            disruption_assessment = (
                f"Moderate disruption potential ({adoption_stage} stage). "
                f"Some innovation characteristics with "
                f"{snapshot.revenue_growth_yoy:.1f}% revenue growth. "
                "Worth monitoring for acceleration."
            )
        else:
            disruption_assessment = (
                f"Low disruption signal ({adoption_stage} stage). "
                "Traditional business model without strong innovation markers. "
                "Not a Wood-style opportunity."
            )

        return AdvisoryVote(
            persona_name=self.name,
            action=VoteAction.ADVISORY,
            innovation_score=innovation_score,
            disruption_assessment=disruption_assessment,
            category=self.category,
        )
