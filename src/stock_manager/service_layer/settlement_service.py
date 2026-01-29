"""
Settlement Service

Handles daily settlement operations including position snapshots
and PnL calculations. Implements SPEC-BACKEND-INFRA-003 requirements.

References:
- SPEC-BACKEND-INFRA-003: Daily Settlement
- WT-004: Position snapshot and daily settlement at market close
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional

from ..domain.market_lifecycle import (
    DailySettlement,
    PositionSnapshot,
)
from ..domain.order import Position
from ..service_layer.position_service import PositionService

logger = logging.getLogger(__name__)


class SettlementError(Exception):
    """Settlement operation failed"""

    pass


class SettlementService(ABC):
    """Settlement service interface

    Handles daily settlement operations.
    """

    @abstractmethod
    def create_daily_settlement(self, trade_date: date) -> DailySettlement:
        """Create daily settlement record (WT-004)

        Args:
            trade_date: Trade date for settlement

        Returns:
            DailySettlement: Created settlement record

        Raises:
            SettlementError: If settlement creation fails
        """
        pass

    @abstractmethod
    def create_position_snapshots(self) -> List[PositionSnapshot]:
        """Create position snapshots for all open positions

        Returns:
            List[PositionSnapshot]: List of position snapshots
        """
        pass

    @abstractmethod
    def calculate_realized_pnl(self, trade_date: date) -> Decimal:
        """Calculate realized PnL for trade date

        Args:
            trade_date: Trade date

        Returns:
            Decimal: Realized PnL
        """
        pass

    @abstractmethod
    def calculate_unrealized_pnl(self, positions: List[Position]) -> Decimal:
        """Calculate unrealized PnL for open positions

        Args:
            positions: List of open positions

        Returns:
            Decimal: Unrealized PnL
        """
        pass

    @abstractmethod
    def get_daily_settlement(self, trade_date: date) -> Optional[DailySettlement]:
        """Get daily settlement for trade date

        Args:
            trade_date: Trade date

        Returns:
            DailySettlement if exists, None otherwise
        """
        pass


class SettlementServiceImpl(SettlementService):
    """Settlement service implementation

    Implements daily settlement operations including position
    snapshots and PnL calculations.
    """

    def __init__(
        self,
        position_service: PositionService,
        db_connection,
    ):
        """Initialize settlement service

        Args:
            position_service: Position service for position operations
            db_connection: Database connection
        """
        self.position_service = position_service
        self.db = db_connection

    def create_daily_settlement(self, trade_date: date) -> DailySettlement:
        """Create daily settlement record (WT-004)

        Process:
        1. Get all open positions
        2. Create position snapshots
        3. Calculate realized PnL from closed positions today
        4. Calculate unrealized PnL from open positions
        5. Calculate total PnL
        6. Save to database

        Args:
            trade_date: Trade date for settlement

        Returns:
            DailySettlement: Created settlement record

        Raises:
            SettlementError: If settlement creation fails
        """
        logger.info(f"Creating daily settlement for {trade_date}")

        try:
            # Step 1: Create position snapshots
            snapshots = self.create_position_snapshots()

            # Step 2: Calculate realized PnL
            realized_pnl = self.calculate_realized_pnl(trade_date)

            # Step 3: Calculate unrealized PnL
            positions = self.position_service.get_all_positions()
            unrealized_pnl = self.calculate_unrealized_pnl(positions)

            # Step 4: Calculate total PnL
            total_pnl = realized_pnl + unrealized_pnl

            # Step 5: Create settlement record
            positions_snapshot = {
                "snapshots": [s.to_dict() for s in snapshots],
                "timestamp": datetime.now().isoformat(),
            }

            settlement = DailySettlement(
                id=0,  # Will be assigned by database
                trade_date=trade_date,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_pnl=total_pnl,
                positions_snapshot=positions_snapshot,
                created_at=datetime.now(),
            )

            # Step 6: Save to database
            settlement_id = self._save_settlement(settlement)
            settlement.id = settlement_id

            logger.info(
                f"Daily settlement created: "
                f"realized={realized_pnl}, unrealized={unrealized_pnl}, "
                f"total={total_pnl}"
            )

            return settlement

        except Exception as e:
            logger.error(f"Failed to create daily settlement: {e}")
            raise SettlementError(f"Settlement creation failed: {e}") from e

    def create_position_snapshots(self) -> List[PositionSnapshot]:
        """Create position snapshots for all open positions

        Returns:
            List[PositionSnapshot]: List of position snapshots
        """
        logger.info("Creating position snapshots")

        positions = self.position_service.get_all_positions()
        snapshots = []

        for position in positions:
            # Get current market price
            # TODO: Implement current price fetching from broker or market data
            current_price = position.avg_price  # Placeholder

            # Calculate realized PnL for this position
            # TODO: Track realized PnL per position
            realized_pnl = Decimal("0")

            snapshot = PositionSnapshot(
                symbol=position.symbol,
                qty=position.qty,
                avg_price=position.avg_price,
                current_price=current_price,
                timestamp=datetime.now(),
                realized_pnl=realized_pnl,
                metadata={"position_id": position.id},
            )

            snapshots.append(snapshot)

        logger.info(f"Created {len(snapshots)} position snapshots")

        return snapshots

    def calculate_realized_pnl(self, trade_date: date) -> Decimal:
        """Calculate realized PnL for trade date

        Realized PnL comes from positions that were closed today
        (sell orders that reduced or eliminated long positions,
        or buy-to-cover orders that reduced or eliminated short positions).

        Args:
            trade_date: Trade date

        Returns:
            Decimal: Realized PnL
        """
        logger.info(f"Calculating realized PnL for {trade_date}")

        # Query fills for the trade date
        query = """
        SELECT
            f.symbol,
            f.side,
            f.qty,
            f.price,
            f.created_at
        FROM fills f
        WHERE DATE(f.filled_at) = %s
        ORDER BY f.filled_at
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (trade_date,))
            rows = cursor.fetchall()

        if not rows:
            logger.info("No fills found for trade date")
            return Decimal("0")

        # Calculate realized PnL
        # For simplicity: (sell_price - buy_price) * qty
        # In production, track cost basis per position using FIFO or specific identification

        realized_pnl = Decimal("0")
        symbol_fills: Dict[str, List[Dict]] = {}

        # Group fills by symbol
        for row in rows:
            symbol, side, qty, price, _ = row
            if symbol not in symbol_fills:
                symbol_fills[symbol] = []

            symbol_fills[symbol].append(
                {
                    "side": side,
                    "qty": Decimal(qty),
                    "price": Decimal(price),
                }
            )

        # Calculate PnL per symbol
        for symbol, fills in symbol_fills.items():
            # Simplified calculation: sell_qty * sell_price - buy_qty * buy_price
            buy_total = Decimal("0")
            sell_total = Decimal("0")

            for fill in fills:
                if fill["side"] == "BUY":
                    buy_total += fill["qty"] * fill["price"]
                else:  # SELL
                    sell_total += fill["qty"] * fill["price"]

            symbol_pnl = sell_total - buy_total
            realized_pnl += symbol_pnl

            logger.debug(
                f"Symbol {symbol}: buy_total={buy_total}, "
                f"sell_total={sell_total}, pnl={symbol_pnl}"
            )

        logger.info(f"Realized PnL calculated: {realized_pnl}")

        return realized_pnl

    def calculate_unrealized_pnl(self, positions: List[Position]) -> Decimal:
        """Calculate unrealized PnL for open positions

        Unrealized PnL = (current_price - avg_price) * qty

        Args:
            positions: List of open positions

        Returns:
            Decimal: Unrealized PnL
        """
        logger.info("Calculating unrealized PnL")

        unrealized_pnl = Decimal("0")

        for position in positions:
            if position.qty == 0:
                continue

            # Get current market price
            # TODO: Implement current price fetching
            current_price = position.avg_price  # Placeholder

            # Calculate unrealized PnL
            position_pnl = (current_price - position.avg_price) * position.qty
            unrealized_pnl += position_pnl

            logger.debug(
                f"Position {position.symbol}: "
                f"qty={position.qty}, avg_price={position.avg_price}, "
                f"current_price={current_price}, pnl={position_pnl}"
            )

        logger.info(f"Unrealized PnL calculated: {unrealized_pnl}")

        return unrealized_pnl

    def get_daily_settlement(self, trade_date: date) -> Optional[DailySettlement]:
        """Get daily settlement for trade date

        Args:
            trade_date: Trade date

        Returns:
            DailySettlement if exists, None otherwise
        """
        query = """
        SELECT id, trade_date, realized_pnl, unrealized_pnl, total_pnl,
               positions_snapshot, created_at, updated_at
        FROM daily_settlements
        WHERE trade_date = %s
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(query, (trade_date,))
                row = cursor.fetchone()

            if row:
                return DailySettlement(
                    id=row['id'],
                    trade_date=row['trade_date'],
                    realized_pnl=Decimal(row['realized_pnl']),
                    unrealized_pnl=Decimal(row['unrealized_pnl']),
                    total_pnl=Decimal(row['total_pnl']),
                    positions_snapshot=row['positions_snapshot'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                )

        except Exception as e:
            logger.error(f"Failed to get daily settlement: {e}")

        return None

    def _save_settlement(self, settlement: DailySettlement) -> int:
        """Save settlement to database

        Args:
            settlement: Settlement to save

        Returns:
            int: Settlement ID
        """
        import json

        query = """
        INSERT INTO daily_settlements (
            trade_date, realized_pnl, unrealized_pnl, total_pnl, positions_snapshot
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (
                    settlement.trade_date,
                    str(settlement.realized_pnl),
                    str(settlement.unrealized_pnl),
                    str(settlement.total_pnl),
                    json.dumps(settlement.positions_snapshot),
                ),
            )
            settlement_id = cursor.fetchone()['id']
            self.db.commit()

        return settlement_id

    def _log_event(self, level: str, message: str, payload: dict = None) -> None:
        """Log event to database

        Args:
            level: Log level (INFO, WARN, ERROR)
            message: Event message
            payload: Event payload
        """
        query = """
        INSERT INTO events (level, message, payload)
        VALUES (%s, %s, %s)
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(query, (level, message, payload if payload else None))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
