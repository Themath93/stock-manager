"""Negative quality test: verify bad stocks are rejected by consensus."""
from decimal import Decimal
from datetime import datetime, timezone
import pytest

from stock_manager.trading.personas.models import (
    MarketSnapshot, PersonaVote, VoteAction, PersonaCategory, ConsensusResult,
)
from stock_manager.trading.consensus.aggregator import VoteAggregator


def _make_bad_snapshot() -> MarketSnapshot:
    """A stock with terrible fundamentals that must be rejected."""
    return MarketSnapshot(
        symbol="BAD001",
        name="BadCorp",
        market="KRX",
        timestamp=datetime.now(timezone.utc),
        current_price=Decimal("5000"),
        per=-10.0,
        pbr=3.0,
        eps=Decimal("-500"),
        dividend_yield=0.0,
        roe=-5.0,
        current_ratio=0.5,
        debt_to_equity=5.0,
        operating_margin=-10.0,
        net_margin=-15.0,
        free_cash_flow=Decimal("-100000000"),
        revenue_growth_yoy=-20.0,
        earnings_growth_yoy=-30.0,
        sma_20=6000.0,
        sma_50=7000.0,
        sma_200=8000.0,
        rsi_14=25.0,
        macd_signal=-0.5,
        bollinger_position=0.1,
        adx_14=15.0,
        atr_14=200.0,
        price_52w_high=Decimal("15000"),
        price_52w_low=Decimal("4000"),
        years_positive_earnings=0,
        years_dividends_paid=0,
        market_cap=Decimal("100000000000"),
    )


def test_bad_stock_gets_few_buy_votes():
    """A terrible stock should receive at most 2 BUY votes."""
    # Import all personas
    from stock_manager.trading.personas.graham_persona import GrahamPersona
    from stock_manager.trading.personas.buffett_persona import BuffettPersona
    from stock_manager.trading.personas.dalio_persona import DalioPersona
    from stock_manager.trading.personas.lynch_persona import LynchPersona
    from stock_manager.trading.personas.fisher_persona import FisherPersona
    from stock_manager.trading.personas.templeton_persona import TempletonPersona
    from stock_manager.trading.personas.simons_persona import SimonsPersona
    from stock_manager.trading.personas.soros_persona import SorosPersona
    from stock_manager.trading.personas.livermore_persona import LivermorePersona
    from stock_manager.trading.personas.munger_persona import MungerPersona
    from stock_manager.trading.reflexivity.cycle_detector import CycleAnalysis
    from stock_manager.trading.reflexivity.thesis import CycleStage
    from unittest.mock import MagicMock

    mock_detector = MagicMock()
    mock_detector.detect_stage_full.return_value = CycleAnalysis(
        stage=CycleStage.COLLAPSE,
        trend_strength=Decimal("0.1"),
        volume_pattern="decreasing",
        volatility=Decimal("0.9"),
        momentum=-1,
    )
    personas = [
        GrahamPersona(), BuffettPersona(), DalioPersona(), LynchPersona(),
        FisherPersona(), TempletonPersona(), SimonsPersona(), SorosPersona(mock_detector),
        LivermorePersona(), MungerPersona(),
    ]

    snapshot = _make_bad_snapshot()
    votes = [p.screen_rule(snapshot) for p in personas]

    buy_count = sum(1 for v in votes if v.action == VoteAction.BUY)
    assert buy_count <= 2, f"Bad stock got {buy_count} BUY votes, expected at most 2"


def test_bad_stock_rejected_by_consensus():
    """Bad stock must NOT pass the consensus threshold."""
    from stock_manager.trading.personas.graham_persona import GrahamPersona
    from stock_manager.trading.personas.buffett_persona import BuffettPersona
    from stock_manager.trading.personas.dalio_persona import DalioPersona
    from stock_manager.trading.personas.lynch_persona import LynchPersona
    from stock_manager.trading.personas.fisher_persona import FisherPersona
    from stock_manager.trading.personas.templeton_persona import TempletonPersona
    from stock_manager.trading.personas.simons_persona import SimonsPersona
    from stock_manager.trading.personas.soros_persona import SorosPersona
    from stock_manager.trading.personas.livermore_persona import LivermorePersona
    from stock_manager.trading.personas.munger_persona import MungerPersona
    from stock_manager.trading.reflexivity.cycle_detector import CycleAnalysis
    from stock_manager.trading.reflexivity.thesis import CycleStage
    from unittest.mock import MagicMock

    mock_detector = MagicMock()
    mock_detector.detect_stage_full.return_value = CycleAnalysis(
        stage=CycleStage.COLLAPSE,
        trend_strength=Decimal("0.1"),
        volume_pattern="decreasing",
        volatility=Decimal("0.9"),
        momentum=-1,
    )
    personas = [
        GrahamPersona(), BuffettPersona(), DalioPersona(), LynchPersona(),
        FisherPersona(), TempletonPersona(), SimonsPersona(), SorosPersona(mock_detector),
        LivermorePersona(), MungerPersona(),
    ]

    snapshot = _make_bad_snapshot()
    votes = [p.screen_rule(snapshot) for p in personas]

    aggregator = VoteAggregator()  # Uses new defaults: threshold=6, quorum=0.70, etc.
    result = aggregator.aggregate(votes)
    assert not result.passes_threshold, "Bad stock should NOT pass consensus"
