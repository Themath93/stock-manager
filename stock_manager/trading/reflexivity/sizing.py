"""Conviction-based asymmetric position sizing."""

from decimal import Decimal
from .thesis import MarketThesis

def calculate_position_size(
    thesis: MarketThesis,
    portfolio_value: Decimal,
    max_position_pct: Decimal = Decimal("0.10")
) -> Decimal:
    """
    Conviction-based position sizing.

    Soros Principle: Size based on opportunity quality, not arbitrary limits.

    Formula:
    base_size = portfolio_value * max_position_pct
    conviction_multiplier = thesis.conviction (0.0-1.0)
    asymmetry_multiplier = min(thesis.asymmetry_ratio / 3.0, 2.0)

    final_size = base_size * conviction_multiplier * asymmetry_multiplier
    """
    base_size = portfolio_value * max_position_pct
    conviction_mult = thesis.conviction
    asymmetry_mult = min(thesis.asymmetry_ratio / Decimal("3.0"), Decimal("2.0"))
    return base_size * conviction_mult * asymmetry_mult
