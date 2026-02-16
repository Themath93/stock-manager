"""
Base class for trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class StrategyScore(ABC):
    """Base class for strategy evaluation scores."""

    symbol: str

    @property
    @abstractmethod
    def passes_all(self) -> bool:
        """Whether the stock passes all criteria."""
        pass

    @property
    @abstractmethod
    def criteria_passed(self) -> int:
        """Count of criteria passed."""
        pass


class Strategy(ABC):
    """Base class for all trading strategies."""

    @abstractmethod
    def evaluate(self, symbol: str) -> Optional[StrategyScore]:
        """
        Evaluate a stock against strategy criteria.

        Args:
            symbol: Stock symbol to evaluate

        Returns:
            StrategyScore or None if evaluation fails
        """
        pass

    def screen(self, symbols: list[str]) -> list[StrategyScore]:
        """
        Screen multiple stocks and return passing scores.

        Args:
            symbols: List of stock symbols to screen

        Returns:
            List of StrategyScore objects that pass criteria
        """
        results = []
        for symbol in symbols:
            score = self.evaluate(symbol)
            if score and score.passes_all:
                results.append(score)
        return results
