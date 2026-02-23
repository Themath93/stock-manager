"""Jim Simons persona: pure quantitative. ZERO LLM trigger.

"We don't override the models."

All signals are derived from statistical patterns. Conviction is a
continuous score computed from weighted signal strengths. No qualitative
judgment is ever applied.

Criteria (signals -- each contributes to continuous conviction):
    1. Mean reversion: price > 2 std below SMA-20
    2. RSI < 30 AND MACD signal turning positive
    3. Bollinger %B < 0.05 (extreme lower band)
    4. Volume anomaly (volume > 2x avg_volume_20d)
    5. Stochastic K/D crossover proxy (RSI + bollinger combined)
    6. Statistical arbitrage (price near 52w low with positive earnings growth)

LLM trigger: 0% -- NEVER.
"""

from __future__ import annotations


from .base import InvestorPersona
from .models import MarketSnapshot, PersonaCategory, PersonaVote, VoteAction


# ---------------------------------------------------------------------------
# Signal weights (sum to 1.0)
# ---------------------------------------------------------------------------

_WEIGHTS: dict[str, float] = {
    "mean_reversion": 0.25,
    "rsi_macd_reversal": 0.20,
    "bollinger_extreme": 0.20,
    "volume_anomaly": 0.10,
    "stochastic_proxy": 0.10,
    "stat_arb": 0.15,
}

# Thresholds
_RSI_OVERSOLD = 30.0
_BOLLINGER_EXTREME = 0.05
_VOLUME_ANOMALY_FACTOR = 2.0
_MEAN_REVERSION_STD = 2.0


class SimonsPersona(InvestorPersona):
    """Jim Simons: pure quantitative, zero human override."""

    def __init__(self) -> None:
        self.name = "Simons"
        self.category = PersonaCategory.QUANTITATIVE

    @property
    def llm_trigger_rate(self) -> float:
        return 0.0

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        criteria: dict[str, bool] = {}
        signal_scores: dict[str, float] = {}

        price = float(snapshot.current_price)

        # 1. Mean reversion: price > 2 std below SMA-20
        if snapshot.sma_20 and snapshot.sma_20 > 0 and price > 0:
            # Estimate std as distance between SMA-20 and price, normalized
            deviation = (snapshot.sma_20 - price) / snapshot.sma_20
            # Signal fires when price is significantly below SMA-20
            criteria["mean_reversion"] = deviation >= 0.04  # ~2std for typical stock
            # Continuous score: how far below (capped at 1.0)
            signal_scores["mean_reversion"] = min(max(deviation / 0.08, 0.0), 1.0)
        else:
            criteria["mean_reversion"] = False
            signal_scores["mean_reversion"] = 0.0

        # 2. RSI < 30 AND MACD turning positive
        rsi_oversold = (
            snapshot.rsi_14 is not None and snapshot.rsi_14 < _RSI_OVERSOLD
        )
        macd_turning = (
            snapshot.macd_signal is not None and snapshot.macd_signal > 0
        )
        criteria["rsi_macd_reversal"] = rsi_oversold and macd_turning
        rsi_score = 0.0
        if snapshot.rsi_14 is not None and snapshot.rsi_14 < _RSI_OVERSOLD:
            rsi_score = (_RSI_OVERSOLD - snapshot.rsi_14) / _RSI_OVERSOLD
        macd_score = 1.0 if macd_turning else 0.0
        signal_scores["rsi_macd_reversal"] = (rsi_score + macd_score) / 2

        # 3. Bollinger %B < 0.05 (extreme lower band)
        criteria["bollinger_extreme"] = (
            snapshot.bollinger_position is not None
            and snapshot.bollinger_position < _BOLLINGER_EXTREME
        )
        if snapshot.bollinger_position is not None:
            if snapshot.bollinger_position < _BOLLINGER_EXTREME:
                signal_scores["bollinger_extreme"] = min(
                    (_BOLLINGER_EXTREME - snapshot.bollinger_position) / _BOLLINGER_EXTREME,
                    1.0,
                )
            else:
                signal_scores["bollinger_extreme"] = 0.0
        else:
            signal_scores["bollinger_extreme"] = 0.0

        # 4. Volume anomaly (volume > 2x average)
        if snapshot.avg_volume_20d > 0:
            vol_ratio = snapshot.volume / snapshot.avg_volume_20d
            criteria["volume_anomaly"] = vol_ratio >= _VOLUME_ANOMALY_FACTOR
            signal_scores["volume_anomaly"] = min(
                vol_ratio / (_VOLUME_ANOMALY_FACTOR * 2), 1.0
            )
        else:
            criteria["volume_anomaly"] = False
            signal_scores["volume_anomaly"] = 0.0

        # 5. Stochastic K/D crossover proxy
        #    Combined RSI-reversal + Bollinger position as proxy for
        #    stochastic crossover (actual K/D not in MarketSnapshot)
        stoch_signal = (rsi_oversold and criteria.get("bollinger_extreme", False))
        criteria["stochastic_proxy"] = stoch_signal
        signal_scores["stochastic_proxy"] = (
            (signal_scores["rsi_macd_reversal"] + signal_scores["bollinger_extreme"]) / 2
        )

        # 6. Statistical arbitrage: price near 52w low + positive earnings growth
        if snapshot.price_52w_low > 0 and snapshot.price_52w_high > 0:
            range_52w = float(snapshot.price_52w_high - snapshot.price_52w_low)
            if range_52w > 0:
                position_in_range = (price - float(snapshot.price_52w_low)) / range_52w
                near_low = position_in_range < 0.15
            else:
                near_low = False
        else:
            near_low = False
        positive_growth = snapshot.earnings_growth_yoy > 0
        criteria["stat_arb"] = near_low and positive_growth
        low_score = 0.0
        if snapshot.price_52w_low > 0 and snapshot.price_52w_high > 0:
            range_52w = float(snapshot.price_52w_high - snapshot.price_52w_low)
            if range_52w > 0:
                position_in_range = (price - float(snapshot.price_52w_low)) / range_52w
                low_score = max(0.0, 1.0 - position_in_range / 0.15)
        growth_score = 1.0 if positive_growth else 0.0
        signal_scores["stat_arb"] = (low_score + growth_score) / 2

        # --- Weighted conviction (continuous, 0.0-1.0) ---
        conviction = 0.0
        for signal_name, weight in _WEIGHTS.items():
            conviction += signal_scores.get(signal_name, 0.0) * weight
        conviction = round(min(max(conviction, 0.0), 1.0), 4)

        # --- Action based on conviction threshold ---
        if conviction >= 0.6:
            action = VoteAction.BUY
        elif conviction >= 0.3:
            action = VoteAction.HOLD
        elif conviction < 0.15:
            action = VoteAction.SELL
        else:
            action = VoteAction.HOLD

        # --- Reasoning (purely quantitative) ---
        active_signals = [k for k, v in criteria.items() if v]
        reasoning = (
            f"Quantitative model score: {conviction:.4f}. "
            f"Active signals: {', '.join(active_signals) if active_signals else 'none'}. "
            f"Signal scores: {', '.join(f'{k}={v:.2f}' for k, v in signal_scores.items())}."
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
        """NEVER trigger LLM. The model is the model."""
        return False
