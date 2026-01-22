-- Initial schema for stock-manager (PostgreSQL)
-- Note: Use application code (or triggers) to manage updated_at changes.

BEGIN;

-- Enums
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_side') THEN
        CREATE TYPE order_side AS ENUM ('BUY', 'SELL');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_type') THEN
        CREATE TYPE order_type AS ENUM ('MARKET', 'LIMIT');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
        CREATE TYPE order_status AS ENUM (
            'NEW', 'SENT', 'PARTIAL', 'FILLED', 'CANCELED', 'REJECTED', 'ERROR'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_level') THEN
        CREATE TYPE event_level AS ENUM ('INFO', 'WARN', 'ERROR');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'param_status') THEN
        CREATE TYPE param_status AS ENUM ('ACTIVE', 'INACTIVE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'draft_status') THEN
        CREATE TYPE draft_status AS ENUM ('DRAFT', 'REVIEW', 'APPROVED', 'REJECTED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_job_type') THEN
        CREATE TYPE ai_job_type AS ENUM ('STRATEGY_PARAM_GEN', 'TRADE_JOURNAL');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_job_status') THEN
        CREATE TYPE ai_job_status AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED');
    END IF;
END $$;

-- Core tables
CREATE TABLE IF NOT EXISTS strategies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategy_params (
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

CREATE TABLE IF NOT EXISTS orders (
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

CREATE TABLE IF NOT EXISTS fills (
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

CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    qty NUMERIC(18, 4) NOT NULL,
    avg_price NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    level event_level NOT NULL,
    message TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AI tables (optional)
CREATE TABLE IF NOT EXISTS strategy_param_drafts (
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

CREATE TABLE IF NOT EXISTS trade_journals (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    details TEXT,
    metrics_json JSONB,
    ai_model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_job_runs (
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_status_symbol ON orders (status, symbol);
CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills (order_id);
CREATE INDEX IF NOT EXISTS idx_strategy_params_trade_date_status ON strategy_params (trade_date, status);
CREATE INDEX IF NOT EXISTS idx_strategy_param_drafts_trade_date_status ON strategy_param_drafts (trade_date, status);
CREATE INDEX IF NOT EXISTS idx_ai_job_runs_type_status ON ai_job_runs (job_type, status);

-- updated_at triggers
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_strategies_updated_at') THEN
        CREATE TRIGGER trg_strategies_updated_at
        BEFORE UPDATE ON strategies
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_strategy_params_updated_at') THEN
        CREATE TRIGGER trg_strategy_params_updated_at
        BEFORE UPDATE ON strategy_params
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_orders_updated_at') THEN
        CREATE TRIGGER trg_orders_updated_at
        BEFORE UPDATE ON orders
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_fills_updated_at') THEN
        CREATE TRIGGER trg_fills_updated_at
        BEFORE UPDATE ON fills
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_positions_updated_at') THEN
        CREATE TRIGGER trg_positions_updated_at
        BEFORE UPDATE ON positions
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_events_updated_at') THEN
        CREATE TRIGGER trg_events_updated_at
        BEFORE UPDATE ON events
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_strategy_param_drafts_updated_at') THEN
        CREATE TRIGGER trg_strategy_param_drafts_updated_at
        BEFORE UPDATE ON strategy_param_drafts
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_trade_journals_updated_at') THEN
        CREATE TRIGGER trg_trade_journals_updated_at
        BEFORE UPDATE ON trade_journals
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_ai_job_runs_updated_at') THEN
        CREATE TRIGGER trg_ai_job_runs_updated_at
        BEFORE UPDATE ON ai_job_runs
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

COMMIT;
