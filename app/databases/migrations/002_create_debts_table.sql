-- Migration: 002_create_debts_table.sql
-- Description: Create debts table that matches frontend TypeScript interfaces exactly
-- Referenced from: Backend Implementation Plan - Debts Table (Enhanced)

-- Create debts table
CREATE TABLE IF NOT EXISTS debts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    debt_type VARCHAR(50) NOT NULL,
    principal_amount DECIMAL(10,2) NOT NULL,
    current_balance DECIMAL(10,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    is_variable_rate BOOLEAN DEFAULT false,
    minimum_payment DECIMAL(10,2) NOT NULL,
    due_date DATE,
    lender VARCHAR(255) NOT NULL,
    remaining_term_months INTEGER,
    is_tax_deductible BOOLEAN DEFAULT false,
    payment_frequency VARCHAR(20) DEFAULT 'monthly',
    is_high_priority BOOLEAN DEFAULT false,
    days_past_due INTEGER DEFAULT 0,
    notes TEXT,
    source VARCHAR(50) DEFAULT 'manual',
    blockchain_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints matching backend implementation plan
ALTER TABLE debts ADD CONSTRAINT check_debt_type 
    CHECK (debt_type IN ('credit_card', 'personal_loan', 'home_loan', 'vehicle_loan', 
                        'education_loan', 'business_loan', 'gold_loan', 'overdraft', 'emi', 'other'));

ALTER TABLE debts ADD CONSTRAINT check_payment_frequency 
    CHECK (payment_frequency IN ('weekly', 'biweekly', 'monthly', 'quarterly'));

ALTER TABLE debts ADD CONSTRAINT check_positive_amounts 
    CHECK (principal_amount > 0 AND current_balance >= 0 AND interest_rate >= 0);

ALTER TABLE debts ADD CONSTRAINT check_minimum_payment_positive
    CHECK (minimum_payment > 0);

ALTER TABLE debts ADD CONSTRAINT check_remaining_term_positive
    CHECK (remaining_term_months IS NULL OR remaining_term_months > 0);

ALTER TABLE debts ADD CONSTRAINT check_days_past_due_non_negative
    CHECK (days_past_due >= 0);

-- Create performance indexes as specified in implementation plan
CREATE INDEX IF NOT EXISTS idx_debts_user_id ON debts(user_id);
CREATE INDEX IF NOT EXISTS idx_debts_active ON debts(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_debts_due_date ON debts(due_date);
CREATE INDEX IF NOT EXISTS idx_debts_debt_type ON debts(debt_type);
CREATE INDEX IF NOT EXISTS idx_debts_high_priority ON debts(user_id, is_high_priority) WHERE is_high_priority = true;

-- Add table and column comments
COMMENT ON TABLE debts IS 'User debt records with full frontend compatibility';
COMMENT ON COLUMN debts.id IS 'Unique identifier for each debt record';
COMMENT ON COLUMN debts.user_id IS 'Reference to users table';
COMMENT ON COLUMN debts.name IS 'Human-readable name for the debt';
COMMENT ON COLUMN debts.debt_type IS 'Type of debt - must match frontend enum values';
COMMENT ON COLUMN debts.principal_amount IS 'Original debt amount';
COMMENT ON COLUMN debts.current_balance IS 'Current outstanding balance';
COMMENT ON COLUMN debts.interest_rate IS 'Annual interest rate as percentage';
COMMENT ON COLUMN debts.is_variable_rate IS 'Whether interest rate can change';
COMMENT ON COLUMN debts.minimum_payment IS 'Required minimum monthly payment';
COMMENT ON COLUMN debts.due_date IS 'Next payment due date';
COMMENT ON COLUMN debts.payment_frequency IS 'How often payments are due';
COMMENT ON COLUMN debts.days_past_due IS 'Number of days payment is overdue';
COMMENT ON COLUMN debts.source IS 'How debt was added (manual, plaid, etc.)';
COMMENT ON COLUMN debts.blockchain_id IS 'Optional blockchain record identifier';



