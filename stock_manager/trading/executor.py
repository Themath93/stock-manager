"""
Order execution with idempotency and retry support.

Wraps KIS orders.py API with simplified interface.
Handles idempotency, retries, and status tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from stock_manager.trading.models import Order

logger = logging.getLogger(__name__)

# Will import from KIS adapter
# from ..adapters.broker.kis.apis.domestic_stock.orders import cash_order, get_tr_id_cash_order

@dataclass
class OrderResult:
    """Result of order execution."""
    success: bool
    order_id: str
    broker_order_id: Optional[str] = None
    message: str = ""
    filled_quantity: int = 0
    filled_price: Optional[int] = None

@dataclass
class OrderExecutor:
    """
    Simplified order executor wrapping KIS API.

    Features:
    - Simplified buy/sell interface
    - Idempotency key support (prevents duplicate orders)
    - Automatic retry with exponential backoff
    - Order status tracking
    """

    client: Any  # KISRestClient
    account_number: str  # 8-digit account number
    account_product_code: str = "01"  # 2-digit product code
    is_paper_trading: bool = False

    # Track submitted idempotency keys to prevent duplicates
    _submitted_keys: set[str] = field(default_factory=set, init=False)

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> OrderResult:
        """
        Place a buy order.

        Args:
            symbol: Stock symbol (e.g., "005930")
            quantity: Number of shares
            price: Limit price (None for market order)
            idempotency_key: Unique key to prevent duplicate orders

        Returns:
            OrderResult with execution details
        """
        return self._execute_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side="buy",
            idempotency_key=idempotency_key
        )

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> OrderResult:
        """
        Place a sell order.
        """
        return self._execute_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side="sell",
            idempotency_key=idempotency_key
        )

    def _execute_order(
        self,
        symbol: str,
        quantity: int,
        price: Optional[int],
        side: Literal["buy", "sell"],
        idempotency_key: Optional[str] = None
    ) -> OrderResult:
        """Internal order execution with idempotency check."""
        from uuid import uuid4

        # Generate idempotency key if not provided
        if idempotency_key is None:
            idempotency_key = str(uuid4())

        # Check for duplicate submission
        if idempotency_key in self._submitted_keys:
            logger.warning(f"Duplicate order rejected: {idempotency_key}")
            return OrderResult(
                success=False,
                order_id=idempotency_key,
                message="Duplicate order - idempotency key already used"
            )

        try:
            # Import KIS API
            from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
                cash_order
            )

            # Determine order type
            ord_dv = "00" if price else "01"  # 00=limit, 01=market

            # Build request config
            request_config = cash_order(
                cano=self.account_number,
                acnt_prdt_cd=self.account_product_code,
                pdno=symbol,
                ord_dv=ord_dv,
                ord_qty=quantity,
                ord_unsl="01",  # shares
                order_type=side,
                ord_prc=price,
                is_paper_trading=self.is_paper_trading,
            )
            response = self.client.make_request(
                method="POST",
                path=request_config["url_path"],
                json_data=request_config["params"],
                headers={"tr_id": request_config["tr_id"]},
            )

            # Parse response
            if response.get("rt_cd", "0") == "0":
                # Mark key as submitted only on successful broker acceptance.
                self._submitted_keys.add(idempotency_key)
                output = response.get("output", {})
                return OrderResult(
                    success=True,
                    order_id=idempotency_key,
                    broker_order_id=output.get("ODNO") or output.get("odno"),
                    message=response.get("msg1", "OK"),
                    filled_quantity=quantity,
                    filled_price=price
                )
            else:
                return OrderResult(
                    success=False,
                    order_id=idempotency_key,
                    message=response.get("msg1", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return OrderResult(
                success=False,
                order_id=idempotency_key,
                message=str(e)
            )

    def execute_with_retry(
        self,
        order: "Order",
        max_attempts: int = 3
    ) -> OrderResult:
        """
        Execute order with retry logic.

        Uses order's idempotency_key to prevent duplicates across retries.
        """
        import time

        result: OrderResult = OrderResult(success=False, order_id="", message="No attempts made")

        for attempt in range(max_attempts):
            order.submission_attempts += 1

            if order.side == "buy":
                result = self.buy(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=order.price,
                    idempotency_key=order.idempotency_key
                )
            else:
                result = self.sell(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=order.price,
                    idempotency_key=order.idempotency_key
                )

            if result.success:
                order.broker_order_id = result.broker_order_id
                order.submitted_at = datetime.now(timezone.utc)
                return result

            # Exponential backoff
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                logger.info(f"Order retry in {wait_time}s: {order.idempotency_key}")
                time.sleep(wait_time)

        return result
