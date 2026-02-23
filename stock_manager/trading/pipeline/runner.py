"""Trading pipeline runner: 11-state machine orchestrator.

Drives each PipelineEntry through the full lifecycle:
WATCHLIST -> SCREENING -> EVALUATING -> CONSENSUS_APPROVED/REJECTED ->
BUY_PENDING -> BOUGHT -> MONITORING -> SELL_PENDING -> SOLD.

Thread-safe via RLock. Errors transition entries to ERROR state with
automatic recovery back to WATCHLIST on the next cycle.
"""

from __future__ import annotations

import logging
import threading
from decimal import Decimal

from stock_manager.trading.logging.pipeline_logger import PipelineJsonLogger
from stock_manager.trading.pipeline.buy_specialist import BuySpecialist
from stock_manager.trading.pipeline.monitor import PositionMonitor
from stock_manager.trading.pipeline.sell_specialist import SellSpecialist
from stock_manager.trading.pipeline.state import PipelineEntry, PipelineState
from stock_manager.trading.strategies.consensus import ConsensusStrategy

logger = logging.getLogger(__name__)


class TradingPipelineRunner:
    """Orchestrates the 11-state trading pipeline for multiple symbols.

    Each symbol is tracked as a PipelineEntry and advanced through the state
    machine one step per ``run_cycle()`` call.  Transitions are validated
    against ``VALID_TRANSITIONS`` and logged via ``PipelineJsonLogger``.

    Args:
        consensus_strategy: Strategy adapter wrapping ConsensusEvaluator.
        buy_specialist: Handles position sizing and buy execution.
        sell_specialist: Handles sell execution with exit reason tracking.
        monitor: Checks open positions for exit signals.
        pipeline_logger: Optional NDJSON pipeline logger.
    """

    def __init__(
        self,
        consensus_strategy: ConsensusStrategy,
        buy_specialist: BuySpecialist,
        sell_specialist: SellSpecialist,
        monitor: PositionMonitor,
        pipeline_logger: PipelineJsonLogger | None = None,
    ) -> None:
        self._strategy = consensus_strategy
        self._buy = buy_specialist
        self._sell = sell_specialist
        self._monitor = monitor
        self._logger = pipeline_logger
        self._entries: dict[str, PipelineEntry] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_to_watchlist(self, symbols: list[str]) -> None:
        """Add symbols to the watchlist (WATCHLIST state).

        Symbols already tracked are silently skipped.

        Args:
            symbols: List of ticker symbols to watch.
        """
        with self._lock:
            for symbol in symbols:
                if symbol not in self._entries:
                    self._entries[symbol] = PipelineEntry(symbol=symbol)
                    if self._logger:
                        self._logger.log_state_change(
                            symbol, "", PipelineState.WATCHLIST.name, "added to watchlist"
                        )

    def run_cycle(self) -> None:
        """Process all entries through the state machine one step.

        Each entry is advanced based on its current state.  Exceptions
        during processing send the entry to ERROR state.
        """
        with self._lock:
            entries = list(self._entries.values())

        for entry in entries:
            try:
                self._step(entry)
            except Exception as exc:
                self._handle_error(entry, exc)

    @property
    def entries(self) -> dict[str, PipelineEntry]:
        """Read-only snapshot of current pipeline entries."""
        with self._lock:
            return dict(self._entries)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _step(self, entry: PipelineEntry) -> None:
        """Advance a single entry one step based on its current state."""
        handlers = {
            PipelineState.WATCHLIST: self._handle_watchlist,
            PipelineState.SCREENING: self._handle_screening,
            PipelineState.EVALUATING: self._handle_evaluating,
            PipelineState.CONSENSUS_APPROVED: self._handle_consensus_approved,
            PipelineState.CONSENSUS_REJECTED: self._handle_consensus_rejected,
            PipelineState.BUY_PENDING: self._handle_buy_pending,
            PipelineState.BOUGHT: self._handle_bought,
            PipelineState.MONITORING: self._handle_monitoring,
            PipelineState.SELL_PENDING: self._handle_sell_pending,
            PipelineState.ERROR: self._handle_error_recovery,
            # SOLD is terminal -- no handler needed
        }
        handler = handlers.get(entry.state)
        if handler is not None:
            handler(entry)

    def _handle_watchlist(self, entry: PipelineEntry) -> None:
        """WATCHLIST -> SCREENING: begin pre-filter."""
        self._transition(entry, PipelineState.SCREENING, "starting screening")

    def _handle_screening(self, entry: PipelineEntry) -> None:
        """SCREENING -> EVALUATING: data is fetched during evaluation."""
        self._transition(entry, PipelineState.EVALUATING, "screening passed")
        if self._logger:
            self._logger.log_screening_complete(
                entry.symbol, {"status": "passed"}
            )

    def _handle_evaluating(self, entry: PipelineEntry) -> None:
        """EVALUATING -> CONSENSUS_APPROVED/REJECTED: run consensus strategy."""
        score = self._strategy.evaluate(entry.symbol)

        if score is not None and score.passes_all:
            entry.consensus_result = score.consensus_result
            self._transition(
                entry,
                PipelineState.CONSENSUS_APPROVED,
                f"consensus approved (buy={score.buy_count}/{score.total_votes}, "
                f"conviction={score.avg_conviction:.2f})",
            )
            if self._logger:
                self._logger.log_consensus_result(
                    entry.symbol,
                    passed=True,
                    buy_count=score.buy_count,
                    total_count=score.total_votes,
                    avg_conviction=score.avg_conviction,
                    categories={},
                )
        else:
            buy_count = score.buy_count if score else 0
            total_votes = score.total_votes if score else 0
            avg_conviction = score.avg_conviction if score else 0.0
            self._transition(
                entry,
                PipelineState.CONSENSUS_REJECTED,
                f"consensus rejected (buy={buy_count}/{total_votes})",
            )
            if self._logger:
                self._logger.log_consensus_result(
                    entry.symbol,
                    passed=False,
                    buy_count=buy_count,
                    total_count=total_votes,
                    avg_conviction=avg_conviction,
                    categories={},
                )

    def _handle_consensus_approved(self, entry: PipelineEntry) -> None:
        """CONSENSUS_APPROVED -> BUY_PENDING: prepare buy order."""
        self._transition(entry, PipelineState.BUY_PENDING, "consensus approved, pending buy")

    def _handle_consensus_rejected(self, entry: PipelineEntry) -> None:
        """CONSENSUS_REJECTED -> WATCHLIST: re-enter for next cycle."""
        entry.consensus_result = None
        self._transition(entry, PipelineState.WATCHLIST, "rejected, returning to watchlist")

    def _handle_buy_pending(self, entry: PipelineEntry) -> None:
        """BUY_PENDING -> BOUGHT: execute buy via BuySpecialist.

        Uses ``entry.current_price`` and a placeholder available capital.
        A full integration would fetch live price and account balance here.
        """
        current_price = entry.current_price or Decimal("0")
        available_capital = Decimal("1000000")  # placeholder

        if current_price <= 0:
            self._handle_error(
                entry, ValueError(f"Invalid price {current_price} for {entry.symbol}")
            )
            return

        success = self._buy.execute(entry, current_price, available_capital)
        if success:
            self._transition(entry, PipelineState.BOUGHT, "buy executed")
            if self._logger:
                self._logger.log_buy_decision(
                    entry.symbol,
                    price=entry.buy_price or Decimal("0"),
                    quantity=entry.buy_quantity or 0,
                    order_type="MARKET",
                    stop_loss=current_price * Decimal("0.93"),
                )
        else:
            self._handle_error(entry, RuntimeError(f"Buy execution failed for {entry.symbol}"))

    def _handle_bought(self, entry: PipelineEntry) -> None:
        """BOUGHT -> MONITORING: immediately transition to monitoring."""
        self._transition(entry, PipelineState.MONITORING, "bought, entering monitoring")

    def _handle_monitoring(self, entry: PipelineEntry) -> None:
        """MONITORING -> SELL_PENDING: check for exit signals."""
        current_price = entry.current_price or Decimal("0")
        if current_price <= 0:
            return  # Cannot evaluate without a price

        exit_reason = self._monitor.check(entry, current_price)
        if exit_reason is not None:
            # Store exit reason on error_message as transport to sell handler.
            entry.error_message = exit_reason
            self._transition(
                entry, PipelineState.SELL_PENDING, f"exit signal: {exit_reason}"
            )
            if self._logger and entry.buy_price is not None:
                pnl = (current_price - entry.buy_price) * (entry.buy_quantity or 0)
                self._logger.log_sell_trigger(
                    entry.symbol,
                    trigger_reason=exit_reason,
                    trigger_value=float(current_price),
                    current_pnl=pnl,
                )

    def _handle_sell_pending(self, entry: PipelineEntry) -> None:
        """SELL_PENDING -> SOLD: execute sell via SellSpecialist."""
        current_price = entry.current_price or Decimal("0")
        reason = entry.error_message or "MANUAL"
        entry.error_message = None

        success = self._sell.execute(entry, reason, current_price)
        if success:
            self._transition(entry, PipelineState.SOLD, f"sold: {reason}")
            if self._logger and entry.buy_price is not None and entry.current_price is not None:
                holding_days = 0
                if entry.history:
                    holding_days = (entry.entered_at - entry.history[-1][1]).days
                pnl = (entry.current_price - entry.buy_price) * (entry.buy_quantity or 0)
                return_pct = (
                    float((entry.current_price - entry.buy_price) / entry.buy_price * 100)
                    if entry.buy_price > 0
                    else 0.0
                )
                self._logger.log_trade_complete(
                    entry.symbol,
                    entry_price=entry.buy_price,
                    exit_price=entry.current_price,
                    pnl=pnl,
                    holding_days=holding_days,
                    return_pct=return_pct,
                )
        else:
            self._handle_error(entry, RuntimeError(f"Sell execution failed for {entry.symbol}"))

    def _handle_error_recovery(self, entry: PipelineEntry) -> None:
        """ERROR -> WATCHLIST: recovery path."""
        entry.error_message = None
        self._transition(entry, PipelineState.WATCHLIST, "recovered from error")

    # ------------------------------------------------------------------
    # Transition and error helpers
    # ------------------------------------------------------------------

    def _transition(self, entry: PipelineEntry, new_state: PipelineState, reason: str) -> None:
        """Validate transition and log.

        Args:
            entry: Pipeline entry to transition.
            new_state: Target state.
            reason: Human-readable reason for the transition.

        Raises:
            ValueError: If the transition is not allowed.
        """
        old_state = entry.state.name
        with self._lock:
            entry.transition(new_state)
        if self._logger:
            self._logger.log_state_change(entry.symbol, old_state, new_state.name, reason)

    def _handle_error(self, entry: PipelineEntry, exc: Exception) -> None:
        """Transition entry to ERROR state and log the exception.

        Args:
            entry: Pipeline entry that encountered an error.
            exc: The exception that was raised.
        """
        logger.warning(
            "Pipeline error for %s in state %s: %s",
            entry.symbol,
            entry.state.name,
            exc,
        )
        entry.error_message = str(exc)
        try:
            self._transition(entry, PipelineState.ERROR, str(exc))
        except ValueError:
            # Already in a terminal state or transition not allowed
            logger.warning(
                "Cannot transition %s to ERROR from %s",
                entry.symbol,
                entry.state.name,
            )
        if self._logger:
            self._logger.log_error(entry.symbol, exc, {"state": entry.state.name})
