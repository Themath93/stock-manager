"""
Daily Summary Service

Generates and stores daily PnL summaries for worker performance tracking.
Implements WH-004: Daily Summary.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from ..domain.worker import DailySummary
from ..service_layer.pnl_calculator import PnLCalculator
from ..adapters.storage.port import DatabasePort

logger = logging.getLogger(__name__)


class DailySummaryService:
    """Daily Summary Service

    Generates and stores daily PnL summaries for worker performance tracking.
    """

    def __init__(
        self,
        db: DatabasePort,
        pnl_calculator: PnLCalculator,
    ):
        """Initialize Daily Summary Service

        Args:
            db: Database connection
            pnl_calculator: PnL calculator
        """
        self.db = db
        self.pnl_calculator = pnl_calculator

    def generate_summary(
        self,
        worker_id: str,
        summary_date: Optional[date] = None,
    ) -> DailySummary:
        """Generate daily summary for a worker

        Args:
            worker_id: Worker ID
            summary_date: Summary date (default: today)

        Returns:
            DailySummary: Generated daily summary
        """
        summary_date = summary_date or datetime.utcnow().date()

        # Fetch trade data for the day
        trade_data = self._fetch_trade_data(worker_id, summary_date)

        # Fetch position snapshots for unrealized PnL
        unrealized_pnl = self._fetch_unrealized_pnl(worker_id, summary_date)

        # Calculate metrics
        total_trades = trade_data["total_trades"]
        winning_trades = trade_data["winning_trades"]
        losing_trades = trade_data["losing_trades"]
        gross_profit = trade_data["gross_profit"]
        gross_loss = trade_data["gross_loss"]
        net_pnl = gross_profit - gross_loss
        max_drawdown = trade_data["max_drawdown"]

        # Calculate derived metrics
        win_rate = self.pnl_calculator.calculate_win_rate(winning_trades, losing_trades)
        profit_factor = self.pnl_calculator.calculate_profit_factor(gross_profit, gross_loss)

        # Create or update daily summary
        summary = self._upsert_summary(
            worker_id=worker_id,
            summary_date=summary_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            unrealized_pnl=unrealized_pnl,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

        logger.info(f"Generated daily summary for worker {worker_id} on {summary_date}")
        return summary

    def get_summary(
        self,
        worker_id: str,
        summary_date: date,
    ) -> Optional[DailySummary]:
        """Get daily summary for a worker

        Args:
            worker_id: Worker ID
            summary_date: Summary date

        Returns:
            Optional[DailySummary]: Daily summary if exists
        """
        try:
            query = """
                SELECT
                    id, worker_id, summary_date, total_trades, winning_trades, losing_trades,
                    gross_profit, gross_loss, net_pnl, unrealized_pnl, max_drawdown,
                    win_rate, profit_factor, created_at, updated_at
                FROM daily_summaries
                WHERE worker_id = $1 AND summary_date = $2
            """
            params = (worker_id, summary_date)

            result = self.db.execute_query(query, params, fetch_one=True)

            if result is None:
                return None

            return DailySummary(
                id=result["id"],
                worker_id=result["worker_id"],
                summary_date=result["summary_date"],
                total_trades=result["total_trades"],
                winning_trades=result["winning_trades"],
                losing_trades=result["losing_trades"],
                gross_profit=Decimal(result["gross_profit"]),
                gross_loss=Decimal(result["gross_loss"]),
                net_pnl=Decimal(result["net_pnl"]),
                unrealized_pnl=Decimal(result["unrealized_pnl"]),
                max_drawdown=Decimal(result["max_drawdown"]),
                win_rate=Decimal(result["win_rate"]),
                profit_factor=Decimal(result["profit_factor"]),
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to get daily summary for {worker_id} on {summary_date}: {e}")
            return None

    def list_summaries(
        self,
        worker_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> list[DailySummary]:
        """List daily summaries for a worker

        Args:
            worker_id: Worker ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of summaries

        Returns:
            list[DailySummary]: List of daily summaries
        """
        try:
            query = """
                SELECT
                    id, worker_id, summary_date, total_trades, winning_trades, losing_trades,
                    gross_profit, gross_loss, net_pnl, unrealized_pnl, max_drawdown,
                    win_rate, profit_factor, created_at, updated_at
                FROM daily_summaries
                WHERE worker_id = $1
            """
            params = [worker_id]
            param_index = 2

            if start_date:
                query += f" AND summary_date >= ${param_index}"
                params.append(start_date)
                param_index += 1

            if end_date:
                query += f" AND summary_date <= ${param_index}"
                params.append(end_date)
                param_index += 1

            query += " ORDER BY summary_date DESC"
            query += f" LIMIT {limit}"

            results = self.db.execute_query(query, tuple(params), fetch_all=True)

            return (
                [
                    DailySummary(
                        id=r["id"],
                        worker_id=r["worker_id"],
                        summary_date=r["summary_date"],
                        total_trades=r["total_trades"],
                        winning_trades=r["winning_trades"],
                        losing_trades=r["losing_trades"],
                        gross_profit=Decimal(r["gross_profit"]),
                        gross_loss=Decimal(r["gross_loss"]),
                        net_pnl=Decimal(r["net_pnl"]),
                        unrealized_pnl=Decimal(r["unrealized_pnl"]),
                        max_drawdown=Decimal(r["max_drawdown"]),
                        win_rate=Decimal(r["win_rate"]),
                        profit_factor=Decimal(r["profit_factor"]),
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                    for r in results
                ]
                if results
                else []
            )

        except Exception as e:
            logger.error(f"Failed to list daily summaries for {worker_id}: {e}")
            return []

    def _fetch_trade_data(self, worker_id: str, summary_date: date) -> dict:
        """Fetch trade data for a day

        Args:
            worker_id: Worker ID
            summary_date: Summary date

        Returns:
            dict: Trade data statistics
        """
        # TODO: Implement actual trade data fetching from orders table
        # This is a placeholder - actual implementation will query the orders/fills table

        # Placeholder: Return zero values
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "gross_profit": Decimal("0"),
            "gross_loss": Decimal("0"),
            "max_drawdown": Decimal("0"),
        }

    def _fetch_unrealized_pnl(self, worker_id: str, summary_date: date) -> Decimal:
        """Fetch unrealized PnL for a day

        Args:
            worker_id: Worker ID
            summary_date: Summary date

        Returns:
            Decimal: Unrealized PnL
        """
        # TODO: Implement actual unrealized PnL fetching from positions table
        # This is a placeholder - actual implementation will query the positions table

        # Placeholder: Return zero
        return Decimal("0")

    def _upsert_summary(
        self,
        worker_id: str,
        summary_date: date,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        gross_profit: Decimal,
        gross_loss: Decimal,
        net_pnl: Decimal,
        unrealized_pnl: Decimal,
        max_drawdown: Decimal,
        win_rate: Decimal,
        profit_factor: Decimal,
    ) -> DailySummary:
        """Upsert daily summary to database

        Args:
            worker_id: Worker ID
            summary_date: Summary date
            total_trades: Total trades
            winning_trades: Winning trades
            losing_trades: Losing trades
            gross_profit: Gross profit
            gross_loss: Gross loss
            net_pnl: Net PnL
            unrealized_pnl: Unrealized PnL
            max_drawdown: Max drawdown
            win_rate: Win rate
            profit_factor: Profit factor

        Returns:
            DailySummary: Upserted daily summary
        """
        try:
            query = """
                INSERT INTO daily_summaries (
                    worker_id, summary_date, total_trades, winning_trades, losing_trades,
                    gross_profit, gross_loss, net_pnl, unrealized_pnl, max_drawdown,
                    win_rate, profit_factor
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (worker_id, summary_date) DO UPDATE SET
                    total_trades = EXCLUDED.total_trades,
                    winning_trades = EXCLUDED.winning_trades,
                    losing_trades = EXCLUDED.losing_trades,
                    gross_profit = EXCLUDED.gross_profit,
                    gross_loss = EXCLUDED.gross_loss,
                    net_pnl = EXCLUDED.net_pnl,
                    unrealized_pnl = EXCLUDED.unrealized_pnl,
                    max_drawdown = EXCLUDED.max_drawdown,
                    win_rate = EXCLUDED.win_rate,
                    profit_factor = EXCLUDED.profit_factor,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, worker_id, summary_date, total_trades, winning_trades, losing_trades,
                    gross_profit, gross_loss, net_pnl, unrealized_pnl, max_drawdown,
                    win_rate, profit_factor, created_at, updated_at
            """
            params = (
                worker_id,
                summary_date,
                total_trades,
                winning_trades,
                losing_trades,
                float(gross_profit),
                float(gross_loss),
                float(net_pnl),
                float(unrealized_pnl),
                float(max_drawdown),
                float(win_rate),
                float(profit_factor),
            )

            result = self.db.execute_query(query, params, fetch_one=True)

            return DailySummary(
                id=result["id"],
                worker_id=result["worker_id"],
                summary_date=result["summary_date"],
                total_trades=result["total_trades"],
                winning_trades=result["winning_trades"],
                losing_trades=result["losing_trades"],
                gross_profit=Decimal(result["gross_profit"]),
                gross_loss=Decimal(result["gross_loss"]),
                net_pnl=Decimal(result["net_pnl"]),
                unrealized_pnl=Decimal(result["unrealized_pnl"]),
                max_drawdown=Decimal(result["max_drawdown"]),
                win_rate=Decimal(result["win_rate"]),
                profit_factor=Decimal(result["profit_factor"]),
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to upsert daily summary for {worker_id} on {summary_date}: {e}")
            raise
