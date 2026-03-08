"""
Position reconciliation with broker.

Periodically syncs local state with broker to detect discrepancies.
BROKER IS SOURCE OF TRUTH.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Optional
import logging

from stock_manager.trading.models import Position, PositionStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrokerPositionSnapshot:
    """Normalized broker position used for runtime convergence."""

    symbol: str
    quantity: int
    entry_price: Decimal | None = None
    current_price: Decimal | None = None


@dataclass
class ReconciliationResult:
    """Result of a reconciliation check."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_clean: bool = True
    discrepancies: list[str] = field(default_factory=list)
    orphan_positions: list[str] = field(default_factory=list)
    missing_positions: list[str] = field(default_factory=list)
    quantity_mismatches: dict[str, tuple[int, int]] = field(default_factory=dict)
    broker_positions: dict[str, BrokerPositionSnapshot] = field(default_factory=dict)
    local_positions: dict[str, BrokerPositionSnapshot] = field(default_factory=dict)

class PositionReconciler:
    """
    Periodic position reconciliation with broker.

    Runs in background thread, detects discrepancies between local state
    and broker positions. Alerts on mismatches.
    """

    def __init__(
        self,
        client: Any = None,  # KISRestClient
        position_manager: Any = None,  # PositionManager
        account_number: str = "",
        account_product_code: str = "01",
        is_paper_trading: bool = False,
        interval: float = 60.0,  # Check every 60 seconds
        on_discrepancy: Optional[Callable[[ReconciliationResult], None]] = None,
        on_cycle_complete: Optional[Callable[[ReconciliationResult], None]] = None,
        inquire_balance_func: Optional[Callable[[], dict[str, Any]]] = None,
        apply_state: bool = False,
    ):
        self.client = client
        self.position_manager = position_manager
        self.account_number = account_number
        self.account_product_code = account_product_code
        self.is_paper_trading = is_paper_trading
        self._inquire_balance_func = inquire_balance_func
        self.interval = interval
        self.on_discrepancy = on_discrepancy
        self.on_cycle_complete = on_cycle_complete
        self.apply_state = apply_state
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
        result = self._do_reconcile()
        self._last_result = result
        if self.on_cycle_complete is not None:
            self.on_cycle_complete(result)
        return result

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
                if self.on_cycle_complete is not None:
                    self.on_cycle_complete(result)

                if not result.is_clean and self.on_discrepancy:
                    self.on_discrepancy(result)

            except Exception as e:
                logger.error(f"Reconciliation error: {e}")

            self._stop_event.wait(self.interval)

    def _do_reconcile(self) -> ReconciliationResult:
        """Perform reconciliation check."""
        result = ReconciliationResult()

        try:
            if self._inquire_balance_func is not None:
                response = self._inquire_balance_func()
            else:
                from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import inquire_balance

                if self.client is None or not self.account_number:
                    raise ValueError("client and account_number are required for broker reconciliation")
                request_config = inquire_balance(
                    cano=self.account_number,
                    acnt_prdt_cd=self.account_product_code,
                    is_paper_trading=self.is_paper_trading,
                )
                response = self.client.make_request(
                    method="GET",
                    path=request_config["url_path"],
                    params=request_config["params"],
                    headers={"tr_id": request_config["tr_id"]},
                )

            if str(response.get("rt_cd")) != "0":
                msg = response.get("msg1") if isinstance(response, dict) else None
                result.is_clean = False
                result.discrepancies.append(f"Failed to query broker: {msg or 'unknown error'}")
                return result

            broker_positions = response.get("output1", [])
            if not isinstance(broker_positions, list):
                broker_positions = []
            result.broker_positions = self._build_broker_positions(broker_positions)
            broker_symbols = set(result.broker_positions)

            # Get local positions
            local_positions = (
                self.position_manager.get_all_positions() if self.position_manager is not None else {}
            )
            result.local_positions = self._build_local_positions(local_positions)
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
                broker_qty = result.broker_positions[symbol].quantity
                local_qty = self._get_local_qty(local_positions[symbol])
                if broker_qty != local_qty:
                    result.quantity_mismatches[symbol] = (local_qty, broker_qty)
                    result.discrepancies.append(
                        f"Quantity mismatch {symbol}: local={local_qty}, broker={broker_qty}"
                    )

            if self.apply_state and self.position_manager is not None:
                self._apply_broker_positions(
                    local_positions=local_positions,
                    broker_positions=result.broker_positions,
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
        """Extract symbol from broker payload with key-variant support."""
        if not isinstance(position, dict):
            return ""
        symbol = position.get("pdno")
        if symbol is None:
            symbol = position.get("PDNO")
        if symbol is None:
            return ""
        return str(symbol)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value in (None, "", "-"):
            return None
        try:
            return Decimal(str(value).replace(",", ""))
        except Exception:
            return None

    def _build_broker_positions(
        self, broker_positions: list[dict[str, Any]]
    ) -> dict[str, BrokerPositionSnapshot]:
        snapshots: dict[str, BrokerPositionSnapshot] = {}
        for position in broker_positions:
            symbol = self._extract_symbol(position)
            if not symbol:
                continue
            qty = position.get("hldg_qty")
            if qty is None:
                qty = position.get("HLDG_QTY", 0)
            try:
                quantity = int(qty or 0)
            except Exception:
                quantity = 0
            snapshots[symbol] = BrokerPositionSnapshot(
                symbol=symbol,
                quantity=quantity,
                entry_price=self._to_decimal(
                    position.get("pchs_avg_pric")
                    or position.get("PCHS_AVG_PRIC")
                    or position.get("avg_price")
                ),
                current_price=self._to_decimal(
                    position.get("prpr") or position.get("PRPR") or position.get("current_price")
                ),
            )
        return snapshots

    def _build_local_positions(
        self, local_positions: dict[str, Any]
    ) -> dict[str, BrokerPositionSnapshot]:
        snapshots: dict[str, BrokerPositionSnapshot] = {}
        for symbol, position in local_positions.items():
            snapshots[symbol] = BrokerPositionSnapshot(
                symbol=symbol,
                quantity=self._get_local_qty(position),
                entry_price=getattr(position, "entry_price", None)
                if not isinstance(position, dict)
                else self._to_decimal(position.get("entry_price")),
                current_price=getattr(position, "current_price", None)
                if not isinstance(position, dict)
                else self._to_decimal(position.get("current_price")),
            )
        return snapshots

    def _get_local_qty(self, position: Any) -> int:
        """Extract quantity from local position (dict or Position model)."""
        if isinstance(position, dict):
            return int(position.get("quantity", 0))
        return int(getattr(position, "quantity", 0))

    def _apply_broker_positions(
        self,
        *,
        local_positions: dict[str, Any],
        broker_positions: dict[str, BrokerPositionSnapshot],
    ) -> None:
        broker_symbols = set(broker_positions)
        local_symbols = set(local_positions)

        if not all(
            hasattr(self.position_manager, attr)
            for attr in ("close_position", "get_position", "open_position")
        ):
            return

        for symbol in local_symbols - broker_symbols:
            self.position_manager.close_position(symbol)

        for symbol in broker_symbols:
            snapshot = broker_positions[symbol]
            existing = self.position_manager.get_position(symbol)
            if existing is None:
                self.position_manager.open_position(
                    Position(
                        symbol=symbol,
                        quantity=snapshot.quantity,
                        entry_price=snapshot.entry_price or Decimal("0"),
                        current_price=snapshot.current_price,
                        status=PositionStatus.OPEN_RECONCILED,
                    )
                )
                continue

            existing.quantity = snapshot.quantity
            if snapshot.entry_price is not None and (
                existing.entry_price <= 0 or existing.status == PositionStatus.OPEN_RECONCILED
            ):
                existing.entry_price = snapshot.entry_price
            if snapshot.current_price is not None:
                existing.current_price = snapshot.current_price
                existing.unrealized_pnl = (
                    snapshot.current_price - existing.entry_price
                ) * Decimal(existing.quantity)
            if existing.status in {PositionStatus.STALE, PositionStatus.CLOSED}:
                existing.status = PositionStatus.OPEN_RECONCILED
