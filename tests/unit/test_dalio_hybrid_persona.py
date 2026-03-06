"""Unit tests for DalioHybridPersona."""

from __future__ import annotations

from decimal import Decimal

import pytest

from stock_manager.trading.llm.circuit_breaker import CircuitBreaker
from stock_manager.trading.llm.config import LLMConfig
from stock_manager.trading.personas.dalio_hybrid_persona import DalioHybridPersona
from stock_manager.trading.personas.dalio_persona import DalioPersona
from stock_manager.trading.personas.models import MarketSnapshot, PersonaVote, VoteAction


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


def _make_hybrid(base: DalioPersona | None = None) -> DalioHybridPersona:
    return DalioHybridPersona(
        base_persona=base,
        circuit_breaker=CircuitBreaker(failure_threshold=5, cooldown_sec=10.0),
        llm_config=LLMConfig(max_retries=1, timeout_sec=1.0),
    )


def test_screen_rule_delegates_to_base_dalio() -> None:
    base = DalioPersona()
    hybrid = _make_hybrid(base)
    snapshot = _make_snapshot()

    base_vote = base.screen_rule(snapshot)
    hybrid_vote = hybrid.screen_rule(snapshot)

    assert hybrid_vote.action == base_vote.action
    assert hybrid_vote.conviction == base_vote.conviction
    assert hybrid_vote.criteria_met == base_vote.criteria_met


def test_should_trigger_llm_delegates_to_base_policy() -> None:
    base = DalioPersona()
    hybrid = _make_hybrid(base)
    vote = PersonaVote(
        persona_name="Dalio",
        action=VoteAction.HOLD,
        conviction=0.4,
        reasoning="test",
        criteria_met={
            "sector_correlation_low": True,
            "volatility_in_band": True,
            "not_overbought": False,
            "trend_alignment": False,
            "risk_reward_favorable": False,
        },
        category=base.category,
    )

    assert hybrid.should_trigger_llm(vote) is base.should_trigger_llm(vote)
    assert hybrid.llm_trigger_rate == pytest.approx(base.llm_trigger_rate)


def test_evaluate_merges_llm_vote_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    hybrid = _make_hybrid()
    snapshot = _make_snapshot()
    monkeypatch.setattr(hybrid, "should_trigger_llm", lambda _vote: True)
    monkeypatch.setattr(
        "stock_manager.trading.personas.hybrid.load_persona_prompt",
        lambda _persona_name: "You are Dalio.",
    )
    monkeypatch.setattr(
        "stock_manager.trading.personas.hybrid.sync_persona_query",
        lambda **_kwargs: "ACTION: SELL\nCONVICTION: 0.9\nREASONING: downside risk",
    )

    vote = hybrid.evaluate(snapshot)
    rule_vote = hybrid.screen_rule(snapshot)

    assert vote.action == VoteAction.SELL
    assert vote.conviction == pytest.approx(min(0.9, rule_vote.conviction) * 0.8)
    assert "LLM override" in vote.reasoning


def test_evaluate_falls_back_to_rule_vote_when_llm_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hybrid = _make_hybrid()
    snapshot = _make_snapshot()
    monkeypatch.setattr(hybrid, "should_trigger_llm", lambda _vote: True)
    monkeypatch.setattr(
        "stock_manager.trading.personas.hybrid.load_persona_prompt",
        lambda _persona_name: "You are Dalio.",
    )

    def _raise_query_error(**_kwargs):
        raise RuntimeError("sdk unavailable")

    monkeypatch.setattr(
        "stock_manager.trading.personas.hybrid.sync_persona_query",
        _raise_query_error,
    )

    vote = hybrid.evaluate(snapshot)
    rule_vote = hybrid.screen_rule(snapshot)

    assert vote.action == rule_vote.action
    assert vote.conviction == rule_vote.conviction
    assert vote.reasoning == rule_vote.reasoning
