"""
Strategy Executor

Evaluates buy and sell signals for candidate stocks based on
trading strategy logic. Implements WT-003: Strategy Evaluation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..domain.worker import Candidate

logger = logging.getLogger(__name__)


@dataclass
class BuySignal:
    """Buy signal for a candidate stock"""

    symbol: str  # Stock symbol
    confidence: Decimal  # Confidence score (0-1)
    reason: str  # Reason for buy signal
    suggested_qty: Optional[Decimal] = None  # Suggested quantity (if known)
    suggested_price: Optional[Decimal] = None  # Suggested price (if known)
    timestamp: datetime = None  # Signal timestamp

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SellSignal:
    """Sell signal for a held stock"""

    symbol: str  # Stock symbol
    confidence: Decimal  # Confidence score (0-1)
    reason: str  # Reason for sell signal
    suggested_price: Optional[Decimal] = None  # Suggested price (if known)
    timestamp: datetime = None  # Signal timestamp

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class StrategyPort(ABC):
    """Strategy interface

    Abstract interface for trading strategies. Concrete implementations
    (e.g., momentum, mean-reversion, ML-based) will implement this port.
    """

    @abstractmethod
    async def evaluate_buy(
        self,
        candidate: Candidate,
        position_qty: Decimal,
    ) -> Optional[BuySignal]:
        """Evaluate buy signal for a candidate

        Args:
            candidate: Candidate stock
            position_qty: Current position quantity (0 for new position)

        Returns:
            Optional[BuySignal]: Buy signal if strategy recommends buy
        """
        pass

    @abstractmethod
    async def evaluate_sell(
        self,
        symbol: str,
        position_qty: Decimal,
        avg_price: Decimal,
        current_price: Decimal,
    ) -> Optional[SellSignal]:
        """Evaluate sell signal for a held stock

        Args:
            symbol: Stock symbol
            position_qty: Current position quantity
            avg_price: Average entry price
            current_price: Current market price

        Returns:
            Optional[SellSignal]: Sell signal if strategy recommends sell
        """
        pass


class StrategyNotFoundError(Exception):
    """Strategy not found"""

    pass


class StrategyExecutor:
    """Strategy Executor

    Evaluates trading strategy signals for buy and sell decisions.
    Uses StrategyPort for strategy evaluation.
    """

    def __init__(
        self,
        strategy: StrategyPort,
        min_confidence: Decimal = Decimal("0.5"),
    ):
        """Initialize Strategy Executor

        Args:
            strategy: Trading strategy implementation
            min_confidence: Minimum confidence threshold for executing signals
        """
        self.strategy = strategy
        self.min_confidence = min_confidence

    async def should_buy(
        self,
        candidate: Candidate,
        position_qty: Decimal = Decimal("0"),
    ) -> Optional[BuySignal]:
        """Evaluate if worker should buy a candidate stock

        Args:
            candidate: Candidate stock
            position_qty: Current position quantity (default: 0)

        Returns:
            Optional[BuySignal]: Buy signal if confidence >= min_confidence
        """
        try:
            buy_signal = await self.strategy.evaluate_buy(candidate, position_qty)

            if buy_signal is None:
                logger.debug(f"No buy signal for {candidate.symbol}")
                return None

            # Check confidence threshold
            if buy_signal.confidence < self.min_confidence:
                logger.debug(
                    f"Buy signal for {candidate.symbol} below confidence threshold: "
                    f"{buy_signal.confidence} < {self.min_confidence}"
                )
                return None

            logger.info(
                f"Buy signal for {candidate.symbol}: confidence={buy_signal.confidence}, "
                f"reason={buy_signal.reason}"
            )

            return buy_signal

        except Exception as e:
            logger.error(f"Failed to evaluate buy signal for {candidate.symbol}: {e}")
            return None

    async def should_sell(
        self,
        symbol: str,
        position_qty: Decimal,
        avg_price: Decimal,
        current_price: Decimal,
    ) -> Optional[SellSignal]:
        """Evaluate if worker should sell a held stock

        Args:
            symbol: Stock symbol
            position_qty: Current position quantity
            avg_price: Average entry price
            current_price: Current market price

        Returns:
            Optional[SellSignal]: Sell signal if confidence >= min_confidence
        """
        try:
            sell_signal = await self.strategy.evaluate_sell(
                symbol, position_qty, avg_price, current_price
            )

            if sell_signal is None:
                logger.debug(f"No sell signal for {symbol}")
                return None

            # Check confidence threshold
            if sell_signal.confidence < self.min_confidence:
                logger.debug(
                    f"Sell signal for {symbol} below confidence threshold: "
                    f"{sell_signal.confidence} < {self.min_confidence}"
                )
                return None

            logger.info(
                f"Sell signal for {symbol}: confidence={sell_signal.confidence}, "
                f"reason={sell_signal.reason}"
            )

            return sell_signal

        except Exception as e:
            logger.error(f"Failed to evaluate sell signal for {symbol}: {e}")
            return None
