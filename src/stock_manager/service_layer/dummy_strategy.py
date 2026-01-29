"""
Dummy Strategy for PoC Testing

TOMBSTONE: PoC simplification - Always returns signals for testing
TODO: Replace with real strategy implementation before production
SPEC: WH-003 Strategy Evaluation
"""

import logging
from decimal import Decimal
from typing import Optional

from .strategy_executor import StrategyPort, BuySignal, SellSignal
from ..domain.worker import Candidate

logger = logging.getLogger(__name__)


class DummyStrategy(StrategyPort):
    """Dummy strategy for PoC testing

    Always returns buy/sell signals with fixed confidence for testing
    the full trading workflow without implementing real strategy logic.

    PoC Only: Remove before production use.
    """

    def __init__(
        self,
        buy_confidence: Decimal = Decimal("0.8"),
        sell_confidence: Decimal = Decimal("0.8"),
        suggested_qty: Decimal = Decimal("10"),
    ):
        """Initialize dummy strategy

        Args:
            buy_confidence: Confidence for buy signals (0-1)
            sell_confidence: Confidence for sell signals (0-1)
            suggested_qty: Default suggested quantity
        """
        self.buy_confidence = buy_confidence
        self.sell_confidence = sell_confidence
        self.suggested_qty = suggested_qty
        logger.info(
            f"DummyStrategy initialized: buy_conf={buy_confidence}, "
            f"sell_conf={sell_confidence}, qty={suggested_qty}"
        )

    async def evaluate_buy(
        self,
        candidate: Candidate,
        position_qty: Decimal,
    ) -> Optional[BuySignal]:
        """Evaluate buy signal (always returns BUY for PoC)

        Args:
            candidate: Candidate stock
            position_qty: Current position quantity

        Returns:
            BuySignal: Always returns a buy signal for testing
        """
        # PoC: Always return buy signal
        signal = BuySignal(
            symbol=candidate.symbol,
            confidence=self.buy_confidence,
            reason=f"PoC: Dummy buy signal for {candidate.symbol}",
            suggested_qty=self.suggested_qty,
            suggested_price=candidate.current_price,
        )

        logger.info(
            f"[PoC] DummyStrategy.evaluate_buy: {candidate.symbol} -> "
            f"confidence={signal.confidence}, qty={signal.suggested_qty}"
        )

        return signal

    async def evaluate_sell(
        self,
        symbol: str,
        position_qty: Decimal,
        avg_price: Decimal,
        current_price: Decimal,
    ) -> Optional[SellSignal]:
        """Evaluate sell signal (returns SELL when profit target reached)

        Args:
            symbol: Stock symbol
            position_qty: Current position quantity
            avg_price: Average entry price
            current_price: Current market price

        Returns:
            Optional[SellSignal]: Returns sell signal when price > avg_price * 1.05
        """
        # PoC: Simple profit target (5% gain)
        profit_threshold = avg_price * Decimal("1.05")

        if current_price >= profit_threshold:
            signal = SellSignal(
                symbol=symbol,
                confidence=self.sell_confidence,
                reason=f"PoC: Profit target reached ({current_price} >= {profit_threshold})",
                suggested_price=current_price,
            )

            logger.info(
                f"[PoC] DummyStrategy.evaluate_sell: {symbol} -> "
                f"SELL at {current_price} (avg: {avg_price}, profit: 5%)"
            )

            return signal

        logger.debug(
            f"[PoC] DummyStrategy.evaluate_sell: {symbol} -> "
            f"HOLD (current: {current_price} < target: {profit_threshold})"
        )

        return None
