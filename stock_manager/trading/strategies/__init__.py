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
from stock_manager.trading.strategies.consensus import ConsensusScore, ConsensusStrategy
from stock_manager.trading.strategies.graham import (
    GrahamScreener,
    DefensiveGrahamScore,
    calculate_ncav_per_share,
    calculate_margin_of_safety,
)


def _normalize_strategy_name(value: str) -> str:
    return "".join(char for char in value.lower().strip() if char.isalnum())


def _build_consensus_strategy(client: Any) -> ConsensusStrategy:
    from stock_manager.trading.consensus.aggregator import VoteAggregator
    from stock_manager.trading.consensus.evaluator import ConsensusEvaluator
    from stock_manager.trading.indicators.fetcher import TechnicalDataFetcher
    from stock_manager.trading.personas.buffett_persona import BuffettPersona
    from stock_manager.trading.personas.dalio_persona import DalioPersona
    from stock_manager.trading.personas.fisher_persona import FisherPersona
    from stock_manager.trading.personas.graham_persona import GrahamPersona
    from stock_manager.trading.personas.livermore_persona import LivermorePersona
    from stock_manager.trading.personas.lynch_persona import LynchPersona
    from stock_manager.trading.personas.munger_persona import MungerPersona
    from stock_manager.trading.personas.simons_persona import SimonsPersona
    from stock_manager.trading.personas.soros_persona import SorosPersona
    from stock_manager.trading.personas.templeton_persona import TempletonPersona
    from stock_manager.trading.personas.wood_advisory import WoodAdvisory
    from stock_manager.trading.reflexivity.cycle_detector import BoomBustCycleDetector

    personas = [
        BuffettPersona(),
        GrahamPersona(),
        LynchPersona(),
        MungerPersona(),
        DalioPersona(),
        SorosPersona(detector=BoomBustCycleDetector(client)),
        FisherPersona(),
        TempletonPersona(),
        LivermorePersona(),
        SimonsPersona(),
    ]
    evaluator = ConsensusEvaluator(
        personas=personas,
        advisory=WoodAdvisory(),
        fetcher=TechnicalDataFetcher(client),
        aggregator=VoteAggregator(),
    )
    return ConsensusStrategy(evaluator=evaluator)


_STRATEGY_FACTORIES: dict[str, Callable[[Any], Strategy]] = {
    "graham": lambda client: GrahamScreener(client=client, market="KOSPI"),
    "grahamscreener": lambda client: GrahamScreener(client=client, market="KOSPI"),
    "consensus": _build_consensus_strategy,
    "consensusstrategy": _build_consensus_strategy,
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
    "ConsensusStrategy",
    "ConsensusScore",
    "GrahamScreener",
    "DefensiveGrahamScore",
    "calculate_ncav_per_share",
    "calculate_margin_of_safety",
    "get_available_strategy_names",
    "resolve_strategy",
]
