-- Database Schema for SPEC-BACKEND-WORKER-004
-- PostgreSQL 15+ row-level lock support

-- Stock Locks Table (WH-001: Multi-worker coordination)
CREATE TABLE IF NOT EXISTS stock_locks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,  -- Stock symbol (e.g., "005930")
    worker_id VARCHAR(100) NOT NULL,  -- Worker instance ID
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- "ACTIVE" or "EXPIRED"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('ACTIVE', 'EXPIRED')),
    CONSTRAINT valid_expiry CHECK (expires_at > acquired_at)
);

-- Indexes for lock management
CREATE INDEX IF NOT EXISTS idx_stock_locks_symbol ON stock_locks(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_locks_worker_id ON stock_locks(worker_id);
CREATE INDEX IF NOT EXISTS idx_stock_locks_expires_at ON stock_locks(expires_at);
CREATE INDEX IF NOT EXISTS idx_stock_locks_status ON stock_locks(status);

-- Worker Processes Table (WH-002: Worker process tracking)
CREATE TABLE IF NOT EXISTS worker_processes (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) NOT NULL UNIQUE,  -- Unique worker instance ID
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE',  -- WorkerStatus enum value
    current_symbol VARCHAR(20),  -- Currently held stock symbol (if HOLDING)
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL,
    heartbeat_interval INTERVAL NOT NULL DEFAULT '30 seconds',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_worker_status CHECK (status IN ('IDLE', 'SCANNING', 'HOLDING', 'EXITING')),
    CONSTRAINT valid_heartbeat_interval CHECK (heartbeat_interval > INTERVAL '0')
);

-- Indexes for worker monitoring
CREATE INDEX IF NOT EXISTS idx_worker_processes_worker_id ON worker_processes(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_processes_status ON worker_processes(status);
CREATE INDEX IF NOT EXISTS idx_worker_processes_last_heartbeat ON worker_processes(last_heartbeat_at);

-- Daily Summaries Table (WH-004: Daily PnL summary)
CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) NOT NULL,
    summary_date DATE NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    gross_profit DECIMAL(20, 8) NOT NULL DEFAULT 0,  -- Positive values only
    gross_loss DECIMAL(20, 8) NOT NULL DEFAULT 0,  -- Positive values only (absolute value)
    net_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0,
    max_drawdown DECIMAL(20, 8) NOT NULL DEFAULT 0,
    win_rate DECIMAL(5, 4) NOT NULL DEFAULT 0,  -- 0.0000 to 1.0000
    profit_factor DECIMAL(20, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT non_negative_trades CHECK (total_trades >= 0),
    CONSTRAINT non_negative_winning_trades CHECK (winning_trades >= 0),
    CONSTRAINT non_negative_losing_trades CHECK (losing_trades >= 0),
    CONSTRAINT trade_consistency CHECK (
        (winning_trades + losing_trades) <= total_trades
    ),
    CONSTRAINT valid_win_rate CHECK (win_rate >= 0 AND win_rate <= 1),
    CONSTRAINT valid_gross_profit CHECK (gross_profit >= 0),
    CONSTRAINT valid_gross_loss CHECK (gross_loss >= 0),
    CONSTRAINT unique_worker_date UNIQUE (worker_id, summary_date)
);

-- Indexes for summary queries
CREATE INDEX IF NOT EXISTS idx_daily_summaries_worker_id ON daily_summaries(worker_id);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_summary_date ON daily_summaries(summary_date);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_worker_date ON daily_summaries(worker_id, summary_date);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_stock_locks_updated_at
    BEFORE UPDATE ON stock_locks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_worker_processes_updated_at
    BEFORE UPDATE ON worker_processes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_summaries_updated_at
    BEFORE UPDATE ON daily_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
