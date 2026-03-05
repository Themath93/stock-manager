"""ATR-based volatility-aware position sizing.

Scales position size inversely with volatility: higher ATR = smaller position.
"""
from __future__ import annotations

from decimal import Decimal


def compute_volatility_position_size(
    available_capital: Decimal,
    current_price: Decimal,
    atr_14: float,
    risk_per_trade_pct: float = 1.0,
    max_position_pct: float = 10.0,
) -> int:
    """Compute position size based on ATR-14 volatility.

    Position size = (capital * risk%) / (ATR-14 * 2)
    Capped at max_position_pct of available capital.

    Args:
        available_capital: Total available capital for trading.
        current_price: Current stock price.
        atr_14: 14-day Average True Range.
        risk_per_trade_pct: Maximum risk per trade as percentage (default 1%).
        max_position_pct: Maximum position size as percentage of capital.

    Returns:
        Number of shares to buy (integer, >= 0).
    """
    if current_price <= 0 or atr_14 <= 0 or available_capital <= 0:
        return 0

    risk_amount = available_capital * Decimal(str(risk_per_trade_pct / 100))
    risk_per_share = Decimal(str(atr_14 * 2))  # 2x ATR as stop distance

    if risk_per_share <= 0:
        return 0

    shares_from_risk = int(risk_amount / risk_per_share)
    max_shares = int(
        available_capital * Decimal(str(max_position_pct / 100)) / current_price
    )

    return max(0, min(shares_from_risk, max_shares))
