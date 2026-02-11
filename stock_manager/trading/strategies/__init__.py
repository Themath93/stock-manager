"""
Trading strategies module.

Implements various investment strategies including:
- Graham's Defensive Investor (7 criteria)
- Value investing strategies
- Growth strategies
"""

from stock_manager.trading.strategies.base import Strategy, StrategyScore
from stock_manager.trading.strategies.graham import (
    GrahamScreener,
    DefensiveGrahamScore,
    calculate_ncav_per_share,
    calculate_margin_of_safety,
)

__all__ = [
    "Strategy",
    "StrategyScore",
    "GrahamScreener",
    "DefensiveGrahamScore",
    "calculate_ncav_per_share",
    "calculate_margin_of_safety",
]
