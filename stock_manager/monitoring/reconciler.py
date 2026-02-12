"""
Position reconciliation with broker.

Periodically syncs local state with broker to detect discrepancies.
BROKER IS SOURCE OF TRUTH.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class ReconciliationResult:
    """Result of a reconciliation check."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_clean: bool = True
    discrepancies: list[str] = field(default_factory=list)
    orphan_positions: list[str] = field(default_factory=list)
    missing_positions: list[str] = field(default_factory=list)
    quantity_mismatches: dict[str, tuple[int, int]] = field(default_factory=dict)

class PositionReconciler:
    """
    Periodic position reconciliation with broker.

    Runs in background thread, detects discrepancies between local state
    and broker positions. Alerts on mismatches.
    """

    def __init__(
        self,
        position_manager: Any,  # PositionManager
        inquire_balance_func: Callable[[], dict[str, Any]],
        interval: float = 60.0,  # Check every 60 seconds
        on_discrepancy: Optional[Callable[[ReconciliationResult], None]] = None
    ):
        self.position_manager = position_manager
        self.inquire_balance_func = inquire_balance_func
        self.interval = interval
        self.on_discrepancy = on_discrepancy
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_result: Optional[ReconciliationResult] = None

    def start(self) -> None:
        """Start reconciliation in background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Reconciler already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._reconcile_loop,
            daemon=True,
            name="PositionReconciler"
        )
        self._thread.start()
        logger.info("Position reconciler started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop reconciler gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("Position reconciler stopped")

    def reconcile_now(self) -> ReconciliationResult:
        """Run reconciliation immediately (can be called from any thread)."""
        return self._do_reconcile()

    @property
    def last_result(self) -> Optional[ReconciliationResult]:
        """Get the last reconciliation result."""
        return self._last_result

    def _reconcile_loop(self) -> None:
        """Reconciliation loop - runs in background thread."""
        while not self._stop_event.is_set():
            try:
                result = self._do_reconcile()
                self._last_result = result

                if not result.is_clean and self.on_discrepancy:
                    self.on_discrepancy(result)

            except Exception as e:
                logger.error(f"Reconciliation error: {e}")

            self._stop_event.wait(self.interval)

    def _do_reconcile(self) -> ReconciliationResult:
        """Perform reconciliation check."""
        result = ReconciliationResult()

        try:
            response = self.inquire_balance_func()
            if str(response.get("rt_cd")) != "0":
                msg = response.get("msg1") if isinstance(response, dict) else None
                result.is_clean = False
                result.discrepancies.append(f"Failed to query broker: {msg or 'unknown error'}")
                return result

            broker_positions = response.get("output1", [])
            if not isinstance(broker_positions, list):
                broker_positions = []

            broker_symbols = {
                symbol for symbol in (self._extract_symbol(p) for p in broker_positions) if symbol
            }

            # Get local positions
            local_positions = self.position_manager.get_all_positions()
            local_symbols = set(local_positions.keys())

            # Find orphans (at broker, not local)
            for symbol in broker_symbols - local_symbols:
                result.orphan_positions.append(symbol)
                result.discrepancies.append(f"Orphan at broker: {symbol}")

            # Find missing (local, not at broker)
            for symbol in local_symbols - broker_symbols:
                result.missing_positions.append(symbol)
                result.discrepancies.append(f"Missing at broker: {symbol}")

            # Check quantity mismatches
            for symbol in broker_symbols & local_symbols:
                broker_qty = self._get_broker_qty(broker_positions, symbol)
                local_qty = self._extract_local_qty(local_positions[symbol])
                if broker_qty != local_qty:
                    result.quantity_mismatches[symbol] = (local_qty, broker_qty)
                    result.discrepancies.append(
                        f"Quantity mismatch {symbol}: local={local_qty}, broker={broker_qty}"
                    )

            result.is_clean = len(result.discrepancies) == 0

            if result.is_clean:
                logger.debug("Reconciliation clean")
            else:
                logger.warning(f"Reconciliation found {len(result.discrepancies)} discrepancies")

        except Exception as e:
            result.is_clean = False
            result.discrepancies.append(f"Reconciliation error: {e}")
            logger.error(f"Reconciliation failed: {e}")

        return result

    @staticmethod
    def _extract_symbol(position: Any) -> str:
        if not isinstance(position, dict):
            return ""
        symbol = position.get("pdno")
        if symbol is None:
            symbol = position.get("PDNO")
        if symbol is None:
            return ""
        return str(symbol)

    @staticmethod
    def _extract_local_qty(position: Any) -> int:
        if isinstance(position, dict):
            raw = position.get("quantity", 0)
        else:
            raw = getattr(position, "quantity", 0)
        return int(raw or 0)

    def _get_broker_qty(self, broker_positions: list[dict], symbol: str) -> int:
        """Extract quantity for symbol from broker positions."""
        for pos in broker_positions:
            if self._extract_symbol(pos) == symbol:
                qty = pos.get("hldg_qty")
                if qty is None:
                    qty = pos.get("HLDG_QTY", 0)
                return int(qty or 0)
        return 0
