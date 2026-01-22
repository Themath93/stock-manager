# Schema and State Diagrams (Mermaid)

This document provides visual references for the database schema and core state transitions.
For full DDL, see `ai_developer_guides/DB_SCHEMA_DDL.md`.
Use Mermaid-compatible renderers to view diagrams.

---

## 1) Core Schema (ERD)

```mermaid
erDiagram
    STRATEGIES {
        BIGINT id PK
        TEXT name
        TEXT description
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    STRATEGY_PARAMS {
        BIGINT id PK
        BIGINT strategy_id FK
        DATE trade_date
        INT version
        JSONB params
        ENUM status
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    ORDERS {
        BIGINT id PK
        TEXT broker_order_id
        TEXT idempotency_key
        TEXT symbol
        ENUM side
        ENUM order_type
        NUMERIC qty
        NUMERIC price
        ENUM status
        TIMESTAMPTZ requested_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    FILLS {
        BIGINT id PK
        BIGINT order_id FK
        TEXT broker_fill_id
        TEXT symbol
        NUMERIC qty
        NUMERIC price
        TIMESTAMPTZ filled_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    POSITIONS {
        BIGINT id PK
        TEXT symbol
        NUMERIC qty
        NUMERIC avg_price
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    EVENTS {
        BIGINT id PK
        ENUM level
        TEXT message
        JSONB payload
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    STRATEGIES ||--o{ STRATEGY_PARAMS : has
    ORDERS ||--o{ FILLS : fills
```

---

## 2) Order Status State Machine

```mermaid
stateDiagram-v2
    [*] --> NEW
    NEW --> SENT
    SENT --> PARTIAL
    PARTIAL --> FILLED
    SENT --> FILLED
    SENT --> CANCELED
    SENT --> REJECTED
    SENT --> ERROR
```

Rules:
- Transitions are one-way; no rollback.
- Broker events can skip intermediate states (e.g., SENT -> FILLED).

---

## 3) Startup Recovery Flow (Summary)

```mermaid
flowchart TD
    A[Load config] --> B[Broker login]
    B --> C[Account and cash check]
    C --> D[Load active strategy params]
    D --> E[Load open orders from DB]
    E --> F[Fetch broker order states]
    F --> G[Resolve conflicts]
    G --> H[Recalculate positions]
    H --> I[Init risk guardrails]
    I --> J[Subscribe realtime events]
    J --> K[Enter trading loop]

    B --> X[Fail: stop mode]
    D --> X
    G --> X
```

---

## 4) Risk Gate (Order Pipeline)

```mermaid
flowchart LR
    S[Signal] --> R{Risk check}
    R -->|Pass| O[Create order]
    R -->|Block| E[Emit event]
    O --> T[Send to broker]
    T --> D[Persist order]
```

Notes:
- Risk check happens before broker call.
- If blocked, a structured event is recorded.
