"""Add AI insights cache table

Revision ID: add_ai_insights_cache
Revises: [previous_revision]
Create Date: 2025-09-24 01:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_ai_insights_cache'
down_revision = None  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_insights_cache table
    op.create_table(
        'ai_insights_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('debt_analysis', postgresql.JSONB, nullable=False),
        sa.Column('recommendations', postgresql.JSONB, nullable=False),
        sa.Column('ai_metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('cache_key', sa.VARCHAR(255), nullable=False),
        sa.Column('generated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('expires_at', sa.TIMESTAMP, nullable=False),
        sa.Column('version', sa.INTEGER, server_default=sa.text('1')),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'completed'")),
        sa.Column('processing_time', sa.FLOAT, nullable=True),
        sa.Column('ai_model_used', sa.VARCHAR(100), nullable=True),
        sa.Column('error_log', sa.TEXT, nullable=True),
    )

    # Create indexes for performance
    op.create_index('idx_ai_insights_user_id', 'ai_insights_cache', ['user_id'])
    op.create_index('idx_ai_insights_cache_key', 'ai_insights_cache', ['cache_key'])
    op.create_index('idx_ai_insights_expires', 'ai_insights_cache', ['expires_at'])
    op.create_index('idx_ai_insights_status', 'ai_insights_cache', ['status'])
    op.create_index('idx_ai_insights_user_status', 'ai_insights_cache', ['user_id', 'status'])

    # Create ai_processing_queue table for background processing
    op.create_table(
        'ai_processing_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_type', sa.VARCHAR(50), nullable=False, server_default=sa.text("'ai_insights'")),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'queued'")),
        sa.Column('priority', sa.INTEGER, server_default=sa.text('5')),
        sa.Column('attempts', sa.INTEGER, server_default=sa.text('0')),
        sa.Column('max_attempts', sa.INTEGER, server_default=sa.text('3')),
        sa.Column('error_log', sa.TEXT, nullable=True),
        sa.Column('payload', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('started_at', sa.TIMESTAMP, nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP, nullable=True),
    )

    # Create indexes for processing queue
    op.create_index('idx_ai_queue_status', 'ai_processing_queue', ['status'])
    op.create_index('idx_ai_queue_user_id', 'ai_processing_queue', ['user_id'])
    op.create_index('idx_ai_queue_priority', 'ai_processing_queue', ['priority', 'created_at'])
    op.create_index('idx_ai_queue_task_type', 'ai_processing_queue', ['task_type', 'status'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_ai_queue_task_type', 'ai_processing_queue')
    op.drop_index('idx_ai_queue_priority', 'ai_processing_queue')
    op.drop_index('idx_ai_queue_user_id', 'ai_processing_queue')
    op.drop_index('idx_ai_queue_status', 'ai_processing_queue')

    op.drop_index('idx_ai_insights_user_status', 'ai_insights_cache')
    op.drop_index('idx_ai_insights_status', 'ai_insights_cache')
    op.drop_index('idx_ai_insights_expires', 'ai_insights_cache')
    op.drop_index('idx_ai_insights_cache_key', 'ai_insights_cache')
    op.drop_index('idx_ai_insights_user_id', 'ai_insights_cache')

    # Drop tables
    op.drop_table('ai_processing_queue')
    op.drop_table('ai_insights_cache')