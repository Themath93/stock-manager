from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from stock_manager.trading.personas.base import InvestorPersona
from stock_manager.trading.personas.buffett_persona import BuffettPersona
from stock_manager.trading.personas.dalio_persona import DalioPersona
from stock_manager.trading.personas.fisher_persona import FisherPersona
from stock_manager.trading.personas.graham_persona import GrahamPersona
from stock_manager.trading.personas.livermore_persona import LivermorePersona
from stock_manager.trading.personas.lynch_persona import LynchPersona, _classify_stock
from stock_manager.trading.personas.models import (
    MarketSnapshot,
    PersonaCategory,
    PersonaVote,
    VoteAction,
)
from stock_manager.trading.personas.munger_persona import MungerPersona
from stock_manager.trading.personas.prompts import prompt_loader
from stock_manager.trading.personas.simons_persona import SimonsPersona
from stock_manager.trading.personas.soros_persona import SorosPersona
from stock_manager.trading.personas.templeton_persona import TempletonPersona
from stock_manager.trading.personas.wood_advisory import (
    WoodAdvisory,
    _assess_adoption_curve,
    _classify_sector,
)
from stock_manager.trading.reflexivity.cycle_detector import BoomBustCycleDetector, CycleAnalysis
from stock_manager.trading.reflexivity.thesis import CycleStage, MarketThesis


def _make_snapshot(**overrides: Any) -> MarketSnapshot:
    payload: dict[str, Any] = {
        "symbol": "005930",
        "name": "Samsung",
        "market": "KOSPI",
        "sector": "technology",
        "timestamp": datetime(2026, 1, 1),
        "current_price": Decimal("100"),
        "open_price": Decimal("98"),
        "high_price": Decimal("101"),
        "low_price": Decimal("97"),
        "prev_close": Decimal("99"),
        "volume": 2500,
        "avg_volume_20d": 1000,
        "market_cap": Decimal("3000000000000"),
        "per": 10.0,
        "pbr": 1.0,
        "eps": Decimal("10"),
        "bps": Decimal("100"),
        "dividend_yield": 3.0,
        "roe": 25.0,
        "current_ratio": 2.5,
        "debt_to_equity": 0.2,
        "operating_margin": 25.0,
        "net_margin": 15.0,
        "free_cash_flow": Decimal("100"),
        "revenue_growth_yoy": 35.0,
        "earnings_growth_yoy": 30.0,
        "revenue_growth_3yr": 20.0,
        "earnings_growth_3yr": 18.0,
        "sma_20": 110.0,
        "sma_50": 95.0,
        "sma_200": 90.0,
        "rsi_14": 55.0,
        "macd_signal": 1.0,
        "bollinger_position": 0.02,
        "adx_14": 30.0,
        "atr_14": 2.0,
        "total_assets": Decimal("1000"),
        "total_liabilities": Decimal("300"),
        "current_assets": Decimal("500"),
        "cash_and_equivalents": Decimal("120"),
        "inventory": Decimal("100"),
        "accounts_receivable": Decimal("100"),
        "shares_outstanding": 1_000_000,
        "price_52w_high": Decimal("160"),
        "price_52w_low": Decimal("80"),
        "years_positive_earnings": 12,
        "years_dividends_paid": 25,
        "kospi_index": Decimal("2700"),
        "kospi_per": 12.0,
        "market_sentiment": "neutral",
        "vkospi": 20.0,
    }
    payload.update(overrides)
    return MarketSnapshot(**payload)


def _make_vote(action: VoteAction, conviction: float, passed: int, total: int = 5) -> PersonaVote:
    criteria = {f"k{i}": i < passed for i in range(total)}
    return PersonaVote(
        persona_name="P",
        action=action,
        conviction=conviction,
        reasoning="r",
        criteria_met=criteria,
        category=PersonaCategory.VALUE,
    )


def _make_analysis(stage: CycleStage) -> CycleAnalysis:
    return CycleAnalysis(
        stage=stage,
        trend_strength=Decimal("0.8"),
        volume_pattern="increasing",
        volatility=Decimal("0.3"),
        momentum=1,
    )


def _make_thesis(
    *,
    stage: CycleStage,
    gap: Decimal,
    asymmetry: Decimal,
    conviction: Decimal,
    feedback: Decimal,
) -> MarketThesis:
    return MarketThesis(
        symbol="005930",
        perception="p",
        reality="r",
        feedback_loop="f",
        prediction="x",
        perception_reality_gap=gap,
        feedback_strength=feedback,
        cycle_stage=stage,
        asymmetry_ratio=asymmetry,
        conviction=conviction,
    )


def test_investor_persona_base_defaults() -> None:
    class DummyPersona(InvestorPersona):
        name = "Dummy"
        category = PersonaCategory.VALUE

        def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
            return PersonaVote(
                persona_name=self.name,
                action=VoteAction.HOLD,
                conviction=0.5,
                reasoning=snapshot.symbol,
                criteria_met={"ok": True},
                category=self.category,
            )

    persona = DummyPersona()
    vote = persona.evaluate(_make_snapshot())
    assert vote.action == VoteAction.HOLD
    assert persona.llm_trigger_rate == 0.0
    assert persona.should_trigger_llm(vote) is False


def test_buffett_persona_paths() -> None:
    persona = BuffettPersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    mid_vote = persona.screen_rule(
        _make_snapshot(
            net_margin=25.0,
            years_positive_earnings=8,
            free_cash_flow=Decimal("-1"),
            years_dividends_paid=1,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            roe=5.0,
            debt_to_equity=2.0,
            net_margin=2.0,
            years_positive_earnings=1,
            free_cash_flow=Decimal("-10"),
            years_dividends_paid=0,
            operating_margin=2.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert mid_vote.action == VoteAction.BUY
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(mid_vote) is True
    assert persona.llm_trigger_rate == 0.20


def test_dalio_persona_paths() -> None:
    persona = DalioPersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    hold_vote = persona.screen_rule(
        _make_snapshot(
            vkospi=50.0,
            atr_14=2.0,
            rsi_14=75.0,
            adx_14=10.0,
            price_52w_high=Decimal("102"),
            sma_50=200.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            vkospi=90.0,
            atr_14=0.0,
            rsi_14=90.0,
            adx_14=5.0,
            price_52w_high=Decimal("101"),
            sma_50=200.0,
        )
    )
    neutral_vote = _make_vote(VoteAction.HOLD, 0.4, passed=2, total=5)

    assert buy_vote.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(neutral_vote) is True
    assert persona.llm_trigger_rate == 0.10
    assert persona.screen_rule(_make_snapshot(vkospi=None)).action in {
        VoteAction.BUY,
        VoteAction.HOLD,
    }


def test_fisher_persona_paths() -> None:
    persona = FisherPersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    hold_vote = persona.screen_rule(
        _make_snapshot(
            revenue_growth_yoy=16.0,
            operating_margin=6.0,
            net_margin=8.0,
            debt_to_equity=0.8,
            roe=10.0,
            earnings_growth_yoy=1.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            revenue_growth_yoy=-5.0,
            operating_margin=0.0,
            net_margin=-1.0,
            debt_to_equity=2.0,
            roe=2.0,
            earnings_growth_yoy=-10.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(_make_vote(VoteAction.HOLD, 0.5, passed=4, total=6)) is True


def test_graham_persona_paths() -> None:
    persona = GrahamPersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    borderline_vote = persona.screen_rule(
        _make_snapshot(
            years_dividends_paid=5,
            per=20.0,
        )
    )
    hold_vote = persona.screen_rule(
        _make_snapshot(
            market_cap=Decimal("3000000000000"),
            current_ratio=2.1,
            debt_to_equity=0.9,
            years_positive_earnings=0,
            years_dividends_paid=0,
            earnings_growth_yoy=3.0,
            per=30.0,
            pbr=2.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            market_cap=Decimal("100"),
            current_ratio=0.1,
            debt_to_equity=10.0,
            years_positive_earnings=0,
            years_dividends_paid=0,
            earnings_growth_yoy=-10.0,
            per=100.0,
            pbr=10.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert borderline_vote.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(borderline_vote) is True


def test_livermore_persona_paths() -> None:
    persona = LivermorePersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    mixed_vote = persona.screen_rule(
        _make_snapshot(
            current_price=Decimal("130"),
            sma_200=120.0,
            macd_signal=-0.5,
            rsi_14=50.0,
            volume=1300,
            avg_volume_20d=1000,
            sma_20=130.0,
            sma_50=120.0,
            adx_14=20.0,
        )
    )
    bearish_vote = persona.screen_rule(
        _make_snapshot(
            current_price=Decimal("80"),
            sma_200=120.0,
            macd_signal=-1.0,
            rsi_14=80.0,
            volume=100,
            avg_volume_20d=1000,
            sma_20=80.0,
            sma_50=120.0,
            adx_14=5.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert mixed_vote.action == VoteAction.HOLD
    assert bearish_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(_make_vote(VoteAction.HOLD, 0.5, passed=3, total=6)) is True


def test_lynch_classification_and_paths() -> None:
    persona = LynchPersona()

    assert _classify_stock(_make_snapshot(earnings_growth_yoy=25.0)) == "fast_grower"
    assert _classify_stock(_make_snapshot(earnings_growth_yoy=15.0)) == "stalwart"
    assert (
        _classify_stock(_make_snapshot(earnings_growth_yoy=-1.0, revenue_growth_yoy=5.0))
        == "turnaround"
    )
    assert (
        _classify_stock(_make_snapshot(earnings_growth_yoy=1.0, revenue_growth_yoy=1.0))
        == "cyclical"
    )

    buy_vote = persona.screen_rule(_make_snapshot())
    buy_low_conviction = persona.screen_rule(
        _make_snapshot(
            earnings_growth_yoy=22.0,
            per=18.0,
            kospi_per=15.0,
            revenue_growth_yoy=12.0,
            pbr=2.0,
        )
    )
    hold_vote = persona.screen_rule(
        _make_snapshot(
            earnings_growth_yoy=12.0,
            per=20.0,
            kospi_per=15.0,
            revenue_growth_yoy=12.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            earnings_growth_yoy=-20.0,
            revenue_growth_yoy=-10.0,
            per=50.0,
            kospi_per=10.0,
            pbr=5.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert buy_low_conviction.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(_make_vote(VoteAction.HOLD, 0.4, passed=3, total=5)) is True


def test_munger_persona_paths() -> None:
    persona = MungerPersona()
    buy_vote = persona.screen_rule(_make_snapshot())
    hold_vote = persona.screen_rule(
        _make_snapshot(
            sector="unknown",
            per=30.0,
            pbr=4.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            total_assets=Decimal("0"),
            roe=0.0,
            sector="",
            per=100.0,
            pbr=100.0,
            operating_margin=-1.0,
            net_margin=-1.0,
            debt_to_equity=5.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(_make_vote(VoteAction.HOLD, 0.5, passed=3, total=6)) is True


def test_simons_persona_paths() -> None:
    persona = SimonsPersona()

    buy_vote = persona.screen_rule(
        _make_snapshot(
            current_price=Decimal("70"),
            sma_20=100.0,
            rsi_14=20.0,
            macd_signal=1.0,
            bollinger_position=0.0,
            volume=5000,
            avg_volume_20d=1000,
            price_52w_low=Decimal("65"),
            price_52w_high=Decimal("200"),
            earnings_growth_yoy=20.0,
        )
    )
    hold_vote = persona.screen_rule(_make_snapshot())
    sell_vote = persona.screen_rule(
        _make_snapshot(
            current_price=Decimal("200"),
            sma_20=100.0,
            rsi_14=80.0,
            macd_signal=-1.0,
            bollinger_position=0.9,
            volume=100,
            avg_volume_20d=1000,
            price_52w_low=Decimal("100"),
            price_52w_high=Decimal("200"),
            earnings_growth_yoy=-5.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert hold_vote.action in {VoteAction.HOLD, VoteAction.BUY}
    assert sell_vote.action == VoteAction.SELL
    assert persona.llm_trigger_rate == 0.0
    assert persona.should_trigger_llm(hold_vote) is False


def test_soros_persona_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDetector(BoomBustCycleDetector):
        def __init__(self, analysis: CycleAnalysis) -> None:
            super().__init__(client=None)
            self._analysis = analysis

        def detect_stage_full(self, symbol: str, lookback_days: int = 90) -> CycleAnalysis:
            _ = (symbol, lookback_days)
            return self._analysis

    buy_analysis = _make_analysis(CycleStage.INCEPTION)
    buy_thesis = _make_thesis(
        stage=CycleStage.INCEPTION,
        gap=Decimal("1.0"),
        asymmetry=Decimal("4.0"),
        conviction=Decimal("0.8"),
        feedback=Decimal("0.6"),
    )
    monkeypatch.setattr(
        "stock_manager.trading.personas.soros_persona.build_rule_based_thesis",
        lambda **_kwargs: buy_thesis,
    )
    buy_persona = SorosPersona(detector=FakeDetector(buy_analysis))
    buy_vote = buy_persona.screen_rule(_make_snapshot())

    sell_analysis = _make_analysis(CycleStage.EUPHORIA)
    sell_thesis = _make_thesis(
        stage=CycleStage.EUPHORIA,
        gap=Decimal("0"),
        asymmetry=Decimal("1.0"),
        conviction=Decimal("0.1"),
        feedback=Decimal("0.1"),
    )
    monkeypatch.setattr(
        "stock_manager.trading.personas.soros_persona.build_rule_based_thesis",
        lambda **_kwargs: sell_thesis,
    )
    sell_persona = SorosPersona(detector=FakeDetector(sell_analysis))
    sell_vote = sell_persona.screen_rule(_make_snapshot())

    abstain_analysis = _make_analysis(CycleStage.INCEPTION)
    abstain_thesis = _make_thesis(
        stage=CycleStage.INCEPTION,
        gap=Decimal("0"),
        asymmetry=Decimal("1.0"),
        conviction=Decimal("0.1"),
        feedback=Decimal("0.1"),
    )
    monkeypatch.setattr(
        "stock_manager.trading.personas.soros_persona.build_rule_based_thesis",
        lambda **_kwargs: abstain_thesis,
    )
    abstain_persona = SorosPersona(detector=FakeDetector(abstain_analysis))
    abstain_vote = abstain_persona.screen_rule(_make_snapshot())

    assert buy_vote.action == VoteAction.BUY
    assert sell_vote.action == VoteAction.SELL
    assert abstain_vote.action == VoteAction.ABSTAIN
    assert (
        buy_persona.should_trigger_llm(_make_vote(VoteAction.HOLD, 0.4, passed=2, total=5)) is True
    )


def test_templeton_persona_paths() -> None:
    persona = TempletonPersona()
    buy_vote = persona.screen_rule(_make_snapshot(
        pbr=0.5, per=7.0, dividend_yield=4.0,
        price_52w_high=Decimal("200"), current_price=Decimal("100"),
    ))
    hold_vote = persona.screen_rule(
        _make_snapshot(
            pbr=2.0,
            dividend_yield=0.0,
        )
    )
    sell_vote = persona.screen_rule(
        _make_snapshot(
            price_52w_high=Decimal("100"),
            current_price=Decimal("99"),
            per=100.0,
            pbr=100.0,
            eps=Decimal("-1"),
            dividend_yield=0.0,
        )
    )

    assert buy_vote.action == VoteAction.BUY
    assert hold_vote.action == VoteAction.HOLD
    assert sell_vote.action == VoteAction.SELL
    assert persona.should_trigger_llm(_make_vote(VoteAction.BUY, 0.6, passed=6, total=6)) is True


def test_wood_advisory_paths() -> None:
    advisory = WoodAdvisory()

    assert _classify_sector("Technology platform") == (True, 1.0)
    assert _classify_sector("cement") == (False, 0.0)

    assert _assess_adoption_curve(_make_snapshot(revenue_growth_yoy=60.0))[0] == "early"
    assert _assess_adoption_curve(_make_snapshot(revenue_growth_yoy=30.0))[0] == "growth"
    assert _assess_adoption_curve(_make_snapshot(revenue_growth_yoy=10.0))[0] == "late_growth"
    assert _assess_adoption_curve(_make_snapshot(revenue_growth_yoy=1.0))[0] == "mature"

    high_vote = advisory.evaluate(_make_snapshot())
    low_vote = advisory.evaluate(
        _make_snapshot(
            sector="unknown",
            revenue_growth_yoy=-5.0,
            operating_margin=-10.0,
            earnings_growth_yoy=-20.0,
        )
    )

    assert high_vote.action == VoteAction.ADVISORY
    assert high_vote.innovation_score >= 0.4
    assert low_vote.innovation_score <= 0.3


def test_prompt_loader_success_and_validation_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_loader.load_persona_prompt.cache_clear()

    class FakeYamlModule:
        @staticmethod
        def safe_load(_file):
            return {
                "philosophy": "P",
                "evaluation_criteria": ["A", "B"],
                "output_format": "O",
            }

    yaml_dir = tmp_path / "prompts"
    yaml_dir.mkdir()
    (yaml_dir / "demo.yaml").write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(prompt_loader, "PROMPTS_DIR", yaml_dir)
    monkeypatch.setattr(prompt_loader.importlib, "import_module", lambda _name: FakeYamlModule)

    rendered = prompt_loader.load_persona_prompt("demo")
    assert "P" in rendered
    assert "- A" in rendered
    assert "## 응답 형식" in rendered

    prompt_loader.load_persona_prompt.cache_clear()
    monkeypatch.setattr(
        prompt_loader.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ImportError("no yaml")),
    )
    with pytest.raises(ImportError):
        prompt_loader.load_persona_prompt("demo")

    class InvalidTypeYaml:
        @staticmethod
        def safe_load(_file):
            return ["not", "dict"]

    prompt_loader.load_persona_prompt.cache_clear()
    monkeypatch.setattr(prompt_loader.importlib, "import_module", lambda _name: InvalidTypeYaml)
    with pytest.raises(ValueError):
        prompt_loader.load_persona_prompt("demo")

    class InvalidCriteriaYaml:
        @staticmethod
        def safe_load(_file):
            return {
                "philosophy": "P",
                "evaluation_criteria": "not-list",
                "output_format": "O",
            }

    prompt_loader.load_persona_prompt.cache_clear()
    monkeypatch.setattr(prompt_loader.importlib, "import_module", lambda _name: InvalidCriteriaYaml)
    with pytest.raises(ValueError):
        prompt_loader.load_persona_prompt("demo")

    class MissingFieldsYaml:
        @staticmethod
        def safe_load(_file):
            return {
                "evaluation_criteria": ["A"],
            }

    prompt_loader.load_persona_prompt.cache_clear()
    monkeypatch.setattr(prompt_loader.importlib, "import_module", lambda _name: MissingFieldsYaml)
    with pytest.raises(ValueError):
        prompt_loader.load_persona_prompt("demo")


def test_prompt_loader_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeYamlModule:
        @staticmethod
        def safe_load(_file):
            return {}

    prompt_loader.load_persona_prompt.cache_clear()
    monkeypatch.setattr(prompt_loader, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompt_loader.importlib, "import_module", lambda _name: FakeYamlModule)

    with pytest.raises(FileNotFoundError):
        prompt_loader.load_persona_prompt("missing")
