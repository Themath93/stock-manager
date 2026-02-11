"""Boom-bust cycle detection based on Soros reflexivity."""

from decimal import Decimal
from typing import Any
import logging

from .thesis import CycleStage

logger = logging.getLogger(__name__)

class BoomBustCycleDetector:
    """Identifies current stage of boom-bust cycle."""

    def __init__(self, client: Any):  # KISRestClient
        self.client = client

    def detect_stage(
        self,
        symbol: str,
        lookback_days: int = 90
    ) -> CycleStage:
        """
        Detect cycle stage based on:
        1. Price trend strength
        2. Volume pattern
        3. Volatility regime
        4. Momentum acceleration
        """
        try:
            from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import (
                inquire_daily_price
            )

            # Get historical data
            response = inquire_daily_price(self.client, symbol, period=str(lookback_days))
            if response.get("rt_cd") != "0":
                logger.warning(f"Failed to get data for {symbol}")
                return CycleStage.INCEPTION

            daily_prices = response.get("output2", [])
            if len(daily_prices) < 20:
                return CycleStage.INCEPTION

            # Calculate indicators
            trend_strength = self._calculate_trend_strength(daily_prices)
            volume_pattern = self._analyze_volume_pattern(daily_prices)
            volatility = self._calculate_volatility(daily_prices)
            momentum = self._calculate_momentum_acceleration(daily_prices)

            # Classify stage
            if trend_strength < Decimal("0.3"):
                return CycleStage.INCEPTION
            elif trend_strength < Decimal("0.6") and momentum > 0:
                return CycleStage.ACCELERATION
            elif trend_strength >= Decimal("0.6") and volatility > Decimal("0.5"):
                return CycleStage.TESTING
            elif trend_strength >= Decimal("0.8") and volume_pattern == "climactic":
                return CycleStage.EUPHORIA
            elif trend_strength >= Decimal("0.6") and momentum < 0:
                return CycleStage.TWILIGHT
            else:
                return CycleStage.COLLAPSE

        except Exception as e:
            logger.error(f"Cycle detection failed: {e}")
            return CycleStage.INCEPTION

    def _calculate_trend_strength(self, daily_prices: list[dict]) -> Decimal:
        """Calculate trend strength (0-1)."""
        if len(daily_prices) < 2:
            return Decimal("0")

        closes = [Decimal(str(p.get("stck_clpr", "0"))) for p in daily_prices]
        if not closes or closes[0] == 0:
            return Decimal("0")

        # Simple: ratio of current to oldest
        return min(Decimal("1"), max(Decimal("0"),
            (closes[0] - closes[-1]) / closes[-1] if closes[-1] != 0 else Decimal("0")
        ))

    def _analyze_volume_pattern(self, daily_prices: list[dict]) -> str:
        """Analyze volume pattern."""
        volumes = [int(p.get("acml_vol", "0")) for p in daily_prices]
        if not volumes:
            return "normal"

        avg_vol = sum(volumes) / len(volumes)
        recent_vol = sum(volumes[:5]) / 5 if len(volumes) >= 5 else avg_vol

        if recent_vol > avg_vol * 2:
            return "climactic"
        elif recent_vol > avg_vol * 1.5:
            return "elevated"
        return "normal"

    def _calculate_volatility(self, daily_prices: list[dict]) -> Decimal:
        """Calculate volatility (0-1 normalized)."""
        closes = [Decimal(str(p.get("stck_clpr", "0"))) for p in daily_prices]
        if len(closes) < 2:
            return Decimal("0")

        returns = [(closes[i] - closes[i+1]) / closes[i+1]
                   for i in range(len(closes)-1) if closes[i+1] != 0]
        if not returns:
            return Decimal("0")

        avg_return = sum(abs(r) for r in returns) / Decimal(len(returns))
        return min(Decimal("1"), avg_return * Decimal("10"))

    def _calculate_momentum_acceleration(self, daily_prices: list[dict]) -> int:
        """Calculate momentum direction (+1, 0, -1)."""
        if len(daily_prices) < 20:
            return 0

        closes = [Decimal(str(p.get("stck_clpr", "0"))) for p in daily_prices]
        recent_momentum = (closes[0] - closes[9]) / closes[9] if closes[9] != 0 else 0
        older_momentum = (closes[10] - closes[19]) / closes[19] if closes[19] != 0 else 0

        if recent_momentum > older_momentum:
            return 1
        elif recent_momentum < older_momentum:
            return -1
        return 0
