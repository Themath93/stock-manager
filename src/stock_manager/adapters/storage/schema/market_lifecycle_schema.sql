-- Market Lifecycle Schema
-- SPEC-BACKEND-INFRA-003: Market Lifecycle
--
-- Tables:
--   - system_states: System state tracking
--   - daily_settlements: Daily settlement records

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- System States Table
-- ============================================

CREATE TABLE IF NOT EXISTS system_states (
    id SERIAL PRIMARY KEY,
    state VARCHAR(50) NOT NULL CHECK (state IN (
        'OFFLINE',
        'INITIALIZING',
        'READY',
        'TRADING',
        'CLOSING',
        'CLOSED',
        'STOPPED'
    )),
    market_open_at TIMESTAMP,
    market_closed_at TIMESTAMP,
    last_recovery_at TIMESTAMP,
    recovery_status VARCHAR(50) DEFAULT 'SUCCESS' CHECK (recovery_status IN (
        'SUCCESS',
        'FAILED',
        'PARTIAL'
    )),
    recovery_details JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for system_states
CREATE INDEX IF NOT EXISTS idx_system_states_state ON system_states(state);
CREATE INDEX IF NOT EXISTS idx_system_states_created_at ON system_states(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_states_recovery_status ON system_states(recovery_status);

-- Comment
COMMENT ON TABLE system_states IS 'System state tracking for market lifecycle (SPEC-BACKEND-INFRA-003)';
COMMENT ON COLUMN system_states.state IS 'Current system state (UB-001: State Machine)';
COMMENT ON COLUMN system_states.market_open_at IS 'Market open timestamp';
COMMENT ON COLUMN system_states.market_closed_at IS 'Market close timestamp';
COMMENT ON COLUMN system_states.last_recovery_at IS 'Last state recovery timestamp';
COMMENT ON COLUMN system_states.recovery_status IS 'Recovery operation status';
COMMENT ON COLUMN system_states.recovery_details IS 'Recovery operation details (JSON)';

-- ============================================
-- Daily Settlements Table
-- ============================================

CREATE TABLE IF NOT EXISTS daily_settlements (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    realized_pnl DECIMAL(20, 2) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(20, 2) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(20, 2) NOT NULL DEFAULT 0,
    positions_snapshot JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Indexes for daily_settlements
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_settlements_trade_date ON daily_settlements(trade_date);
CREATE INDEX IF NOT EXISTS idx_daily_settlements_created_at ON daily_settlements(created_at DESC);

-- Comment
COMMENT ON TABLE daily_settlements IS 'Daily settlement records (WT-004: Market Close Settlement)';
COMMENT ON COLUMN daily_settlements.trade_date IS 'Trade date for settlement';
COMMENT ON COLUMN daily_settlements.realized_pnl IS 'Realized PnL (closed positions)';
COMMENT ON COLUMN daily_settlements.unrealized_pnl IS 'Unrealized PnL (open positions)';
COMMENT ON COLUMN daily_settlements.total_pnl IS 'Total PnL (realized + unrealized)';
COMMENT ON COLUMN daily_settlements.positions_snapshot IS 'Position snapshots at close time (JSON)';

-- ============================================
-- Update Timestamp Trigger Function
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Triggers
-- ============================================

-- Trigger for system_states
CREATE TRIGGER update_system_states_updated_at
    BEFORE UPDATE ON system_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for daily_settlements
CREATE TRIGGER update_daily_settlements_updated_at
    BEFORE UPDATE ON daily_settlements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Sample Data (Optional)
-- ============================================

-- Insert initial system state (OFFLINE)
INSERT INTO system_states (state, recovery_status)
VALUES ('OFFLINE', 'SUCCESS')
ON CONFLICT DO NOTHING;
