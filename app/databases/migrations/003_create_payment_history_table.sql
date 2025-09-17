-- Migration: 003_create_payment_history_table.sql
-- Description: Create payment history table with relationships to Users and Debts
-- Referenced from: Backend Implementation Plan - Payment History Table

-- Create payment_history table
CREATE TABLE IF NOT EXISTS payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debt_id UUID NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    principal_portion DECIMAL(10,2),
    interest_portion DECIMAL(10,2),
    payment_method VARCHAR(50),
    status VARCHAR(20) DEFAULT 'completed',
    notes TEXT,
    blockchain_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints
ALTER TABLE payment_history ADD CONSTRAINT check_payment_amount_positive
    CHECK (amount > 0);

ALTER TABLE payment_history ADD CONSTRAINT check_payment_status
    CHECK (status IN ('completed', 'pending', 'failed', 'cancelled'));

ALTER TABLE payment_history ADD CONSTRAINT check_principal_portion_non_negative
    CHECK (principal_portion IS NULL OR principal_portion >= 0);

ALTER TABLE payment_history ADD CONSTRAINT check_interest_portion_non_negative
    CHECK (interest_portion IS NULL OR interest_portion >= 0);

ALTER TABLE payment_history ADD CONSTRAINT check_portions_sum_not_exceed_amount
    CHECK (
        (principal_portion IS NULL AND interest_portion IS NULL) OR
        (principal_portion IS NULL AND interest_portion <= amount) OR
        (interest_portion IS NULL AND principal_portion <= amount) OR
        (principal_portion + interest_portion <= amount)
    );

ALTER TABLE payment_history ADD CONSTRAINT check_payment_date_not_future
    CHECK (payment_date <= CURRENT_DATE);

-- Create performance indexes as specified in implementation plan
CREATE INDEX IF NOT EXISTS idx_payment_history_debt_id ON payment_history(debt_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_user_date ON payment_history(user_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_payment_history_date ON payment_history(payment_date);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(status);

-- Add table and column comments
COMMENT ON TABLE payment_history IS 'Record of all debt payments made by users';
COMMENT ON COLUMN payment_history.id IS 'Unique identifier for each payment record';
COMMENT ON COLUMN payment_history.debt_id IS 'Reference to the debt this payment applies to';
COMMENT ON COLUMN payment_history.user_id IS 'Reference to the user who made the payment';
COMMENT ON COLUMN payment_history.amount IS 'Total payment amount';
COMMENT ON COLUMN payment_history.payment_date IS 'Date when payment was made';
COMMENT ON COLUMN payment_history.principal_portion IS 'Amount applied to principal balance';
COMMENT ON COLUMN payment_history.interest_portion IS 'Amount applied to interest';
COMMENT ON COLUMN payment_history.payment_method IS 'How payment was made (bank transfer, card, etc.)';
COMMENT ON COLUMN payment_history.status IS 'Payment processing status';
COMMENT ON COLUMN payment_history.blockchain_id IS 'Optional blockchain transaction identifier';
