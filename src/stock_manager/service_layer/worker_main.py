"""
Worker Main

Worker orchestrator that implements the worker state machine and event loop.
Implements ED-001: Worker Status Machine and all event-driven requirements.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from ..domain.worker import WorkerStatus
from ..service_layer.lock_service import LockService
from ..service_layer.worker_lifecycle_service import WorkerLifecycleService
from ..service_layer.market_data_poller import MarketDataPoller
from ..service_layer.strategy_executor import StrategyExecutor, BuySignal, SellSignal
from ..service_layer.order_service import OrderService, OrderRequest, OrderType, OrderSide
from ..service_layer.daily_summary_service import DailySummaryService

logger = logging.getLogger(__name__)


class WorkerMain:
    """Worker Main Orchestrator

    Implements the worker state machine:
    IDLE -> SCANNING -> HOLDING -> SCANNING -> EXITING

    Event-driven workflow:
    1. Scan market for candidates (WT-002)
    2. Evaluate strategy for buy/sell signals (WT-003)
    3. Acquire stock lock before buying (WH-001)
    4. Execute buy/sell orders via OrderService
    5. Hold position and monitor for sell signal
    6. Release lock after sell
    7. Generate daily summary (WH-004)
    """

    def __init__(
        self,
        worker_id: str,
        lock_service: LockService,
        worker_lifecycle: WorkerLifecycleService,
        market_data_poller: MarketDataPoller,
        strategy_executor: StrategyExecutor,
        order_service: OrderService,
        daily_summary_service: DailySummaryService,
        heartbeat_interval: timedelta = timedelta(seconds=30),
        poll_interval: timedelta = timedelta(seconds=10),
        lock_ttl: timedelta = timedelta(minutes=5),
    ):
        """Initialize Worker Main

        Args:
            worker_id: Worker instance ID
            lock_service: Lock service for stock locks
            worker_lifecycle: Worker lifecycle service
            market_data_poller: Market data poller
            strategy_executor: Strategy executor
            order_service: Order service
            daily_summary_service: Daily summary service
            heartbeat_interval: Heartbeat interval
            poll_interval: Market data poll interval
            lock_ttl: Stock lock TTL
        """
        self.worker_id = worker_id
        self.lock_service = lock_service
        self.worker_lifecycle = worker_lifecycle
        self.market_data_poller = market_data_poller
        self.strategy_executor = strategy_executor
        self.order_service = order_service
        self.daily_summary_service = daily_summary_service
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        self.lock_ttl = lock_ttl

        self._running = False
        self._current_symbol: Optional[str] = None
        self._current_lock: Optional[any] = None  # StockLock

    async def start(self) -> None:
        """Start worker main event loop

        Implements ED-001: Worker Status Machine
        """
        logger.info(f"Starting worker {self.worker_id}")

        # Register worker
        self.worker_lifecycle.start(worker_id=self.worker_id)
        self.worker_lifecycle.transition_status(self.worker_id, WorkerStatus.IDLE)

        # Start background tasks
        self._running = True
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        worker_task = asyncio.create_task(self._worker_loop())

        # Wait for worker loop completion
        await worker_task

        # Cleanup
        self._running = False
        await heartbeat_task
        await self._cleanup()

        logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """Stop worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}")
        self._running = False

        # Transition to EXITING status
        try:
            self.worker_lifecycle.transition_status(self.worker_id, WorkerStatus.EXITING)
        except Exception as e:
            logger.warning(f"Failed to transition to EXITING status: {e}")

    async def _heartbeat_loop(self) -> None:
        """Background task: Send heartbeat periodically"""
        while self._running:
            try:
                # Send worker heartbeat
                self.worker_lifecycle.heartbeat(self.worker_id)

                # Renew stock lock if holding
                if self._current_lock:
                    self.lock_service.heartbeat(self._current_symbol, self.worker_id)

            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")

            await asyncio.sleep(self.heartbeat_interval.total_seconds())

    async def _worker_loop(self) -> None:
        """Main worker event loop

        Implements state machine:
        IDLE -> SCANNING -> HOLDING -> SCANNING -> EXITING
        """
        while self._running:
            try:
                # Get current worker status
                worker = self.worker_lifecycle.get_worker(self.worker_id)
                if worker is None:
                    logger.error(f"Worker {self.worker_id} not found")
                    break

                # Execute state machine
                if worker.status == WorkerStatus.IDLE:
                    await self._state_idle()

                elif worker.status == WorkerStatus.SCANNING:
                    await self._state_scanning()

                elif worker.status == WorkerStatus.HOLDING:
                    await self._state_holding()

                elif worker.status == WorkerStatus.EXITING:
                    await self._state_exiting()
                    break

                else:
                    logger.error(f"Unknown worker status: {worker.status}")
                    break

                # Wait before next iteration
                await asyncio.sleep(self.poll_interval.total_seconds())

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(self.poll_interval.total_seconds())

    async def _state_idle(self) -> None:
        """IDLE state: Transition to SCANNING"""
        logger.debug(f"Worker {self.worker_id} in IDLE state")
        self.worker_lifecycle.transition_status(self.worker_id, WorkerStatus.SCANNING)

    async def _state_scanning(self) -> None:
        """SCANNING state: Discover candidates and evaluate buy signals

        Implements WT-002: Market Data Polling
        Implements WT-003: Strategy Evaluation
        """
        logger.debug(f"Worker {self.worker_id} in SCANNING state")

        try:
            # Discover candidates (WT-002)
            candidates = await self.market_data_poller.discover_candidates(max_candidates=50)

            # Evaluate buy signals (WT-003)
            for candidate in candidates:
                buy_signal = await self.strategy_executor.should_buy(candidate)

                if buy_signal:
                    # Acquire stock lock (WH-001)
                    try:
                        lock = self.lock_service.acquire(
                            symbol=candidate.symbol,
                            worker_id=self.worker_id,
                            ttl=self.lock_ttl,
                        )

                        # Execute buy order
                        await self._execute_buy(candidate, buy_signal)

                        # Transition to HOLDING state
                        self.worker_lifecycle.transition_status(
                            self.worker_id,
                            WorkerStatus.HOLDING,
                            current_symbol=candidate.symbol,
                        )
                        self._current_symbol = candidate.symbol
                        self._current_lock = lock

                        return  # Exit SCANNING state

                    except Exception as e:
                        logger.warning(f"Failed to acquire lock for {candidate.symbol}: {e}")
                        continue  # Try next candidate

            logger.debug(f"No buy signals for worker {self.worker_id}")

        except Exception as e:
            logger.error(f"Error in SCANNING state: {e}")

    async def _state_holding(self) -> None:
        """HOLDING state: Monitor for sell signal

        Implements WT-003: Strategy Evaluation
        """
        logger.debug(f"Worker {self.worker_id} in HOLDING state")

        if self._current_symbol is None:
            logger.warning("Worker in HOLDING state but no symbol set")
            self.worker_lifecycle.transition_status(self.worker_id, WorkerStatus.SCANNING)
            return

        try:
            # Get current position
            # TODO: Fetch position from PositionService
            position_qty = Decimal("10")  # Placeholder
            avg_price = Decimal("1000")  # Placeholder
            current_price = Decimal("1050")  # Placeholder

            # Evaluate sell signal (WT-003)
            sell_signal = await self.strategy_executor.should_sell(
                symbol=self._current_symbol,
                position_qty=position_qty,
                avg_price=avg_price,
                current_price=current_price,
            )

            if sell_signal:
                # Execute sell order
                await self._execute_sell(sell_signal)

                # Release stock lock (WH-001)
                self.lock_service.release(self._current_symbol, self.worker_id)

                # Transition back to SCANNING state
                self.worker_lifecycle.transition_status(
                    self.worker_id,
                    WorkerStatus.SCANNING,
                    current_symbol=None,
                )
                self._current_symbol = None
                self._current_lock = None

        except Exception as e:
            logger.error(f"Error in HOLDING state: {e}")

    async def _state_exiting(self) -> None:
        """EXITING state: Cleanup and shutdown"""
        logger.debug(f"Worker {self.worker_id} in EXITING state")

        # If holding position, sell it (forced liquidation if needed)
        if self._current_symbol:
            try:
                # TODO: Implement forced liquidation (UB-003)
                logger.warning(f"Forced liquidation for {self._current_symbol} on shutdown")

                # Release lock
                self.lock_service.release(self._current_symbol, self.worker_id)

            except Exception as e:
                logger.error(f"Error during shutdown cleanup: {e}")

        # Stop worker
        self.worker_lifecycle.stop(self.worker_id)

    async def _execute_buy(self, candidate: any, buy_signal: BuySignal) -> None:
        """Execute buy order

        Args:
            candidate: Candidate stock
            buy_signal: Buy signal
        """
        try:
            # Create order request
            qty = buy_signal.suggested_qty or Decimal("10")  # Placeholder
            price = buy_signal.suggested_price  # None for market order

            order_request = OrderRequest(
                symbol=candidate.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
                qty=qty,
                price=price,
                idempotency_key=f"{self.worker_id}_buy_{candidate.symbol}_{datetime.utcnow().isoformat()}",
            )

            # Execute order via OrderService
            order = self.order_service.create_order(order_request)
            self.order_service.send_order(order.id)

            logger.info(
                f"BUY order executed: {candidate.symbol}, qty={qty}, "
                f"confidence={buy_signal.confidence}, reason={buy_signal.reason}"
            )

        except Exception as e:
            logger.error(f"Failed to execute buy order: {e}")
            raise

    async def _execute_sell(self, sell_signal: SellSignal) -> None:
        """Execute sell order

        Args:
            sell_signal: Sell signal
        """
        try:
            # TODO: Fetch actual position quantity
            qty = Decimal("10")  # Placeholder

            # Create order request
            price = sell_signal.suggested_price  # None for market order

            order_request = OrderRequest(
                symbol=self._current_symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
                qty=qty,
                price=price,
                idempotency_key=f"{self.worker_id}_sell_{self._current_symbol}_{datetime.utcnow().isoformat()}",
            )

            # Execute order via OrderService
            order = self.order_service.create_order(order_request)
            self.order_service.send_order(order.id)

            logger.info(
                f"SELL order executed: {self._current_symbol}, qty={qty}, "
                f"confidence={sell_signal.confidence}, reason={sell_signal.reason}"
            )

        except Exception as e:
            logger.error(f"Failed to execute sell order: {e}")
            raise

    async def _cleanup(self) -> None:
        """Cleanup on shutdown"""
        # Generate daily summary (WH-004)
        try:
            self.daily_summary_service.generate_summary(self.worker_id)
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
