"""Unit tests for HybridPersonaWrapper and _apply_selective_llm_overlay."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from stock_manager.trading.llm.circuit_breaker import CircuitBreaker
from stock_manager.trading.llm.config import LLMConfig
from stock_manager.trading.personas.hybrid import HybridPersonaWrapper
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
from stock_manager.trading.personas.models import MarketSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="005930",
        name="Samsung",
        market="KOSPI",
        sector="Electronics",
        current_price=Decimal("70000"),
        sma_50=69000.0,
        rsi_14=60.0,
        adx_14=25.0,
        atr_14=1400.0,
        price_52w_high=Decimal("80000"),
        vkospi=16.0,
    )


def _make_cb() -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=5, cooldown_sec=10.0)


def _make_wrapper(base) -> HybridPersonaWrapper:
    return HybridPersonaWrapper(
        base_persona=base,
        circuit_breaker=_make_cb(),
        llm_config=LLMConfig(max_retries=1, timeout_sec=1.0),
    )


def _make_soros() -> SorosPersona:
    detector = MagicMock()
    from decimal import Decimal
    from stock_manager.trading.reflexivity.cycle_detector import CycleAnalysis
    from stock_manager.trading.reflexivity.thesis import CycleStage

    analysis = CycleAnalysis(
        stage=CycleStage.INCEPTION,
        trend_strength=Decimal("0.7"),
        volume_pattern="increasing",
        volatility=Decimal("0.3"),
        momentum=1,
    )
    detector.detect_stage_full.return_value = analysis
    return SorosPersona(detector=detector)


# ---------------------------------------------------------------------------
# Parametrized: all 10 personas
# ---------------------------------------------------------------------------

ALL_PERSONAS = [
    GrahamPersona(),
    BuffettPersona(),
    LynchPersona(),
    DalioPersona(),
    MungerPersona(),
    TempletonPersona(),
    LivermorePersona(),
    FisherPersona(),
    SimonsPersona(),
]


@pytest.mark.parametrize("base", ALL_PERSONAS, ids=lambda p: p.name)
def test_wrapper_delegates_name_and_category(base) -> None:
    wrapper = _make_wrapper(base)
    assert wrapper.name == base.name
    assert wrapper.category == base.category


@pytest.mark.parametrize("base", ALL_PERSONAS, ids=lambda p: p.name)
def test_wrapper_delegates_llm_trigger_rate(base) -> None:
    wrapper = _make_wrapper(base)
    assert wrapper.llm_trigger_rate == pytest.approx(base.llm_trigger_rate)


@pytest.mark.parametrize("base", ALL_PERSONAS, ids=lambda p: p.name)
def test_wrapper_delegates_screen_rule(base) -> None:
    snapshot = _make_snapshot()
    wrapper = _make_wrapper(base)
    base_vote = base.screen_rule(snapshot)
    wrapper_vote = wrapper.screen_rule(snapshot)
    assert wrapper_vote.action == base_vote.action
    assert wrapper_vote.conviction == pytest.approx(base_vote.conviction)
    assert wrapper_vote.criteria_met == base_vote.criteria_met


@pytest.mark.parametrize("base", ALL_PERSONAS, ids=lambda p: p.name)
def test_wrapper_delegates_should_trigger_llm(base) -> None:
    snapshot = _make_snapshot()
    wrapper = _make_wrapper(base)
    vote = base.screen_rule(snapshot)
    assert wrapper.should_trigger_llm(vote) == base.should_trigger_llm(vote)


# ---------------------------------------------------------------------------
# Soros: requires BoomBustCycleDetector mock
# ---------------------------------------------------------------------------


def test_soros_wrapper_delegates_name_and_category() -> None:
    soros = _make_soros()
    wrapper = _make_wrapper(soros)
    assert wrapper.name == "Soros"
    assert wrapper.category == soros.category


def test_soros_wrapper_delegates_screen_rule() -> None:
    soros = _make_soros()
    snapshot = _make_snapshot()
    wrapper = _make_wrapper(soros)
    base_vote = soros.screen_rule(snapshot)
    wrapper_vote = wrapper.screen_rule(snapshot)
    assert wrapper_vote.action == base_vote.action
    assert wrapper_vote.conviction == pytest.approx(base_vote.conviction)


# ---------------------------------------------------------------------------
# Simons: should_trigger_llm always False, LLM never called
# ---------------------------------------------------------------------------


def test_simons_wrapper_never_triggers_llm() -> None:
    simons = SimonsPersona()
    wrapper = _make_wrapper(simons)
    snapshot = _make_snapshot()
    vote = simons.screen_rule(snapshot)
    assert wrapper.should_trigger_llm(vote) is False
    assert wrapper.llm_trigger_rate == pytest.approx(0.0)


def test_simons_wrapper_evaluate_never_calls_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    simons = SimonsPersona()
    wrapper = _make_wrapper(simons)
    snapshot = _make_snapshot()

    called = []

    def _mock_query(**_kwargs):
        called.append(True)
        return "ACTION: BUY\nCONVICTION: 0.9\nREASONING: x"

    monkeypatch.setattr("stock_manager.trading.personas.hybrid.sync_persona_query", _mock_query)

    wrapper.evaluate(snapshot)
    assert called == [], "LLM should never be called for Simons"


# ---------------------------------------------------------------------------
# _apply_selective_llm_overlay: all personas become HybridPersonaWrapper
# ---------------------------------------------------------------------------


def _make_mock_strategy(personas: list):
    strategy = MagicMock()
    strategy.evaluator.personas = personas
    return strategy


def _make_consensus_mock(bases: list):
    """Create a mock that passes isinstance(x, ConsensusStrategy) with real evaluator attr."""
    from stock_manager.trading.strategies.consensus import ConsensusStrategy

    strategy = MagicMock(spec=ConsensusStrategy)
    evaluator = MagicMock()
    evaluator.personas = bases
    strategy.evaluator = evaluator
    return strategy


def test_apply_selective_llm_overlay_wraps_all_personas(monkeypatch: pytest.MonkeyPatch) -> None:
    from stock_manager.slack_bot.session_manager import SessionManager
    from stock_manager.trading.llm.config import InvocationCounter

    bases = [GrahamPersona(), BuffettPersona(), SimonsPersona()]
    strategy = _make_consensus_mock(bases)

    monkeypatch.setattr(
        "stock_manager.slack_bot.session_manager.SessionManager._build_hybrid_shared_resources",
        staticmethod(lambda: (LLMConfig(max_retries=1, timeout_sec=1.0), _make_cb(), InvocationCounter())),
    )

    SessionManager._apply_selective_llm_overlay(strategy)

    for persona in strategy.evaluator.personas:
        assert isinstance(persona, HybridPersonaWrapper)


def test_apply_selective_llm_overlay_shares_circuit_breaker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from stock_manager.slack_bot.session_manager import SessionManager
    from stock_manager.trading.llm.config import InvocationCounter

    shared_cb = _make_cb()
    shared_llm = LLMConfig(max_retries=1, timeout_sec=1.0)
    shared_counter = InvocationCounter()

    monkeypatch.setattr(
        "stock_manager.slack_bot.session_manager.SessionManager._build_hybrid_shared_resources",
        staticmethod(lambda: (shared_llm, shared_cb, shared_counter)),
    )

    bases = [GrahamPersona(), DalioPersona(), SimonsPersona()]
    strategy = _make_consensus_mock(bases)

    SessionManager._apply_selective_llm_overlay(strategy)

    circuit_breakers = [p._circuit_breaker for p in strategy.evaluator.personas]
    assert all(cb is shared_cb for cb in circuit_breakers)

    counters = [p._invocation_counter for p in strategy.evaluator.personas]
    assert all(c is shared_counter for c in counters)


def test_apply_selective_llm_overlay_requires_consensus_strategy() -> None:
    from stock_manager.slack_bot.session_manager import SessionManager

    strategy = MagicMock()  # not a ConsensusStrategy
    with pytest.raises(ValueError, match="consensus"):
        SessionManager._apply_selective_llm_overlay(strategy)


def test_apply_selective_llm_overlay_wraps_correct_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from stock_manager.slack_bot.session_manager import SessionManager
    from stock_manager.trading.llm.config import InvocationCounter

    monkeypatch.setattr(
        "stock_manager.slack_bot.session_manager.SessionManager._build_hybrid_shared_resources",
        staticmethod(lambda: (LLMConfig(), _make_cb(), InvocationCounter())),
    )

    bases = [GrahamPersona(), BuffettPersona(), LynchPersona(), DalioPersona()]
    strategy = _make_consensus_mock(bases)

    SessionManager._apply_selective_llm_overlay(strategy)

    assert len(strategy.evaluator.personas) == 4
    for persona in strategy.evaluator.personas:
        assert isinstance(persona, HybridPersonaWrapper)
