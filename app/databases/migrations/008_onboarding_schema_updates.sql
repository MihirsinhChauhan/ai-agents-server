-- Migration: 008_onboarding_schema_updates.sql
-- Description: Add onboarding tables and enhance users table for onboarding functionality
-- Referenced from: ONBOARDING_IMPLEMENTATION_PLAN.md

-- =============================================
-- ONBOARDING PROGRESS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_step VARCHAR(50) NOT NULL DEFAULT 'welcome',
    completed_steps JSONB DEFAULT '[]',
    onboarding_data JSONB DEFAULT '{}',
    is_completed BOOLEAN DEFAULT false,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints for onboarding_progress
ALTER TABLE onboarding_progress ADD CONSTRAINT check_onboarding_progress_current_step
    CHECK (current_step IN ('welcome', 'profile_setup', 'debt_collection', 'goal_setting', 'dashboard_intro', 'completed'));

ALTER TABLE onboarding_progress ADD CONSTRAINT check_onboarding_progress_completed_steps
    CHECK (jsonb_typeof(completed_steps) = 'array');

ALTER TABLE onboarding_progress ADD CONSTRAINT check_onboarding_progress_onboarding_data
    CHECK (jsonb_typeof(onboarding_data) = 'object');

-- Create indexes for onboarding_progress
CREATE INDEX IF NOT EXISTS idx_onboarding_progress_user_id ON onboarding_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_progress_step ON onboarding_progress(current_step);
CREATE INDEX IF NOT EXISTS idx_onboarding_progress_completed ON onboarding_progress(is_completed) WHERE is_completed = true;

-- Add comments for onboarding_progress table
COMMENT ON TABLE onboarding_progress IS 'Tracks user progress through the onboarding flow';
COMMENT ON COLUMN onboarding_progress.user_id IS 'Reference to the user completing onboarding';
COMMENT ON COLUMN onboarding_progress.current_step IS 'Current step in the onboarding process';
COMMENT ON COLUMN onboarding_progress.completed_steps IS 'Array of completed onboarding steps';
COMMENT ON COLUMN onboarding_progress.onboarding_data IS 'JSON data collected during onboarding';
COMMENT ON COLUMN onboarding_progress.is_completed IS 'Whether the user has completed onboarding';

-- =============================================
-- USER GOALS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_type VARCHAR(50) NOT NULL,
    target_amount DECIMAL(12,2),
    target_date DATE,
    preferred_strategy VARCHAR(50) DEFAULT 'snowball',
    monthly_extra_payment DECIMAL(10,2),
    priority_level INTEGER DEFAULT 5,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints for user_goals
ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_goal_type
    CHECK (goal_type IN ('debt_freedom', 'reduce_interest', 'specific_amount', 'custom'));

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_preferred_strategy
    CHECK (preferred_strategy IN ('snowball', 'avalanche', 'custom'));

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_priority_level
    CHECK (priority_level >= 1 AND priority_level <= 10);

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_target_amount_positive
    CHECK (target_amount IS NULL OR target_amount > 0);

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_monthly_extra_payment_positive
    CHECK (monthly_extra_payment IS NULL OR monthly_extra_payment > 0);

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_progress_percentage
    CHECK (progress_percentage >= 0.00 AND progress_percentage <= 100.00);

ALTER TABLE user_goals ADD CONSTRAINT check_user_goals_target_date_future
    CHECK (target_date IS NULL OR target_date > CURRENT_DATE);

-- Create indexes for user_goals
CREATE INDEX IF NOT EXISTS idx_user_goals_user_id ON user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_user_goals_active ON user_goals(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_user_goals_type ON user_goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_user_goals_target_date ON user_goals(target_date) WHERE target_date IS NOT NULL;

-- Add comments for user_goals table
COMMENT ON TABLE user_goals IS 'User financial goals for debt management planning';
COMMENT ON COLUMN user_goals.user_id IS 'Reference to the user who set the goal';
COMMENT ON COLUMN user_goals.goal_type IS 'Type of financial goal (debt_freedom, reduce_interest, etc.)';
COMMENT ON COLUMN user_goals.target_amount IS 'Monetary target for the goal';
COMMENT ON COLUMN user_goals.preferred_strategy IS 'Preferred debt repayment strategy';
COMMENT ON COLUMN user_goals.priority_level IS 'Priority level (1-10) for goal importance';

-- =============================================
-- ONBOARDING ANALYTICS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS onboarding_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    step_name VARCHAR(50) NOT NULL,
    time_spent_seconds INTEGER,
    completion_rate DECIMAL(5,2),
    drop_off_point VARCHAR(50),
    user_agent TEXT,
    device_type VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints for onboarding_analytics
ALTER TABLE onboarding_analytics ADD CONSTRAINT check_onboarding_analytics_step_name
    CHECK (step_name IN ('welcome', 'profile_setup', 'debt_collection', 'goal_setting', 'dashboard_intro'));

ALTER TABLE onboarding_analytics ADD CONSTRAINT check_onboarding_analytics_time_spent_positive
    CHECK (time_spent_seconds IS NULL OR time_spent_seconds > 0);

ALTER TABLE onboarding_analytics ADD CONSTRAINT check_onboarding_analytics_completion_rate
    CHECK (completion_rate IS NULL OR (completion_rate >= 0.00 AND completion_rate <= 100.00));

ALTER TABLE onboarding_analytics ADD CONSTRAINT check_onboarding_analytics_device_type
    CHECK (device_type IS NULL OR device_type IN ('desktop', 'mobile', 'tablet'));

-- Create indexes for onboarding_analytics
CREATE INDEX IF NOT EXISTS idx_onboarding_analytics_user_id ON onboarding_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_analytics_step ON onboarding_analytics(step_name);
CREATE INDEX IF NOT EXISTS idx_onboarding_analytics_created_at ON onboarding_analytics(created_at);

-- Add comments for onboarding_analytics table
COMMENT ON TABLE onboarding_analytics IS 'Analytics data for onboarding flow user behavior';
COMMENT ON COLUMN onboarding_analytics.user_id IS 'Reference to the user being analyzed';
COMMENT ON COLUMN onboarding_analytics.step_name IS 'Name of the onboarding step';
COMMENT ON COLUMN onboarding_analytics.time_spent_seconds IS 'Time spent on this step in seconds';
COMMENT ON COLUMN onboarding_analytics.completion_rate IS 'Percentage completion rate for this step';

-- =============================================
-- ENHANCE USERS TABLE
-- =============================================

-- Add new columns to users table for onboarding
ALTER TABLE users ADD COLUMN IF NOT EXISTS income_frequency VARCHAR(20) DEFAULT 'monthly';
ALTER TABLE users ADD COLUMN IF NOT EXISTS employment_status VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS financial_experience VARCHAR(20) DEFAULT 'beginner';
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMP WITH TIME ZONE;

-- Add constraints for new users table columns
ALTER TABLE users ADD CONSTRAINT check_users_income_frequency
    CHECK (income_frequency IN ('weekly', 'biweekly', 'monthly', 'annually'));

ALTER TABLE users ADD CONSTRAINT check_users_employment_status
    CHECK (employment_status IS NULL OR employment_status IN ('employed', 'self_employed', 'unemployed', 'retired', 'student'));

ALTER TABLE users ADD CONSTRAINT check_users_financial_experience
    CHECK (financial_experience IN ('beginner', 'intermediate', 'advanced'));

-- Create indexes for new users table columns
CREATE INDEX IF NOT EXISTS idx_users_onboarding_completed ON users(onboarding_completed) WHERE onboarding_completed = true;
CREATE INDEX IF NOT EXISTS idx_users_employment_status ON users(employment_status);

-- Add comments for new users table columns
COMMENT ON COLUMN users.income_frequency IS 'How often the user receives income (weekly, biweekly, monthly, annually)';
COMMENT ON COLUMN users.employment_status IS 'Current employment status of the user';
COMMENT ON COLUMN users.financial_experience IS 'User self-reported financial experience level';
COMMENT ON COLUMN users.onboarding_completed IS 'Whether the user has completed the onboarding process';
COMMENT ON COLUMN users.onboarding_completed_at IS 'Timestamp when onboarding was completed';

-- =============================================
-- UPDATE EXISTING TABLES WITH ONBOARDING SUPPORT
-- =============================================

-- Add onboarding_completed_at trigger for users table
CREATE OR REPLACE FUNCTION update_onboarding_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.onboarding_completed = true AND OLD.onboarding_completed = false THEN
        NEW.onboarding_completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_onboarding_completed_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_onboarding_completed_at();

-- =============================================
-- CREATE VIEWS FOR ONBOARDING ANALYTICS
-- =============================================

-- Create view for onboarding completion summary
CREATE OR REPLACE VIEW onboarding_completion_summary AS
SELECT
    COUNT(*) as total_users,
    COUNT(CASE WHEN onboarding_completed = true THEN 1 END) as completed_users,
    ROUND(
        COUNT(CASE WHEN onboarding_completed = true THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0) * 100, 2
    ) as completion_rate_percentage,
    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - created_at))/3600) as avg_completion_time_hours
FROM users
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';

-- Add comment for the view
COMMENT ON VIEW onboarding_completion_summary IS 'Summary statistics for onboarding completion rates over the last 30 days';
