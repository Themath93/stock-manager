-- Migration for SPEC-BACKEND-002: Add missing fields to orders table
-- Required: filled_qty, avg_fill_price

BEGIN;

-- Check if columns already exist before adding
DO $$
BEGIN
    -- Add filled_qty column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = 'filled_qty'
    ) THEN
        ALTER TABLE orders ADD COLUMN filled_qty NUMERIC(18, 4) NOT NULL DEFAULT 0;
    END IF;

    -- Add avg_fill_price column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = 'avg_fill_price'
    ) THEN
        ALTER TABLE orders ADD COLUMN avg_fill_price NUMERIC(18, 4);
    END IF;
END $$;

COMMIT;
