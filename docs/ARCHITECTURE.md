# Stock Manager Architecture (v2.0)

## Overview

Stock Manager is a Python 3.13-based automated trading bot with a hexagonal architecture pattern. This document provides a comprehensive overview of the system architecture, components, and data flow.

**Version**: 2.0 (with Worker Architecture)
**Last Updated**: 2026-01-24

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Stock Manager                                     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    Worker Process                                │    │
│  │                                                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐                 │    │
│  │  │ Market   │  │ Strategy │  │ LockService  │                 │    │
│  │  │ Poller   │  │ Executor │  │              │                 │    │
│  │  └────┬─────┘  └────┬─────┘  └──────┬───────┘                 │    │
│  │       │              │               │                          │    │
│  │       │              ▼               ▼                          │    │
│  │       │       ┌─────────┐         │                          │    │
│  │       │       │ Worker  │─────────┘                          │    │
│  │       │       │  Main   │                                     │    │
│  │       │       └────┬────┘                                     │    │
│  │       │            │                                          │    │
│  │       │            ▼                                          │    │
│  │       │       ┌─────────┐                                     │    │
│  │       └───────┤  Order  │────────────┐                        │    │
│  │               │ Service │            │                        │    │
│  │               └─────────┘            │                        │    │
│  │                                      │                        │    │
│  └──────────────────────────────────────┼────────────────────────┘    │
│                                         ▼                             │
│                              ┌──────────────────┐                      │
│                              │ Service Layer    │                      │
│                              └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │    Domain        │
                              └──────────────────┘
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               │                         │                         │
               ▼                         ▼                         ▼
        ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
        │   Broker    │          │    Storage   │          │  Slack/Logs │
        │   Adapter   │          │   Adapter   │          │   Adapter   │
        └─────────────┘          └─────────────┘          └─────────────┘
               │                         │                         │
               ▼                         ▼                         ▼
        ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
        │     KIS     │          │  PostgreSQL │          │   Slack     │
        │  REST/WS    │          │   Database  │          │   API       │
        └─────────────┘          └─────────────┘          └─────────────┘
```

---

## Component Overview

### 1. Domain Layer

**Location**: `src/stock_manager/domain/`

**Purpose**: Pure domain models and business logic (no external dependencies)

**Components**:
- `order.py`: Order, Fill, OrderStatus, OrderRequest
- `worker.py`: WorkerStatus, StockLock, WorkerProcess, Candidate, DailySummary
- `strategy.py`: BuySignal, SellSignal
- `position.py`: Position, PositionSnapshot

**Key Models**:

```python
# Order domain
class Order:
    id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Optional[Decimal]
    status: OrderStatus
    # ...

# Worker domain
class StockLock:
    id: UUID
    symbol: str
    worker_id: str
    acquired_at: datetime
    expires_at: datetime
    # ...

class WorkerStatus(Enum):
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    HOLDING = "HOLDING"
    EXITING = "EXITING"
```

---

### 2. Service Layer

**Location**: `src/stock_manager/service_layer/`

**Purpose**: Use cases and business logic orchestration

**Components**:

#### Order Management
- `order_service.py`: Order creation, transmission, cancellation, fill processing
- `position_service.py`: Position calculation and updates

#### Worker Architecture (NEW)
- `lock_service.py`: Distributed stock lock management
- `worker_lifecycle_service.py`: Worker lifecycle management
- `market_data_poller.py`: Market data polling and candidate discovery
- `strategy_executor.py`: Buy/sell signal evaluation
- `pnl_calculator.py`: PnL calculations (realized, unrealized, daily)
- `daily_summary_service.py`: Daily performance summary generation
- `worker_main.py`: Worker orchestrator (state machine, event loop)

**Key Services**:

```python
# LockService
class LockService:
    def acquire(symbol, worker_id, ttl) -> StockLock
    def release(symbol, worker_id) -> bool
    def renew(symbol, worker_id, ttl) -> StockLock
    def heartbeat(symbol, worker_id) -> bool
    def cleanup_expired() -> int

# WorkerMain
class WorkerMain:
    async def start() -> None
    async def stop() -> None
    # State machine: IDLE → SCANNING → HOLDING → SCANNING → EXITING
```

---

### 3. Adapter Layer

**Location**: `src/stock_manager/adapters/`

**Purpose**: External dependency integration

**Components**:

#### Broker Adapter
- `broker/`: Korean Investment Securities (KIS) REST/WS integration
  - `kis_rest_client.py`: REST API client
  - `kis_websocket_client.py`: WebSocket client
  - `kis_config.py`: Configuration
  - `kis_broker_adapter.py`: Broker port implementation

#### Storage Adapter
- `storage/`: Database integration
  - `port.py`: Database port interface
  - `schema/`: Database schemas
    - `orders_schema.sql`
    - `fills_schema.sql`
    - `worker_schema.sql` (NEW)

#### Notification Adapter
- `notifications/`: Slack integration
  - `slack_client.py`: Slack API client

#### Observability Adapter
- `observability/`: Logging and metrics
  - `logger.py`: Logging configuration

---

### 4. Entry Points

**Location**: `src/stock_manager/entrypoints/`

**Purpose**: Application entry points (CLI, worker, scheduler)

**Components**:
- `cli.py`: Command-line interface (TODO)
- `worker.py`: Worker entry point (TODO)
- `scheduler.py`: Scheduler entry point (TODO)

---

## Data Flow

### 1. Worker Trading Flow

```
┌─────────────┐
│ WorkerMain  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ State Machine: IDLE → SCANNING → HOLDING → EXITING     │
└──────────────────────────────────────────────────────────┘
       │
       ├─▶ SCANNING State
       │       │
       │       ▼
       │   ┌──────────────────────────┐
       │   │ 1. Discover Candidates   │
       │   │    (MarketDataPoller)    │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 2. Evaluate Buy Signal  │
       │   │    (StrategyExecutor)    │
       │   └──────────┬───────────────┘
       │              │
       │              ▼ (if buy signal)
       │   ┌──────────────────────────┐
       │   │ 3. Acquire Stock Lock   │
       │   │    (LockService)        │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 4. Execute Buy Order    │
       │   │    (OrderService)       │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 5. Transition to HOLDING│
       │   └──────────────────────────┘
       │
       ├─▶ HOLDING State
       │       │
       │       ▼
       │   ┌──────────────────────────┐
       │   │ 1. Monitor Position     │
       │   │    (PositionService)     │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 2. Evaluate Sell Signal │
       │   │    (StrategyExecutor)    │
       │   └──────────┬───────────────┘
       │              │
       │              ▼ (if sell signal)
       │   ┌──────────────────────────┐
       │   │ 3. Execute Sell Order   │
       │   │    (OrderService)       │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 4. Release Lock        │
       │   │    (LockService)        │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │   ┌──────────────────────────┐
       │   │ 5. Transition to SCAN  │
       │   └──────────────────────────┘
       │
       └─▶ EXITING State
               │
               ▼
           ┌──────────────────────────┐
           │ 1. Force Liquidate     │
           │    (if holding)         │
           └──────────┬───────────────┘
                      │
                      ▼
           ┌──────────────────────────┐
           │ 2. Generate Summary    │
           │    (DailySummaryService)│
           └──────────┬───────────────┘
                      │
                      ▼
           ┌──────────────────────────┐
           │ 3. Stop Worker         │
           └──────────────────────────┘
```

### 2. Order Execution Flow

```
┌─────────────┐
│ WorkerMain  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│ OrderService            │
│ 1. create_order()      │
│ 2. send_order()        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ BrokerPort              │
│ 1. validate_order()     │
│ 2. submit_order()       │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ KISBrokerAdapter        │
│ 1. POST to KIS API      │
│ 2. Get order ID         │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ KIS REST API            │
│ /uapi/domestic-stock/v1 │
│ /ordering/order         │
└──────────────────────────┘

Fill Processing (WebSocket):
┌──────────────────────────┐
│ KIS WebSocket           │
│ (fills stream)          │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ KISBrokerAdapter        │
│ 1. Parse fill message   │
│ 2. Create Fill object   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ OrderService            │
│ 1. process_fill()       │
│ 2. Update order status  │
│ 3. Update position      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Database                │
│ 1. Store fill          │
│ 2. Update order        │
│ 3. Update position     │
└──────────────────────────┘
```

### 3. Lock Management Flow

```
┌─────────────┐
│ WorkerMain  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│ LockService             │
│ 1. acquire(symbol)     │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Database (PostgreSQL)    │
│ 1. INSERT ... ON CONFLICT│
│ 2. row-level lock       │
└──────────┬───────────────┘
           │
           ▼ (success)
┌──────────────────────────┐
│ StockLock               │
│ - symbol: "005930"      │
│ - worker_id: "w-001"    │
│ - expires_at: NOW+5min   │
└──────────┬───────────────┘
           │
           ▼ (periodic)
┌──────────────────────────┐
│ LockService             │
│ 1. heartbeat()         │
│ 2. renew()             │
└──────────┬───────────────┘
           │
           ▼ (after sell)
┌──────────────────────────┐
│ LockService             │
│ 1. release()           │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Database                │
│ 1. UPDATE status=EXPIRED│
└──────────────────────────┘
```

---

## Database Schema

### Core Tables

#### 1. Orders
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(10) NOT NULL,
    qty DECIMAL(18, 4) NOT NULL,
    price DECIMAL(18, 2),
    status VARCHAR(20) NOT NULL,
    broker_order_id VARCHAR(100),
    idempotency_key VARCHAR(200) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. Fills
```sql
CREATE TABLE fills (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    qty DECIMAL(18, 4) NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    fill_time TIMESTAMP NOT NULL,
    broker_fill_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. Stock Locks (NEW)
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

#### 4. Worker Processes (NEW)
```sql
CREATE TABLE worker_processes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL,
    current_symbol VARCHAR(20),
    last_heartbeat_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Daily Summaries (NEW)
```sql
CREATE TABLE daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id VARCHAR(100) NOT NULL,
    summary_date DATE NOT NULL,
    total_trades INTEGER NOT NULL,
    realized_pnl DECIMAL(18, 2) NOT NULL,
    unrealized_pnl DECIMAL(18, 2) NOT NULL,
    win_rate DECIMAL(5, 4) NOT NULL,
    profit_factor DECIMAL(18, 4) NOT NULL,
    max_drawdown DECIMAL(18, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(worker_id, summary_date)
);
```

---

## Ports and Adapters (Hexagonal Architecture)

### Ports (Interfaces)

**Location**: `src/stock_manager/adapters/`

#### BrokerPort
```python
class BrokerPort(Protocol):
    def submit_order(self, order: Order) -> str
    def cancel_order(self, order_id: str) -> bool
    def get_account_balance(self) -> AccountBalance
    def get_positions(self) -> list[Position]
```

#### DatabasePort
```python
class DatabasePort(Protocol):
    def execute_query(self, query: str, params, fetch_one: bool, fetch_all: bool)
    def begin_transaction(self)
    def commit_transaction(self)
    def rollback_transaction(self)
```

#### NotificationPort
```python
class NotificationPort(Protocol):
    def send_message(self, message: str, channel: str) -> str
    def update_message(self, message_id: str, message: str) -> bool
```

#### StrategyPort
```python
class StrategyPort(Protocol):
    async def should_buy(self, candidate: Candidate) -> Optional[BuySignal]
    async def should_sell(self, symbol: str, ...) -> Optional[SellSignal]
```

### Adapters (Implementations)

#### KISBrokerAdapter
- Implements BrokerPort
- Uses KIS REST API for order submission
- Uses KIS WebSocket for fill updates

#### PostgreSQLAdapter (TODO)
- Implements DatabasePort
- Uses psycopg2 for PostgreSQL connectivity
- Connection pooling support

#### SlackNotificationAdapter
- Implements NotificationPort
- Uses Slack Web API for notifications

---

## Worker Architecture Details

### Worker State Machine

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │
     ▼
┌─────────────┐
│  SCANNING   │ ◄────────┐
└──────┬──────┘          │
       │ (buy signal)    │
       │                 │
       ▼                 │ (sell signal)
┌─────────────┐           │
│  HOLDING    │───────────┘
└──────┬──────┘
       │
       │ (stop/shutdown)
       ▼
   ┌─────────┐
   │ EXITING │
   └─────────┘
```

### Worker Services

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| **WorkerMain** | Orchestrator | `start()`, `stop()`, state machine |
| **LockService** | Stock locks | `acquire()`, `release()`, `renew()`, `heartbeat()` |
| **WorkerLifecycleService** | Worker lifecycle | `start()`, `stop()`, `heartbeat()`, `transition_status()` |
| **MarketDataPoller** | Candidate discovery | `discover_candidates()` |
| **StrategyExecutor** | Signal evaluation | `should_buy()`, `should_sell()` |
| **OrderService** | Order execution | `create_order()`, `send_order()`, `cancel_order()` |
| **PnLCalculator** | PnL calculations | `calculate_realized_pnl()`, `calculate_unrealized_pnl()` |
| **DailySummaryService** | Performance summary | `generate_summary()`, `get_summary()` |

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/stock_manager

# KIS Broker
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_no

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Worker
WORKER_HEARTBEAT_INTERVAL=30
WORKER_POLL_INTERVAL=10
WORKER_LOCK_TTL=300
```

---

## Deployment

### Local Development
```bash
# Install dependencies
pip install -e .

# Setup database
createdb stock_manager
psql -d stock_manager -f src/stock_manager/adapters/storage/schema/orders_schema.sql
psql -d stock_manager -f src/stock_manager/adapters/storage/schema/fills_schema.sql
psql -d stock_manager -f src/stock_manager/adapters/storage/schema/worker_schema.sql

# Run tests
pytest tests/
```

### Production Deployment
```bash
# Use Docker for deployment
docker-compose up -d

# Multiple workers
docker-compose up -d --scale worker=5
```

---

## Future Enhancements

- [ ] PostgreSQL adapter implementation
- [ ] Worker crash recovery (TTL cleanup, stale lock detection)
- [ ] Daily forced liquidation (T-Δ based)
- [ ] PositionService implementation
- [ ] Multi-worker coordination
- [ ] Performance metrics collection
- [ ] Health check endpoints
- [ ] State persistence for crash recovery

---

## Documentation

- **API Documentation**:
  - [LockService API](./lock_service_api.md)
  - [WorkerMain API](./worker_main_api.md)

- **Specifications**:
  - [SPEC-BACKEND-002](./SPEC-BACKEND-002.md)
  - [SPEC-BACKEND-WORKER-004](./SPEC-BACKEND-WORKER-004-implementation-plan.md)

- **AI Developer Guides**:
  - [Slack Notification Guide](../ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md)

---

## References

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Python Asyncio](https://docs.python.org/3/library/asyncio.html)
- [PostgreSQL Row-Level Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
