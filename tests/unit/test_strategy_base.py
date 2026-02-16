from __future__ import annotations

from dataclasses import dataclass
import pytest

from stock_manager.trading.strategies.base import Strategy, StrategyScore


@dataclass
class _TestScore(StrategyScore):
    passes: bool
    passed_count: int

    @property
    def passes_all(self) -> bool:
        return self.passes

    @property
    def criteria_passed(self) -> int:
        return self.passed_count


class _TestStrategy(Strategy):
    def __init__(self, scores: dict[str, bool]) -> None:
        self.scores = scores

    def evaluate(self, symbol: str) -> _TestScore | None:
        passed = self.scores.get(symbol, True)
        return _TestScore(symbol=symbol, passes=passed, passed_count=1 if passed else 0)


class _NoneStrategy(Strategy):
    def evaluate(self, symbol: str) -> None:
        return None


def test_screen_filters_out_non_passing_scores() -> None:
    strategy = _TestStrategy({"AAPL": True, "MSFT": False, "TSLA": True})
    screened = strategy.screen(["AAPL", "MSFT", "TSLA"])

    assert [score.symbol for score in screened] == ["AAPL", "TSLA"]
    assert all(score.passes_all for score in screened)


def test_screen_skips_none_scores() -> None:
    strategy = _NoneStrategy()
    screened = strategy.screen(["AAPL", "MSFT"])

    assert screened == []


def test_abstract_strategy_score_requires_properties() -> None:
    with pytest.raises(TypeError, match="abstract"):

        class _IncompleteScore(StrategyScore):
            pass

        _IncompleteScore(symbol="AAPL")
