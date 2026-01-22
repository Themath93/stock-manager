# Database Schema DDL (PostgreSQL)

이 문서는 **DB 스키마의 단일 기준**이다. 스키마 변경은 이 문서와 마이그레이션에 동시에 반영한다.

**강제 규칙**
- 모든 테이블은 `created_at`, `updated_at` 컬럼을 **TIMESTAMPTZ**(datetime)로 반드시 포함한다.
- `created_at`, `updated_at` 기본값은 `NOW()`.
- `updated_at` 갱신은 **애플리케이션 또는 트리거**로 처리한다.

---

## 1. Enum 타입

```sql
-- Core enums
CREATE TYPE order_side AS ENUM ('BUY', 'SELL');
CREATE TYPE order_type AS ENUM ('MARKET', 'LIMIT');
CREATE TYPE order_status AS ENUM ('NEW', 'SENT', 'PARTIAL', 'FILLED', 'CANCELED', 'REJECTED', 'ERROR');
CREATE TYPE event_level AS ENUM ('INFO', 'WARN', 'ERROR');
CREATE TYPE param_status AS ENUM ('ACTIVE', 'INACTIVE');

-- AI enums (optional)
CREATE TYPE draft_status AS ENUM ('DRAFT', 'REVIEW', 'APPROVED', 'REJECTED');
CREATE TYPE ai_job_type AS ENUM ('STRATEGY_PARAM_GEN', 'TRADE_JOURNAL');
CREATE TYPE ai_job_status AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED');
```

---

## 2. Core Tables (필수)

```sql
CREATE TABLE strategies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE strategy_params (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    version INTEGER NOT NULL,
    params JSONB NOT NULL,
    status param_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (strategy_id, trade_date, version)
);

CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    broker_order_id TEXT UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    side order_side NOT NULL,
    order_type order_type NOT NULL,
    qty NUMERIC(18, 4) NOT NULL CHECK (qty > 0),
    price NUMERIC(18, 4) CHECK (price IS NULL OR price > 0),
    status order_status NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (order_type <> 'LIMIT' OR price IS NOT NULL)
);

CREATE TABLE fills (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    broker_fill_id TEXT UNIQUE,
    symbol TEXT NOT NULL,
    qty NUMERIC(18, 4) NOT NULL CHECK (qty > 0),
    price NUMERIC(18, 4) NOT NULL CHECK (price > 0),
    filled_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE positions (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    qty NUMERIC(18, 4) NOT NULL,
    avg_price NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    level event_level NOT NULL,
    message TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 3. AI Tables (선택)

AI 배치(전략 생성/매매일지) 기능을 사용한다면 아래 테이블을 추가한다.

```sql
CREATE TABLE strategy_param_drafts (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    version INTEGER NOT NULL,
    params JSONB NOT NULL,
    status draft_status NOT NULL DEFAULT 'DRAFT',
    ai_model TEXT,
    prompt_hash TEXT,
    input_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE trade_journals (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    details TEXT,
    metrics_json JSONB,
    ai_model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_job_runs (
    id BIGSERIAL PRIMARY KEY,
    job_type ai_job_type NOT NULL,
    status ai_job_status NOT NULL DEFAULT 'PENDING',
    model TEXT,
    prompt TEXT,
    response TEXT,
    error TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 4. Indexes

```sql
CREATE INDEX idx_orders_status_symbol ON orders (status, symbol);
CREATE INDEX idx_fills_order_id ON fills (order_id);
CREATE INDEX idx_strategy_params_trade_date_status ON strategy_params (trade_date, status);

-- AI indexes (optional)
CREATE INDEX idx_strategy_param_drafts_trade_date_status ON strategy_param_drafts (trade_date, status);
CREATE INDEX idx_ai_job_runs_type_status ON ai_job_runs (job_type, status);
```

---

## 5. updated_at 자동 갱신 (기본)

`updated_at`은 자동 갱신이 **기본 정책**이다. 아래 트리거를 적용한다.

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Example
CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

적용 시 **모든 테이블**에 동일한 트리거를 추가한다.

적용 대상(기본):
- `strategies`
- `strategy_params`
- `orders`
- `fills`
- `positions`
- `events`
- `strategy_param_drafts`
- `trade_journals`
- `ai_job_runs`
