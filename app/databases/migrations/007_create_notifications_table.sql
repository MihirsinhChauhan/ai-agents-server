-- Migration: 007_create_notifications_table.sql
-- Description: Create notifications table for user messaging
-- Referenced from: Backend Implementation Plan - Notifications Table

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add constraints
ALTER TABLE notifications ADD CONSTRAINT check_notification_type
    CHECK (type IN ('payment_reminder', 'debt_milestone', 'ai_suggestion', 'streak_achievement', 
                   'payment_confirmation', 'debt_payoff', 'system_update', 'security_alert'));

ALTER TABLE notifications ADD CONSTRAINT check_title_not_empty
    CHECK (TRIM(title) != '');

ALTER TABLE notifications ADD CONSTRAINT check_message_not_empty
    CHECK (TRIM(message) != '');

ALTER TABLE notifications ADD CONSTRAINT check_scheduled_for_future_or_null
    CHECK (scheduled_for IS NULL OR scheduled_for >= created_at);

ALTER TABLE notifications ADD CONSTRAINT check_sent_at_after_scheduled
    CHECK (sent_at IS NULL OR scheduled_for IS NULL OR sent_at >= scheduled_for);

-- Create performance indexes as specified in implementation plan
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_user_type ON notifications(user_id, type);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_for ON notifications(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);

-- Create partial indexes for common queries
CREATE INDEX IF NOT EXISTS idx_notifications_unread 
    ON notifications(user_id, created_at DESC) 
    WHERE is_read = false;

CREATE INDEX IF NOT EXISTS idx_notifications_pending 
    ON notifications(scheduled_for) 
    WHERE sent_at IS NULL AND scheduled_for IS NOT NULL;

-- Add table and column comments
COMMENT ON TABLE notifications IS 'User notifications and messaging system';
COMMENT ON COLUMN notifications.id IS 'Unique identifier for each notification';
COMMENT ON COLUMN notifications.user_id IS 'Reference to the user receiving the notification';
COMMENT ON COLUMN notifications.type IS 'Type of notification (payment_reminder, milestone, etc.)';
COMMENT ON COLUMN notifications.title IS 'Short title for the notification';
COMMENT ON COLUMN notifications.message IS 'Full notification message content';
COMMENT ON COLUMN notifications.is_read IS 'Whether user has read this notification';
COMMENT ON COLUMN notifications.scheduled_for IS 'When notification should be sent (NULL for immediate)';
COMMENT ON COLUMN notifications.sent_at IS 'When notification was actually sent';
COMMENT ON COLUMN notifications.metadata IS 'Additional notification data (JSON format)';
