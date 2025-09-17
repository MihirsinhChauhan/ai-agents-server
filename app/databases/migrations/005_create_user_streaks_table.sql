-- Migration: 005_create_user_streaks_table.sql
-- Description: Create user streaks table for gamification features
-- Referenced from: Backend Implementation Plan - User Streaks Table

-- Create user_streaks table
CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_check_in TIMESTAMP WITH TIME ZONE,
    total_payments_logged INTEGER DEFAULT 0,
    milestones_achieved JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints
ALTER TABLE user_streaks ADD CONSTRAINT check_current_streak_non_negative
    CHECK (current_streak >= 0);

ALTER TABLE user_streaks ADD CONSTRAINT check_longest_streak_non_negative
    CHECK (longest_streak >= 0);

ALTER TABLE user_streaks ADD CONSTRAINT check_total_payments_non_negative
    CHECK (total_payments_logged >= 0);

ALTER TABLE user_streaks ADD CONSTRAINT check_longest_streak_gte_current
    CHECK (longest_streak >= current_streak);

ALTER TABLE user_streaks ADD CONSTRAINT check_milestones_is_array
    CHECK (jsonb_typeof(milestones_achieved) = 'array');

-- Ensure one record per user
ALTER TABLE user_streaks ADD CONSTRAINT unique_user_streak
    UNIQUE (user_id);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_user_streaks_user_id ON user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_streaks_current_streak ON user_streaks(current_streak DESC);
CREATE INDEX IF NOT EXISTS idx_user_streaks_longest_streak ON user_streaks(longest_streak DESC);
CREATE INDEX IF NOT EXISTS idx_user_streaks_last_check_in ON user_streaks(last_check_in);

-- Add table and column comments
COMMENT ON TABLE user_streaks IS 'User engagement streaks and gamification milestones';
COMMENT ON COLUMN user_streaks.id IS 'Unique identifier for each streak record';
COMMENT ON COLUMN user_streaks.user_id IS 'Reference to the user - one record per user';
COMMENT ON COLUMN user_streaks.current_streak IS 'Current consecutive days of payment logging';
COMMENT ON COLUMN user_streaks.longest_streak IS 'Longest streak ever achieved by user';
COMMENT ON COLUMN user_streaks.last_check_in IS 'Timestamp of last payment log activity';
COMMENT ON COLUMN user_streaks.total_payments_logged IS 'Total number of payments logged by user';
COMMENT ON COLUMN user_streaks.milestones_achieved IS 'Array of milestone identifiers achieved';
