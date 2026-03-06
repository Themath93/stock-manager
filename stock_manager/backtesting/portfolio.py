"""Simulated portfolio for backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Position:
    """Open position in the simulated portfolio."""

    symbol: str
    quantity: int
    entry_price: Decimal
    entry_date: date


@dataclass
class Trade:
    """Completed trade record."""

    symbol: str
    quantity: int
    entry_price: Decimal
    exit_price: Decimal
    entry_date: date
    exit_date: date
    pnl: Decimal
    commission: Decimal

    @property
    def return_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return float((self.exit_price - self.entry_price) / self.entry_price * 100)


class SimulatedPortfolio:
    """Tracks positions, cash, and trade history."""

    def __init__(
        self,
        initial_capital: Decimal,
        commission_rate: Decimal = Decimal("0.00015"),
    ) -> None:
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self._equity_curve: list[tuple[date, Decimal]] = []

    def buy(
        self, symbol: str, quantity: int, price: Decimal, trade_date: date
    ) -> bool:
        """Execute buy. Returns True if sufficient cash."""
        cost = price * quantity
        commission = cost * self.commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            return False

        self.cash -= total_cost
        if symbol in self.positions:
            # Average up
            existing = self.positions[symbol]
            total_qty = existing.quantity + quantity
            avg_price = (
                existing.entry_price * existing.quantity + price * quantity
            ) / total_qty
            self.positions[symbol] = Position(
                symbol, total_qty, avg_price, existing.entry_date
            )
        else:
            self.positions[symbol] = Position(symbol, quantity, price, trade_date)
        return True

    def sell(self, symbol: str, price: Decimal, trade_date: date) -> Trade | None:
        """Sell entire position. Returns Trade or None if no position."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None

        proceeds = price * pos.quantity
        commission = proceeds * self.commission_rate
        net_proceeds = proceeds - commission
        pnl = net_proceeds - (pos.entry_price * pos.quantity)

        self.cash += net_proceeds
        trade = Trade(
            symbol=symbol,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=price,
            entry_date=pos.entry_date,
            exit_date=trade_date,
            pnl=pnl,
            commission=commission,
        )
        self.trades.append(trade)
        return trade

    def total_value(self, prices: dict[str, Decimal]) -> Decimal:
        """Total portfolio value = cash + sum(position_value)."""
        position_value = sum(
            (prices.get(sym, pos.entry_price) * pos.quantity)
            for sym, pos in self.positions.items()
        )
        return self.cash + position_value

    def record_equity(self, trade_date: date, prices: dict[str, Decimal]) -> None:
        """Record equity curve data point."""
        self._equity_curve.append((trade_date, self.total_value(prices)))

    @property
    def equity_curve(self) -> list[tuple[date, Decimal]]:
        """Return copy of equity curve."""
        return list(self._equity_curve)

    @property
    def position_count(self) -> int:
        """Number of currently open positions."""
        return len(self.positions)
