# WorkerMain API Documentation

## Overview

`WorkerMain` is the primary orchestrator for the automated trading bot, implementing a state machine-driven event loop for stock trading operations.

**Location**: `src/stock_manager/service_layer/worker_main.py`

**Key Features**:
- State machine-based workflow (IDLE → SCANNING → HOLDING → SCANNING → EXITING)
- Async event loop for concurrent operations
- Background heartbeat task for liveness monitoring
- Integration with all worker services (Lock, Lifecycle, Poller, Strategy, Order, Summary)
- Automatic daily summary generation on shutdown

---

## Architecture

### State Machine

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │
     ▼
┌─────────────┐
│  SCANNING   │ ◄────────┐
└──────┬──────┘          │
       │                 │
       │ (buy signal)    │
       │                 │
       ▼                 │
┌─────────────┐           │
│  HOLDING    │           │
└──────┬──────┘           │
       │                 │
       │ (sell signal)   │
       │                 │
       └─────────────────┘
              │
              ▼
         ┌─────────┐
         │ EXITING │
         └─────────┘
```

### State Descriptions

| State | Description | Transitions |
|-------|-------------|-------------|
| **IDLE** | Worker initialization | → SCANNING |
| **SCANNING** | Discover candidates and evaluate buy signals | → HOLDING (buy signal), → SCANNING (no signal) |
| **HOLDING** | Monitor position for sell signal | → SCANNING (sell signal) |
| **EXITING** | Cleanup and shutdown | → (terminated) |

### Event Loop

```python
async def _worker_loop():
    while self._running:
        1. Get current worker status
        2. Execute state handler (_state_idle, _state_scanning, _state_holding, _state_exiting)
        3. Wait poll_interval seconds
        4. Repeat
```

### Background Tasks

```python
async def _heartbeat_loop():
    while self._running:
        1. Send worker heartbeat (WorkerLifecycleService)
        2. Send stock lock heartbeat (if holding)
        3. Wait heartbeat_interval seconds
        4. Repeat
```

---

## API Reference

### Initialization

```python
from datetime import timedelta
from stock_manager.service_layer.worker_main import WorkerMain

worker = WorkerMain(
    worker_id="worker-001",
    lock_service=lock_service,
    worker_lifecycle=worker_lifecycle,
    market_data_poller=market_data_poller,
    strategy_executor=strategy_executor,
    order_service=order_service,
    daily_summary_service=daily_summary_service,
    heartbeat_interval=timedelta(seconds=30),
    poll_interval=timedelta(seconds=10),
    lock_ttl=timedelta(minutes=5),
)
```

**Parameters**:
- `worker_id` (str): Worker instance ID (unique identifier)
- `lock_service` (LockService): Lock service for stock locks
- `worker_lifecycle` (WorkerLifecycleService): Worker lifecycle service
- `market_data_poller` (MarketDataPoller): Market data poller for candidate discovery
- `strategy_executor` (StrategyExecutor): Strategy executor for signal evaluation
- `order_service` (OrderService): Order service for order execution
- `daily_summary_service` (DailySummaryService): Daily summary service for performance tracking
- `heartbeat_interval` (timedelta): Heartbeat interval (default: 30 seconds)
- `poll_interval` (timedelta): Market data poll interval (default: 10 seconds)
- `lock_ttl` (timedelta): Stock lock TTL (default: 5 minutes)

---

### Public Methods

#### 1. `start()`

Start worker main event loop.

**Implements**: ED-001 (Worker Status Machine)

**Workflow**:
1. Register worker with `WorkerLifecycleService`
2. Transition to IDLE status
3. Start background tasks:
   - Heartbeat loop (`_heartbeat_loop`)
   - Worker loop (`_worker_loop`)
4. Wait for worker loop completion
5. Cleanup on shutdown:
   - Stop background tasks
   - Generate daily summary
6. Log completion

**Returns**: `None`

**Raises**: Exception if worker registration fails

**Example**:
```python
import asyncio

async def main():
    worker = WorkerMain(...)
    await worker.start()

asyncio.run(main())
```

**Implementation Details**:
- Uses `asyncio.create_task` for concurrent background tasks
- Automatically transitions from IDLE → SCANNING
- Runs until `_running` flag is set to False or EXITING state is reached

---

#### 2. `stop()`

Stop worker gracefully.

**Workflow**:
1. Set `_running` flag to False
2. Transition worker status to EXITING
3. Worker loop detects EXITING state and stops
4. Background heartbeat loop stops
5. Cleanup is performed

**Returns**: `None`

**Example**:
```python
async def main():
    worker = WorkerMain(...)

    # Start worker in background
    task = asyncio.create_task(worker.start())

    # Stop after 1 hour
    await asyncio.sleep(3600)
    await worker.stop()

    # Wait for worker to stop
    await task
```

**Implementation Details**:
- Non-blocking: Worker loop detects `_running=False` and stops
- Graceful: Completes current state before stopping
- Cleanup: Releases locks and generates daily summary

---

### Private Methods (State Handlers)

#### 3. `_state_idle()`

IDLE state handler.

**Workflow**:
1. Log debug message
2. Transition worker status to SCANNING

**Example**:
```python
# Worker loop calls this when status is IDLE
await self._state_idle()
# Worker transitions to SCANNING state
```

---

#### 4. `_state_scanning()`

SCANNING state handler.

**Implements**:
- WT-002: Market Data Polling
- WT-003: Strategy Evaluation

**Workflow**:
1. Discover candidates using `MarketDataPoller.discover_candidates()`
2. For each candidate:
   - Evaluate buy signal using `StrategyExecutor.should_buy()`
   - If buy signal:
     - Acquire stock lock using `LockService.acquire()`
     - Execute buy order using `_execute_buy()`
     - Transition worker status to HOLDING
     - Set current symbol and lock
     - Exit SCANNING state
3. If no buy signals: Continue to next poll

**Example**:
```python
# Worker loop calls this when status is SCANNING
await self._state_scanning()
# Workflow:
# 1. Discover up to 50 candidates
# 2. Evaluate buy signals
# 3. Buy if signal found
# 4. Transition to HOLDING
```

**Implementation Details**:
- Tries next candidate if lock acquisition fails
- Logs warnings for failed lock acquisitions
- Uses idempotency key for buy orders

---

#### 5. `_state_holding()`

HOLDING state handler.

**Implements**:
- WT-003: Strategy Evaluation

**Workflow**:
1. Check if current symbol is set (error if not)
2. Get current position:
   - Position quantity (TODO: fetch from PositionService)
   - Average price (TODO: fetch from PositionService)
   - Current price (TODO: fetch from market data)
3. Evaluate sell signal using `StrategyExecutor.should_sell()`
4. If sell signal:
   - Execute sell order using `_execute_sell()`
   - Release stock lock using `LockService.release()`
   - Transition worker status to SCANNING
   - Clear current symbol and lock

**Example**:
```python
# Worker loop calls this when status is HOLDING
await self._state_holding()
# Workflow:
# 1. Monitor position
# 2. Evaluate sell signals
# 3. Sell if signal found
# 4. Release lock
# 5. Transition to SCANNING
```

**Implementation Details**:
- Currently uses placeholder values (TODO: implement PositionService integration)
- Uses idempotency key for sell orders
- Releases lock immediately after sell

---

#### 6. `_state_exiting()`

EXITING state handler.

**Workflow**:
1. If holding position:
   - Forced liquidation (TODO: implement UB-003)
   - Release stock lock
2. Stop worker using `WorkerLifecycleService.stop()`

**Example**:
```python
# Worker loop calls this when status is EXITING
await self._state_exiting()
# Workflow:
# 1. Force liquidate if holding
# 2. Release lock
# 3. Stop worker
```

**Implementation Details**:
- Logs warning for forced liquidation
- Releases lock even if forced liquidation fails

---

### Helper Methods

#### 7. `_execute_buy(candidate, buy_signal)`

Execute buy order.

**Parameters**:
- `candidate` (Candidate): Candidate stock to buy
- `buy_signal` (BuySignal): Buy signal with suggested quantity/price

**Workflow**:
1. Create `OrderRequest`:
   - Symbol from candidate
   - Side: BUY
   - Type: MARKET (if price=None) or LIMIT
   - Quantity: from buy signal or default (10)
   - Price: from buy signal or None
   - Idempotency key: unique key with timestamp
2. Create order using `OrderService.create_order()`
3. Send order using `OrderService.send_order()`
4. Log buy execution

**Example**:
```python
# Called from _state_scanning()
await self._execute_buy(candidate, buy_signal)
# Logs: "BUY order executed: 005930, qty=10, confidence=0.85, reason=Strong buy signal"
```

---

#### 8. `_execute_sell(sell_signal)`

Execute sell order.

**Parameters**:
- `sell_signal` (SellSignal): Sell signal with suggested price

**Workflow**:
1. Create `OrderRequest`:
   - Symbol from current symbol
   - Side: SELL
   - Type: MARKET (if price=None) or LIMIT
   - Quantity: placeholder (TODO: fetch from position)
   - Price: from sell signal or None
   - Idempotency key: unique key with timestamp
2. Create order using `OrderService.create_order()`
3. Send order using `OrderService.send_order()`
4. Log sell execution

**Example**:
```python
# Called from _state_holding()
await self._execute_sell(sell_signal)
# Logs: "SELL order executed: 005930, qty=10, confidence=0.90, reason=Take profit reached"
```

---

#### 9. `_heartbeat_loop()`

Background task: Send heartbeat periodically.

**Workflow**:
While running:
1. Send worker heartbeat using `WorkerLifecycleService.heartbeat()`
2. If holding stock: Send lock heartbeat using `LockService.heartbeat()`
3. Wait `heartbeat_interval` seconds
4. Repeat

**Example**:
```python
# Started automatically in start() method
# Runs in background every 30 seconds (default)
# Sends:
# - Worker heartbeat (to WorkerLifecycleService)
# - Stock lock heartbeat (to LockService, if holding)
```

---

#### 10. `_cleanup()`

Cleanup on shutdown.

**Workflow**:
1. Generate daily summary using `DailySummaryService.generate_summary()`
2. Log error if summary generation fails

**Example**:
```python
# Called automatically after worker loop stops
# Generates daily summary with:
# - Total trades
# - Realized PnL
# - Unrealized PnL
# - Win rate
# - Profit factor
# - Max drawdown
```

---

## Usage Patterns

### Pattern 1: Basic Worker Lifecycle

```python
import asyncio
from datetime import timedelta
from stock_manager.service_layer.worker_main import WorkerMain

async def main():
    # Initialize worker
    worker = WorkerMain(
        worker_id="worker-001",
        lock_service=lock_service,
        worker_lifecycle=worker_lifecycle,
        market_data_poller=market_data_poller,
        strategy_executor=strategy_executor,
        order_service=order_service,
        daily_summary_service=daily_summary_service,
    )

    # Start worker
    await worker.start()

asyncio.run(main())
```

### Pattern 2: Worker with Timeout

```python
async def main():
    worker = WorkerMain(...)

    # Start worker in background
    task = asyncio.create_task(worker.start())

    # Stop after 1 hour
    await asyncio.sleep(3600)
    await worker.stop()

    # Wait for graceful shutdown
    await task
```

### Pattern 3: Multiple Workers

```python
async def main():
    # Create multiple workers
    workers = [
        WorkerMain(worker_id=f"worker-{i:03d}", ...)
        for i in range(5)
    ]

    # Start all workers in parallel
    tasks = [asyncio.create_task(w.start()) for w in workers]

    # Wait for all workers (or stop them externally)
    await asyncio.gather(*tasks)
```

---

## State Transitions

### Transition 1: IDLE → SCANNING

```python
# Occurs immediately after worker starts
# _state_idle() called
# Status changes from IDLE to SCANNING
```

### Transition 2: SCANNING → HOLDING

```python
# Occurs when buy signal is found
# _state_scanning() called
# Workflow:
# 1. Discover candidates
# 2. Evaluate buy signals
# 3. If buy signal:
#    - Acquire lock
#    - Execute buy order
#    - Transition to HOLDING
```

### Transition 3: HOLDING → SCANNING

```python
# Occurs when sell signal is found
# _state_holding() called
# Workflow:
# 1. Evaluate sell signals
# 2. If sell signal:
#    - Execute sell order
#    - Release lock
#    - Transition to SCANNING
```

### Transition 4: SCANNING → EXITING

```python
# Occurs when stop() is called
# _state_exiting() called
# Workflow:
# 1. Force liquidate if holding
# 2. Release lock
# 3. Stop worker
```

---

## Error Handling

### Exception in Worker Loop

```python
try:
    # Worker loop continues even if exception occurs
    # Error is logged and loop continues
    pass
except Exception as e:
    logger.error(f"Error in worker loop: {e}")
    await asyncio.sleep(self.poll_interval.total_seconds())
```

### Exception in Heartbeat Loop

```python
try:
    # Heartbeat loop continues even if exception occurs
    # Error is logged and loop continues
    pass
except Exception as e:
    logger.error(f"Failed to send heartbeat: {e}")
```

### Exception in Order Execution

```python
# If buy/sell order fails, exception is raised
# Worker catches and logs error
# State transition continues (may try next candidate or retry)
```

---

## Best Practices

1. **Use unique worker_id**: Each worker instance should have a unique ID
2. **Set appropriate intervals**:
   - `heartbeat_interval`: 30-60 seconds (balance between liveness and overhead)
   - `poll_interval`: 10-30 seconds (balance between responsiveness and load)
   - `lock_ttl`: 5-10 minutes (match expected holding duration)
3. **Handle shutdown gracefully**: Always call `stop()` to ensure cleanup
4. **Monitor logs**: Monitor debug logs for state transitions and order execution
5. **Implement PositionService**: Replace placeholder position data with actual PositionService integration
6. **Implement forced liquidation**: Implement UB-003 for proper shutdown liquidation

---

## Integration Points

### Required Services

WorkerMain integrates with the following services:

1. **LockService** (`lock_service`):
   - Acquire stock locks before buying
   - Release locks after selling
   - Send heartbeats while holding

2. **WorkerLifecycleService** (`worker_lifecycle`):
   - Register worker on startup
   - Transition worker status
   - Send heartbeats
   - Stop worker on shutdown

3. **MarketDataPoller** (`market_data_poller`):
   - Discover candidates in SCANNING state

4. **StrategyExecutor** (`strategy_executor`):
   - Evaluate buy signals in SCANNING state
   - Evaluate sell signals in HOLDING state

5. **OrderService** (`order_service`):
   - Create and send buy/sell orders

6. **DailySummaryService** (`daily_summary_service`):
   - Generate daily summary on shutdown

---

## Future Enhancements

- [ ] PositionService integration for position tracking
- [ ] Forced liquidation (UB-003) implementation
- [ ] State transition logging for debugging
- [ ] Performance metrics collection
- [ ] Worker health check endpoint
- [ ] Dynamic configuration updates
- [ ] State persistence for crash recovery
- [ ] Multi-worker coordination

---

## Related Components

- **LockService**: Manages distributed stock locks
- **WorkerLifecycleService**: Manages worker lifecycle
- **MarketDataPoller**: Discovers trading candidates
- **StrategyExecutor**: Evaluates buy/sell signals
- **OrderService**: Executes orders
- **DailySummaryService**: Generates performance summaries
- **PnLCalculator**: Calculates profit/loss

---

## Testing

**Example Test** (integration test with mock services):
```python
import pytest
from datetime import timedelta

@pytest.mark.asyncio
async def test_worker_main_state_machine():
    # Setup mock services
    mock_lock_service = MockLockService()
    mock_lifecycle = MockWorkerLifecycleService()
    # ... (setup other mock services)

    # Create worker
    worker = WorkerMain(
        worker_id="test-worker",
        lock_service=mock_lock_service,
        worker_lifecycle=mock_lifecycle,
        # ... (other services)
        poll_interval=timedelta(seconds=1),
    )

    # Start worker
    task = asyncio.create_task(worker.start())

    # Wait for state transitions
    await asyncio.sleep(5)

    # Stop worker
    await worker.stop()
    await task

    # Verify state transitions
    assert mock_lifecycle.transitions == [
        WorkerStatus.IDLE,
        WorkerStatus.SCANNING,
        WorkerStatus.EXITING,
    ]
```

---

## Troubleshooting

### Worker Stuck in SCANNING State

**Cause**: No buy signals generated by strategy

**Solution**:
- Check strategy executor configuration
- Verify candidate discovery is working
- Review market data quality

### Worker Not Sending Heartbeats

**Cause**: Exception in heartbeat loop

**Solution**:
- Check logs for heartbeat errors
- Verify LockService connectivity
- Ensure worker is still running

### Lock Not Released on Shutdown

**Cause**: Worker crashed before cleanup

**Solution**:
- Lock will expire after TTL
- Manual cleanup via `LockService.cleanup_expired()`
- Verify proper shutdown handling

### Daily Summary Not Generated

**Cause**: Exception in summary generation

**Solution**:
- Check logs for summary errors
- Verify DailySummaryService connectivity
- Ensure worker shutdown completes
