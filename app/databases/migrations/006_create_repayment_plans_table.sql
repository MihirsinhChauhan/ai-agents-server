-- Migration: 006_create_repayment_plans_table.sql
-- Description: Create repayment plans table for optimization strategies
-- Referenced from: Backend Implementation Plan - Repayment Plans Table (Enhanced)

-- Create repayment_plans table
CREATE TABLE IF NOT EXISTS repayment_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy VARCHAR(50) NOT NULL,
    monthly_payment_amount DECIMAL(10,2) NOT NULL,
    total_interest_saved DECIMAL(10,2),
    expected_completion_date DATE,
    debt_order JSONB,
    payment_schedule JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints
ALTER TABLE repayment_plans ADD CONSTRAINT check_strategy_type
    CHECK (strategy IN ('avalanche', 'snowball', 'custom', 'ai_optimized', 'hybrid'));

ALTER TABLE repayment_plans ADD CONSTRAINT check_monthly_payment_positive
    CHECK (monthly_payment_amount > 0);

ALTER TABLE repayment_plans ADD CONSTRAINT check_interest_saved_non_negative
    CHECK (total_interest_saved IS NULL OR total_interest_saved >= 0);

ALTER TABLE repayment_plans ADD CONSTRAINT check_completion_date_future
    CHECK (expected_completion_date IS NULL OR expected_completion_date > CURRENT_DATE);

ALTER TABLE repayment_plans ADD CONSTRAINT check_debt_order_is_array
    CHECK (debt_order IS NULL OR jsonb_typeof(debt_order) = 'array');

ALTER TABLE repayment_plans ADD CONSTRAINT check_payment_schedule_is_array
    CHECK (payment_schedule IS NULL OR jsonb_typeof(payment_schedule) = 'array');

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_repayment_plans_user_id ON repayment_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_repayment_plans_user_active ON repayment_plans(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_repayment_plans_strategy ON repayment_plans(strategy);
CREATE INDEX IF NOT EXISTS idx_repayment_plans_completion_date ON repayment_plans(expected_completion_date);

-- Create a partial index for active plans
CREATE INDEX IF NOT EXISTS idx_repayment_plans_active 
    ON repayment_plans(user_id, created_at DESC) 
    WHERE is_active = true;

-- Add table and column comments
COMMENT ON TABLE repayment_plans IS 'AI-generated debt repayment optimization plans';
COMMENT ON COLUMN repayment_plans.id IS 'Unique identifier for each repayment plan';
COMMENT ON COLUMN repayment_plans.user_id IS 'Reference to the user this plan is for';
COMMENT ON COLUMN repayment_plans.strategy IS 'Type of repayment strategy (avalanche, snowball, etc.)';
COMMENT ON COLUMN repayment_plans.monthly_payment_amount IS 'Total monthly payment amount across all debts';
COMMENT ON COLUMN repayment_plans.total_interest_saved IS 'Estimated total interest savings vs minimum payments';
COMMENT ON COLUMN repayment_plans.expected_completion_date IS 'Projected date when all debts will be paid off';
COMMENT ON COLUMN repayment_plans.debt_order IS 'Array of debt IDs in priority order for payment';
COMMENT ON COLUMN repayment_plans.payment_schedule IS 'Detailed monthly payment schedule (JSON array)';
COMMENT ON COLUMN repayment_plans.is_active IS 'Whether this plan is currently active for the user';



