"""Jesse Livermore persona: momentum / tape-reading.

"There is nothing new in Wall Street. There can't be because speculation
is as old as the hills."

Criteria (all must pass for BUY):
    1. Price above SMA-200 (primary trend is up)
    2. MACD histogram positive (macd_signal > 0 as proxy)
    3. RSI 40-70 (momentum without overbought)
    4. High volume (volume > avg_volume_20d * 1.2)
    5. Golden cross SMA-20 above SMA-60 (proxy via sma_20 > sma_50)
    6. ADX > 25 (strong trend)

LLM trigger ~10%: ambiguous tape patterns.
"""

from __future__ import annotations

from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_RSI_LOW = 40.0
_RSI_HIGH = 70.0
_ADX_TRENDING = 25.0
_VOLUME_MULTIPLIER = 1.2  # Volume must exceed avg by 20%


class LivermorePersona(InvestorPersona):
    """Jesse Livermore: follow the tape, trade with the trend."""

    def __init__(self) -> None:
        self.name = "Livermore"
        self.category = PersonaCategory.MOMENTUM

    @property
    def llm_trigger_rate(self) -> float:
        return 0.10

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {}

        # 1. Price above SMA-200 (primary uptrend)
        criteria["above_sma200"] = (
            snapshot.sma_200 is not None
            and snapshot.sma_200 > 0
            and float(snapshot.current_price) > snapshot.sma_200
        )

        # 2. MACD histogram positive (bullish momentum)
        criteria["macd_positive"] = (
            snapshot.macd_signal is not None and snapshot.macd_signal > 0
        )

        # 3. RSI in sweet spot (40-70)
        criteria["rsi_momentum_zone"] = (
            snapshot.rsi_14 is not None
            and _RSI_LOW <= snapshot.rsi_14 <= _RSI_HIGH
        )

        # 4. High volume confirmation
        criteria["high_volume"] = (
            snapshot.avg_volume_20d > 0
            and snapshot.volume > snapshot.avg_volume_20d * _VOLUME_MULTIPLIER
        )

        # 5. Golden cross: SMA-20 above SMA-50 (intermediate trend)
        criteria["golden_cross"] = (
            snapshot.sma_20 is not None
            and snapshot.sma_50 is not None
            and snapshot.sma_20 > 0
            and snapshot.sma_50 > 0
            and snapshot.sma_20 > snapshot.sma_50
        )

        # 6. ADX > 25 (trending market)
        criteria["adx_trending"] = (
            snapshot.adx_14 is not None and snapshot.adx_14 > _ADX_TRENDING
        )

        # --- Conviction ---
        met_count = sum(criteria.values())
        conviction = round(met_count / len(criteria), 4)

        # --- Action ---
        if met_count >= 5:
            action = VoteAction.BUY
        elif met_count >= 3:
            action = VoteAction.HOLD
        elif met_count <= 1:
            action = VoteAction.SELL
        else:
            action = VoteAction.HOLD

        # Check for bearish reversal signals (SELL override)
        bearish_reversal = (
            not criteria["above_sma200"]
            and not criteria["macd_positive"]
            and snapshot.rsi_14 is not None
            and snapshot.rsi_14 > _RSI_HIGH
        )
        if bearish_reversal:
            action = VoteAction.SELL
            conviction = max(conviction, 0.6)

        # --- Reasoning ---
        passed = [k for k, v in criteria.items() if v]
        failed = [k for k, v in criteria.items() if not v]
        if met_count >= 5:
            reasoning = (
                "The tape reads bullish: strong trend, confirmed by volume "
                "and momentum. Livermore says follow the line of least resistance."
            )
        elif bearish_reversal:
            reasoning = (
                "Bearish tape: price below SMA-200, negative MACD, and "
                "overbought RSI. Livermore would cut losses quickly."
            )
        else:
            reasoning = (
                f"Mixed tape. Bullish: {', '.join(passed) if passed else 'none'}. "
                f"Weak: {', '.join(failed) if failed else 'none'}. "
                "Livermore would wait for clearer direction."
            )

        return PersonaVote(
            persona_name=self.name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met=criteria,
            category=self.category,
        )

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        """Trigger on ambiguous tape patterns."""
        passed = sum(1 for v in vote.criteria_met.values() if v)
        total = len(vote.criteria_met)
        return total > 0 and 0.4 <= (passed / total) <= 0.6
