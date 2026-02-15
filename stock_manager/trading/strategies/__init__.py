"""
Trading strategies module.

Implements various investment strategies including:
- Graham's Defensive Investor (7 criteria)
- Value investing strategies
- Growth strategies
"""

from __future__ import annotations

from collections.abc import Callable

from typing import Any

from stock_manager.trading.strategies.base import Strategy, StrategyScore
from stock_manager.trading.strategies.graham import (
    GrahamScreener,
    DefensiveGrahamScore,
    calculate_ncav_per_share,
    calculate_margin_of_safety,
)


def _normalize_strategy_name(value: str) -> str:
    return "".join(char for char in value.lower().strip() if char.isalnum())


_STRATEGY_FACTORIES: dict[str, Callable[[Any], Strategy]] = {
    "graham": lambda client: GrahamScreener(client=client, market="KOSPI"),
    "grahamscreener": lambda client: GrahamScreener(client=client, market="KOSPI"),
}


def get_available_strategy_names() -> tuple[str, ...]:
    return tuple(sorted(_STRATEGY_FACTORIES))


def resolve_strategy(strategy_name: str, *, client: Any) -> Strategy:
    normalized_name = _normalize_strategy_name(strategy_name)
    try:
        factory = _STRATEGY_FACTORIES[normalized_name]
    except KeyError as exc:
        available = ", ".join(get_available_strategy_names())
        raise ValueError(
            f"Unknown strategy '{strategy_name}'. Available strategies: {available}"
        ) from exc

    return factory(client)


__all__ = [
    "Strategy",
    "StrategyScore",
    "GrahamScreener",
    "DefensiveGrahamScore",
    "calculate_ncav_per_share",
    "calculate_margin_of_safety",
    "get_available_strategy_names",
    "resolve_strategy",
]
