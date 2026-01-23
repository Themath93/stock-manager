# LockService API Documentation

## Overview

`LockService` provides distributed stock lock management for multi-worker coordination using PostgreSQL row-level locks with TTL (Time-To-Live) support for crash recovery.

**Location**: `src/stock_manager/service_layer/lock_service.py`

**Key Features**:
- Atomic lock acquisition using PostgreSQL row-level locking
- TTL support for automatic lock expiration (crash recovery)
- Heartbeat mechanism for keeping locks alive
- Lock renewal for extending ownership
- Automatic cleanup of expired locks

---

## Architecture

### Database Schema

The `stock_locks` table stores lock information:

```sql
CREATE TABLE stock_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    worker_id VARCHAR(100) NOT NULL,
    acquired_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    heartbeat_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `idx_stock_locks_symbol` on `symbol`
- `idx_stock_locks_status` on `status`
- `idx_stock_locks_expires_at` on `expires_at`

**Triggers**:
- Auto-update `updated_at` on row modifications

### Lock States

| Status | Description |
|--------|-------------|
| `ACTIVE` | Lock is currently held and valid |
| `EXPIRED` | Lock has expired or been released |

---

## API Reference

### Initialization

```python
from datetime import timedelta
from stock_manager.service_layer.lock_service import LockService

lock_service = LockService(
    db=database_port,
    default_ttl=timedelta(minutes=5)
)
```

**Parameters**:
- `db` (DatabasePort): Database connection port
- `default_ttl` (timedelta): Default time-to-live for locks (default: 5 minutes)

---

### Methods

#### 1. `acquire(symbol, worker_id, ttl=None)`

Acquire lock on a stock symbol atomically.

**Uses PostgreSQL row-level locking** (INSERT ... ON CONFLICT) to ensure atomic acquisition without blocking.

**Parameters**:
- `symbol` (str): Stock symbol to lock (e.g., "005930")
- `worker_id` (str): Worker instance ID
- `ttl` (timedelta, optional): Lock time-to-live (default: default_ttl)

**Returns**: `StockLock` - Acquired lock object

**Raises**:
- `LockAcquisitionError`: If lock is already held by another worker

**Example**:
```python
from datetime import timedelta

try:
    lock = lock_service.acquire(
        symbol="005930",
        worker_id="worker-001",
        ttl=timedelta(minutes=10)
    )
    print(f"Lock acquired: {lock}")
except LockAcquisitionError as e:
    print(f"Failed to acquire lock: {e}")
```

**Implementation Details**:
1. Cleans up any expired locks for the symbol
2. Attempts to insert new lock with `INSERT ... ON CONFLICT DO NOTHING`
3. If symbol exists with ACTIVE status:
   - If owned by same worker → renews the lock
   - If owned by different worker → raises `LockAcquisitionError`

---

#### 2. `release(symbol, worker_id)`

Release lock on a stock symbol.

**Parameters**:
- `symbol` (str): Stock symbol
- `worker_id` (str): Worker ID requesting release

**Returns**: `bool` - True if lock was released, False if not found or not owned

**Raises**:
- `LockNotFoundError`: If lock not found

**Example**:
```python
try:
    success = lock_service.release(
        symbol="005930",
        worker_id="worker-001"
    )
    if success:
        print("Lock released successfully")
except LockNotFoundError as e:
    print(f"Lock not found: {e}")
```

**Implementation Details**:
- Updates lock status to `EXPIRED`
- Only releases if lock is owned by the requesting worker
- Updates `updated_at` timestamp

---

#### 3. `renew(symbol, worker_id, ttl=None)`

Renew lock by extending TTL (Time-To-Live).

**Parameters**:
- `symbol` (str): Stock symbol
- `worker_id` (str): Worker ID requesting renewal
- `ttl` (timedelta, optional): New TTL (default: default_ttl)

**Returns**: `StockLock` - Renewed lock object

**Raises**:
- `LockNotFoundError`: If lock not found or not owned
- `LockExpiredError`: If lock has already expired

**Example**:
```python
try:
    lock = lock_service.renew(
        symbol="005930",
        worker_id="worker-001",
        ttl=timedelta(minutes=10)
    )
    print(f"Lock renewed, expires at: {lock.expires_at}")
except LockExpiredError as e:
    print(f"Cannot renew expired lock: {e}")
```

**Implementation Details**:
- Extends `expires_at` by TTL
- Updates `heartbeat_at` timestamp
- Only renews if lock is owned by requesting worker and not expired

---

#### 4. `heartbeat(symbol, worker_id)`

Send heartbeat to keep lock alive without extending TTL.

**Updates `heartbeat_at` timestamp** to signal that the worker is still alive.

**Parameters**:
- `symbol` (str): Stock symbol
- `worker_id` (str): Worker ID sending heartbeat

**Returns**: `bool` - True if heartbeat was sent, False if lock not found or expired

**Raises**:
- `LockNotFoundError`: If lock not found

**Example**:
```python
try:
    success = lock_service.heartbeat(
        symbol="005930",
        worker_id="worker-001"
    )
    if success:
        print("Heartbeat sent")
except LockNotFoundError as e:
    print(f"Lock not found: {e}")
```

**Implementation Details**:
- Updates `heartbeat_at` to current timestamp
- Does not extend TTL
- Only succeeds if lock is active and owned by requesting worker

---

#### 5. `cleanup_expired()`

Cleanup all expired locks (status=ACTIVE but expires_at < NOW).

**Called automatically** during lock acquisition to clean up stale locks.

**Returns**: `int` - Number of expired locks cleaned up

**Example**:
```python
cleaned_count = lock_service.cleanup_expired()
print(f"Cleaned up {cleaned_count} expired locks")
```

**Implementation Details**:
- Updates all expired ACTIVE locks to EXPIRED status
- Returns count of locks cleaned
- Logs information about cleanup

---

#### 6. `get_lock(symbol)`

Get current lock for a symbol.

**Parameters**:
- `symbol` (str): Stock symbol

**Returns**: `Optional[StockLock]` - Lock if exists, None otherwise

**Example**:
```python
lock = lock_service.get_lock("005930")
if lock:
    print(f"Lock owned by {lock.worker_id}, expires at {lock.expires_at}")
else:
    print("No lock found")
```

---

#### 7. `list_active_locks()`

List all active locks.

**Returns**: `list[StockLock]` - List of active locks (sorted by acquired_at DESC)

**Example**:
```python
active_locks = lock_service.list_active_locks()
for lock in active_locks:
    print(f"{lock.symbol} owned by {lock.worker_id}")
```

---

## Domain Model: StockLock

```python
@dataclass
class StockLock:
    id: UUID
    symbol: str
    worker_id: str
    acquired_at: datetime
    expires_at: datetime
    heartbeat_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    def is_valid(self) -> bool:
        """Check if lock is still valid (not expired)"""
        return self.status == "ACTIVE" and self.expires_at > datetime.utcnow()

    def needs_renewal(self, threshold: timedelta = timedelta(minutes=1)) -> bool:
        """Check if lock needs renewal (expires within threshold)"""
        return (self.expires_at - datetime.utcnow()) < threshold
```

---

## Exceptions

| Exception | Description |
|-----------|-------------|
| `LockAcquisitionError` | Failed to acquire lock (already held by another worker) |
| `LockNotFoundError` | Lock not found in database |
| `LockExpiredError` | Lock has expired and cannot be renewed |

---

## Usage Patterns

### Pattern 1: Basic Lock Acquisition

```python
# Acquire lock
try:
    lock = lock_service.acquire("005930", "worker-001")
    print(f"Lock acquired: {lock}")

    # Do work with stock...

finally:
    # Release lock
    lock_service.release("005930", "worker-001")
```

### Pattern 2: Lock with Periodic Renewal

```python
lock = lock_service.acquire("005930", "worker-001", ttl=timedelta(minutes=10))

try:
    while True:
        # Do work...

        # Renew lock periodically
        if lock.needs_renewal():
            lock = lock_service.renew("005930", "worker-001")
            print("Lock renewed")

        # Send heartbeat to keep alive
        lock_service.heartbeat("005930", "worker-001")

        time.sleep(30)

finally:
    lock_service.release("005930", "worker-001")
```

### Pattern 3: Context Manager Usage

```python
from contextlib import contextmanager

@contextmanager
def acquire_lock(symbol: str, worker_id: str, ttl: timedelta = None):
    lock = lock_service.acquire(symbol, worker_id, ttl)
    try:
        yield lock
    finally:
        lock_service.release(symbol, worker_id)

# Usage
with acquire_lock("005930", "worker-001") as lock:
    print(f"Working with {lock.symbol}")
    # Do work...
```

---

## Error Handling

### Handling Lock Conflicts

```python
try:
    lock = lock_service.acquire("005930", "worker-001")
except LockAcquisitionError:
    # Lock already held by another worker
    # Option 1: Wait and retry
    time.sleep(5)
    lock = lock_service.acquire("005930", "worker-001")

    # Option 2: Try different symbol
    lock = lock_service.acquire("000660", "worker-001")
```

### Handling Expired Locks

```python
try:
    lock = lock_service.renew("005930", "worker-001")
except LockExpiredError:
    # Lock has expired, need to re-acquire
    lock = lock_service.acquire("005930", "worker-001")
```

---

## Testing

See: `tests/unit/domain/test_worker.py` for StockLock model tests

**Example Test**:
```python
def test_lock_expiry():
    from datetime import timedelta
    from stock_manager.domain.worker import StockLock

    lock = StockLock(
        id=uuid4(),
        symbol="005930",
        worker_id="worker-001",
        acquired_at=datetime.utcnow() - timedelta(minutes=10),
        expires_at=datetime.utcnow() - timedelta(minutes=5),
        heartbeat_at=datetime.utcnow() - timedelta(minutes=5),
        status="ACTIVE",
        created_at=datetime.utcnow() - timedelta(minutes=10),
        updated_at=datetime.utcnow() - timedelta(minutes=5),
    )

    assert not lock.is_valid()
    assert lock.needs_renewal(threshold=timedelta(minutes=10))
```

---

## Best Practices

1. **Always release locks**: Use try/finally or context managers to ensure locks are released
2. **Set appropriate TTL**: Match TTL to expected work duration (recommended: 5-10 minutes)
3. **Send heartbeats**: Send heartbeats periodically to indicate worker is alive
4. **Renew before expiry**: Check `lock.needs_renewal()` and renew before TTL expires
5. **Handle conflicts**: Gracefully handle `LockAcquisitionError` by trying different symbols or retrying
6. **Cleanup expired locks**: Call `cleanup_expired()` periodically or before acquiring new locks

---

## Thread Safety

**Thread Safety**: LockService is **not thread-safe** by default. Each worker instance should have its own LockService instance.

For multi-threaded workers:
- Use a single LockService instance per worker
- Ensure database connection is thread-safe (connection pooling)
- Consider using locks around LockService calls if needed

---

## Performance Considerations

1. **Row-level locking**: PostgreSQL row-level locks are lightweight and fast
2. **Index usage**: Queries use indexes on `symbol`, `status`, and `expires_at`
3. **Conflict handling**: Uses `ON CONFLICT` to avoid blocking on lock conflicts
4. **Cleanup**: Expired locks are cleaned up automatically during acquisition

---

## Related Components

- **WorkerMain**: Uses LockService for stock lock management during trading
- **WorkerLifecycleService**: Coordinates with LockService for worker lifecycle
- **DatabasePort**: Provides database access for lock persistence

---

## Future Enhancements

- [ ] Distributed locking with Redis (alternative to PostgreSQL)
- [ ] Lock priority levels
- [ ] Lock transfer between workers
- [ ] Lock statistics and monitoring
- [ ] Lock ownership transfer API
