"""
Risk management for trading operations.

Enforces position limits, portfolio exposure, and validates stop-loss/take-profit.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskLimits:
    """Configurable risk limits."""

    max_position_size_pct: Decimal = Decimal("0.10")  # Max 10% of portfolio per position
    max_portfolio_exposure_pct: Decimal = Decimal("0.80")  # Max 80% total exposure
    max_positions: int = 5  # Maximum concurrent positions
    min_stop_loss_pct: Decimal = Decimal("0.02")  # Minimum 2% stop-loss
    max_stop_loss_pct: Decimal = Decimal("0.10")  # Maximum 10% stop-loss
    min_take_profit_pct: Decimal = Decimal("0.05")  # Minimum 5% take-profit
    default_stop_loss_pct: Decimal = Decimal("0.05")  # Default 5% stop-loss
    default_take_profit_pct: Decimal = Decimal("0.10")  # Default 10% take-profit


@dataclass
class RiskCheckResult:
    """Result of risk validation."""

    approved: bool
    reason: str = ""
    adjusted_quantity: Optional[int] = None
    suggested_stop_loss: Optional[Decimal] = None
    suggested_take_profit: Optional[Decimal] = None


def calculate_kelly_position_size(
    portfolio_value: Decimal,
    price: Decimal,
    risk_per_trade_pct: Decimal,
    stop_loss_pct: Decimal,
    max_position_size_pct: Decimal,
) -> int:
    """Calculate position size using Kelly-inspired sizing.

    Pure function - no side effects, easily testable.

    Args:
        portfolio_value: Total portfolio value
        price: Entry price per share
        risk_per_trade_pct: Maximum risk per trade (e.g., 0.02 = 2%)
        stop_loss_pct: Stop-loss distance as percentage (e.g., 0.05 = 5%)
        max_position_size_pct: Maximum position as portfolio % (e.g., 0.10 = 10%)

    Returns:
        Recommended position size in shares (0 if invalid inputs)
    """
    if portfolio_value <= 0:
        return 0

    # Risk amount = portfolio * risk%
    risk_amount = portfolio_value * risk_per_trade_pct

    # Position size = risk_amount / stop_loss%
    position_value = risk_amount / stop_loss_pct

    # Cap at max position size
    max_value = portfolio_value * max_position_size_pct
    position_value = min(position_value, max_value)

    return int(position_value / price)


class RiskManager:
    """
    Risk management for trading operations.

    Validates orders against portfolio limits and position constraints.
    """

    def __init__(
        self, limits: Optional[RiskLimits] = None, portfolio_value: Decimal = Decimal("0")
    ):
        self.limits = limits or RiskLimits()
        self.portfolio_value = portfolio_value
        self._current_exposure = Decimal("0")
        self._position_count = 0

    def update_portfolio(
        self, portfolio_value: Decimal, current_exposure: Decimal, position_count: int
    ) -> None:
        """Update portfolio state for risk calculations."""
        self.portfolio_value = portfolio_value
        self._current_exposure = current_exposure
        self._position_count = position_count

    def validate_order(
        self,
        symbol: str,
        quantity: int,
        price: Decimal,
        side: str,  # "buy" or "sell"
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> RiskCheckResult:
        """
        Validate an order against risk limits.

        Args:
            symbol: Stock symbol
            quantity: Order quantity
            price: Order price
            side: "buy" or "sell"
            stop_loss: Optional stop-loss price
            take_profit: Optional take-profit price

        Returns:
            RiskCheckResult with approval status and adjustments
        """
        if side == "sell":
            # Sells reduce risk - generally approved
            return RiskCheckResult(approved=True, reason="Sell order approved")

        # Calculate order value
        order_value = Decimal(str(quantity)) * price

        # Check 1: Position count limit
        if self._position_count >= self.limits.max_positions:
            return RiskCheckResult(
                approved=False, reason=f"Maximum positions ({self.limits.max_positions}) reached"
            )

        # Check 2: Portfolio value check
        if self.portfolio_value <= 0:
            return RiskCheckResult(approved=False, reason="Portfolio value not set")

        # Check 3: Position size limit
        max_position_value = self.portfolio_value * self.limits.max_position_size_pct
        if order_value > max_position_value:
            adjusted_qty = int(max_position_value / price)
            if adjusted_qty <= 0:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Order exceeds max position size ({self.limits.max_position_size_pct * 100}%)",
                )
            return RiskCheckResult(
                approved=True,
                reason=f"Quantity adjusted from {quantity} to {adjusted_qty}",
                adjusted_quantity=adjusted_qty,
            )

        # Check 4: Portfolio exposure limit
        new_exposure = self._current_exposure + order_value
        max_exposure = self.portfolio_value * self.limits.max_portfolio_exposure_pct
        if new_exposure > max_exposure:
            available = max_exposure - self._current_exposure
            if available <= 0:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Portfolio exposure limit ({self.limits.max_portfolio_exposure_pct * 100}%) reached",
                )
            adjusted_qty = int(available / price)
            if adjusted_qty <= 0:
                return RiskCheckResult(approved=False, reason="Insufficient exposure capacity")
            return RiskCheckResult(
                approved=True,
                reason=f"Quantity adjusted to {adjusted_qty} due to exposure limit",
                adjusted_quantity=adjusted_qty,
            )

        # Check 5: Stop-loss validation
        result = RiskCheckResult(approved=True, reason="Order approved")

        if stop_loss is None:
            result.suggested_stop_loss = price * (1 - self.limits.default_stop_loss_pct)
        else:
            stop_loss_pct = (price - stop_loss) / price
            if stop_loss_pct < self.limits.min_stop_loss_pct:
                result.suggested_stop_loss = price * (1 - self.limits.min_stop_loss_pct)
                result.reason = f"Stop-loss too tight, suggested: {result.suggested_stop_loss}"
            elif stop_loss_pct > self.limits.max_stop_loss_pct:
                result.suggested_stop_loss = price * (1 - self.limits.max_stop_loss_pct)
                result.reason = f"Stop-loss too wide, suggested: {result.suggested_stop_loss}"

        # Check 6: Take-profit validation
        if take_profit is None:
            result.suggested_take_profit = price * (1 + self.limits.default_take_profit_pct)
        else:
            take_profit_pct = (take_profit - price) / price
            if take_profit_pct < self.limits.min_take_profit_pct:
                result.suggested_take_profit = price * (1 + self.limits.min_take_profit_pct)

        return result

    def calculate_position_size(
        self,
        price: Decimal,
        risk_per_trade_pct: Decimal = Decimal("0.02"),
        stop_loss_pct: Optional[Decimal] = None,
    ) -> int:
        """
        Calculate optimal position size using Kelly-inspired sizing.

        Args:
            price: Entry price
            risk_per_trade_pct: Maximum risk per trade as portfolio percentage
            stop_loss_pct: Stop-loss percentage (default from limits)

        Returns:
            Recommended position size (shares)
        """
        sl_pct = stop_loss_pct or self.limits.default_stop_loss_pct
        return calculate_kelly_position_size(
            self.portfolio_value,
            price,
            risk_per_trade_pct,
            sl_pct,
            self.limits.max_position_size_pct,
        )
