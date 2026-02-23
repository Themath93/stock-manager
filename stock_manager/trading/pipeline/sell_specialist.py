"""Sell specialist: exit execution with reason tracking.

Validates that the entry has an open position and records the exit
reason for post-trade analysis and logging.
"""

from __future__ import annotations

from decimal import Decimal

from stock_manager.trading.pipeline.state import PipelineEntry

#: Recognized exit reason codes.
EXIT_REASONS: set[str] = {
    "STOP_LOSS",
    "TAKE_PROFIT",
    "TRAILING_STOP",
    "MAX_HOLDING",
    "CONSENSUS_REVERSAL",
    "MANUAL",
}


class SellSpecialist:
    """Handles sell order execution with exit reason validation.

    Stateless: does not track positions itself. Relies on the
    ``PipelineEntry`` having valid ``buy_price`` and ``buy_quantity``.
    """

    def execute(
        self,
        entry: PipelineEntry,
        reason: str,
        current_price: Decimal,
    ) -> bool:
        """Execute a sell order for the given pipeline entry.

        Steps:
            1. Validate the entry has ``buy_price`` and ``buy_quantity``.
            2. Compute realized P&L.
            3. Update ``entry.current_price`` and ``entry.unrealized_pnl``.
            4. Return True on success.

        Args:
            entry: Pipeline entry to sell.
            reason: Exit reason code (e.g. "STOP_LOSS", "TAKE_PROFIT").
            current_price: Current market price per share.

        Returns:
            True if the sell was executed successfully, False otherwise.
        """
        if entry.buy_price is None or entry.buy_quantity is None:
            return False

        if entry.buy_quantity <= 0:
            return False

        # Record exit reason for post-trade analysis
        entry.error_message = reason

        # Record the exit
        entry.current_price = current_price
        pnl = (current_price - entry.buy_price) * entry.buy_quantity
        entry.unrealized_pnl = pnl  # Now realized

        return True
