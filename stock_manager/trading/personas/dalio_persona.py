"""Ray Dalio investor persona.

All-weather risk-parity approach: evaluates sector correlation,
volatility regime, overbought/oversold conditions, trend alignment,
and ATR-based risk/reward.
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction

# Thresholds
_MAX_SECTOR_CORRELATION = 0.7
_RSI_OVERBOUGHT = 70.0
_ADX_TRENDING = 25.0
_RISK_REWARD_MIN = 2.0  # ATR-based minimum risk/reward ratio


class DalioPersona(InvestorPersona):
    """All-weather risk parity: diversification and regime awareness."""

    def __init__(self) -> None:
        self.name = "Dalio"
        self.category = PersonaCategory.QUANTITATIVE

    # -- criteria helpers --------------------------------------------------

    @staticmethod
    def _check_sector_correlation(snapshot: MarketSnapshot) -> bool:
        """Sector correlation below threshold (proxy: VKOSPI as market stress).

        When VKOSPI is elevated (>25) correlations tend to spike; we use it
        as an inverse proxy.  If VKOSPI is unavailable we pass the check.
        """
        if snapshot.vkospi is None:
            return True
        # High VKOSPI implies high cross-asset correlation
        return snapshot.vkospi < (_MAX_SECTOR_CORRELATION * 100)

    @staticmethod
    def _check_volatility_band(snapshot: MarketSnapshot) -> bool:
        """ATR-14 within acceptable band (non-zero and not extreme).

        We consider ATR acceptable when it is between 0.5% and 5% of price.
        """
        if snapshot.atr_14 <= 0 or float(snapshot.current_price) <= 0:
            return False
        atr_pct = snapshot.atr_14 / float(snapshot.current_price) * 100
        return 0.5 <= atr_pct <= 5.0

    @staticmethod
    def _check_not_overbought(snapshot: MarketSnapshot) -> bool:
        """RSI-14 below overbought threshold."""
        return snapshot.rsi_14 < _RSI_OVERBOUGHT

    @staticmethod
    def _check_trend_alignment(snapshot: MarketSnapshot) -> bool:
        """ADX-14 indicates a trending market (>25) with positive direction.

        Uses price vs SMA-50 as a directional proxy when ADX confirms trend.
        """
        is_trending = snapshot.adx_14 >= _ADX_TRENDING
        price_above_sma = float(snapshot.current_price) > snapshot.sma_50 if snapshot.sma_50 > 0 else False
        return is_trending and price_above_sma

    @staticmethod
    def _check_risk_reward(snapshot: MarketSnapshot) -> bool:
        """Favourable risk/reward based on ATR distance to 52-week levels.

        Upside potential (distance to 52w high) should be at least
        RISK_REWARD_MIN times the downside risk (1 ATR).
        """
        if snapshot.atr_14 <= 0 or float(snapshot.current_price) <= 0:
            return False
        upside = float(snapshot.price_52w_high - snapshot.current_price)
        downside = snapshot.atr_14  # 1 ATR as risk unit
        if downside <= 0:
            return False
        return (upside / downside) >= _RISK_REWARD_MIN

    # -- InvestorPersona interface -----------------------------------------

    @property
    def llm_trigger_rate(self) -> float:
        return 0.10

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger on economic regime shift signals."""
        passed = sum(1 for v in vote.criteria_met.values() if v)
        total = len(vote.criteria_met)
        return total > 0 and passed == total // 2  # exactly half criteria met

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {
            "sector_correlation_low": self._check_sector_correlation(snapshot),
            "volatility_in_band": self._check_volatility_band(snapshot),
            "not_overbought": self._check_not_overbought(snapshot),
            "trend_alignment": self._check_trend_alignment(snapshot),
            "risk_reward_favorable": self._check_risk_reward(snapshot),
        }
        met = sum(criteria.values())

        if met == 5:
            action = VoteAction.BUY
            conviction = 0.8
            reasoning = (
                "All 5 Dalio all-weather criteria met. Low correlation, "
                "controlled volatility, trending with favourable risk/reward."
            )
        elif met >= 3:
            action = VoteAction.BUY
            conviction = 0.5
            reasoning = (
                f"{met}/5 Dalio criteria met. Risk environment is acceptable "
                "but not optimal; position sizing should reflect gaps."
            )
        elif met >= 2:
            action = VoteAction.HOLD
            conviction = 0.35
            reasoning = (
                f"Only {met}/5 Dalio criteria met. Risk regime is unfavourable "
                "for new allocation; maintain existing positions cautiously."
            )
        else:
            action = VoteAction.SELL
            conviction = 0.7
            reasoning = (
                f"Only {met}/5 Dalio criteria met. Risk environment is hostile: "
                "high correlation, extreme volatility, or adverse trend. "
                "Reduce exposure."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )
