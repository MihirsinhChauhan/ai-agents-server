-- Migration: 004_create_ai_recommendations_table.sql
-- Description: Create AI recommendations table for storing ML insights
-- Referenced from: Backend Implementation Plan - AI Recommendations Table

-- Create ai_recommendations table
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recommendation_type VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    potential_savings DECIMAL(10,2),
    priority_score INTEGER DEFAULT 0,
    is_dismissed BOOLEAN DEFAULT false,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints
ALTER TABLE ai_recommendations ADD CONSTRAINT check_recommendation_type
    CHECK (recommendation_type IN ('snowball', 'avalanche', 'refinance', 'consolidation', 'automation', 'emergency_fund', 'custom'));

ALTER TABLE ai_recommendations ADD CONSTRAINT check_priority_score_range
    CHECK (priority_score >= 0 AND priority_score <= 10);

ALTER TABLE ai_recommendations ADD CONSTRAINT check_potential_savings_non_negative
    CHECK (potential_savings IS NULL OR potential_savings >= 0);

ALTER TABLE ai_recommendations ADD CONSTRAINT check_title_not_empty
    CHECK (TRIM(title) != '');

ALTER TABLE ai_recommendations ADD CONSTRAINT check_description_not_empty
    CHECK (TRIM(description) != '');

-- Create performance indexes as specified in implementation plan
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_user_active ON ai_recommendations(user_id, is_dismissed);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_user_type ON ai_recommendations(user_id, recommendation_type);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_priority ON ai_recommendations(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_created_at ON ai_recommendations(created_at);

-- Create a partial index for active recommendations
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_active 
    ON ai_recommendations(user_id, priority_score DESC) 
    WHERE is_dismissed = false;

-- Add table and column comments
COMMENT ON TABLE ai_recommendations IS 'AI-generated recommendations for debt optimization';
COMMENT ON COLUMN ai_recommendations.id IS 'Unique identifier for each recommendation';
COMMENT ON COLUMN ai_recommendations.user_id IS 'Reference to the user this recommendation is for';
COMMENT ON COLUMN ai_recommendations.recommendation_type IS 'Type of recommendation (snowball, avalanche, etc.)';
COMMENT ON COLUMN ai_recommendations.title IS 'Short title for the recommendation';
COMMENT ON COLUMN ai_recommendations.description IS 'Detailed description of the recommendation';
COMMENT ON COLUMN ai_recommendations.potential_savings IS 'Estimated savings if recommendation is followed';
COMMENT ON COLUMN ai_recommendations.priority_score IS 'AI-calculated priority score (0-10)';
COMMENT ON COLUMN ai_recommendations.is_dismissed IS 'Whether user has dismissed this recommendation';
COMMENT ON COLUMN ai_recommendations.metadata IS 'Additional data for the recommendation (JSON format)';



