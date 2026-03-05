"""Circuit breaker: halts trading after consecutive losses or daily drawdown.

Trip conditions (any triggers halt):
    - N consecutive losses (default: 3)
    - Daily portfolio drawdown exceeds threshold (default: 5%)

Thread-safe with internal lock. Reset daily via reset_daily().
"""
from __future__ import annotations

import threading
from decimal import Decimal


class CircuitBreakerManager:
    """Standalone circuit breaker with internal lock.

    Args:
        max_consecutive_losses: Number of consecutive losses before tripping.
        max_daily_drawdown_pct: Maximum daily drawdown as decimal (0.05 = 5%).
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        max_daily_drawdown_pct: float = 0.05,
    ) -> None:
        self._lock = threading.Lock()
        self._max_consecutive_losses = max_consecutive_losses
        self._max_daily_drawdown_pct = max_daily_drawdown_pct
        self._consecutive_losses = 0
        self._daily_pnl = Decimal("0")
        self._daily_start_value = Decimal("0")
        self._tripped = False

    def record_trade_result(self, pnl: Decimal) -> None:
        """Record a trade's P&L and check trip conditions.

        Args:
            pnl: Profit/loss of the completed trade.
        """
        with self._lock:
            self._daily_pnl += pnl
            if pnl < 0:
                self._consecutive_losses += 1
            else:
                self._consecutive_losses = 0

            if self._consecutive_losses >= self._max_consecutive_losses:
                self._tripped = True

            if (
                self._daily_start_value > 0
                and self._daily_pnl < 0
                and abs(float(self._daily_pnl / self._daily_start_value))
                >= self._max_daily_drawdown_pct
            ):
                self._tripped = True

    def is_tripped(self) -> bool:
        """Check if circuit breaker is currently tripped."""
        with self._lock:
            return self._tripped

    def reset_daily(self, portfolio_value: Decimal | None = None) -> None:
        """Reset daily counters. Call at start of each trading day.

        Args:
            portfolio_value: Current portfolio value for drawdown calculation.
        """
        with self._lock:
            self._daily_pnl = Decimal("0")
            self._tripped = False
            self._consecutive_losses = 0
            if portfolio_value is not None:
                self._daily_start_value = portfolio_value
