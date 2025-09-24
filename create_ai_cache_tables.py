#!/usr/bin/env python3
"""
Create AI Insights cache tables manually
"""

import asyncio
import asyncpg
from app.configs.config import settings

async def create_tables():
    """Create AI insights cache tables"""
    database_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    conn = await asyncpg.connect(database_url)

    try:
        # Create ai_insights_cache table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_insights_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                debt_analysis JSONB NOT NULL,
                recommendations JSONB NOT NULL,
                ai_metadata JSONB DEFAULT '{}'::jsonb,
                cache_key VARCHAR(255) NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                version INTEGER DEFAULT 1,
                status VARCHAR(20) DEFAULT 'completed',
                processing_time FLOAT,
                ai_model_used VARCHAR(100),
                error_log TEXT
            );
        """)

        # Create indexes for performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_user_id ON ai_insights_cache(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_cache_key ON ai_insights_cache(cache_key);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_expires ON ai_insights_cache(expires_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_status ON ai_insights_cache(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_user_status ON ai_insights_cache(user_id, status);")

        # Create ai_processing_queue table for background processing
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_processing_queue (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                task_type VARCHAR(50) NOT NULL DEFAULT 'ai_insights',
                status VARCHAR(20) DEFAULT 'queued',
                priority INTEGER DEFAULT 5,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                error_log TEXT,
                payload JSONB DEFAULT '{}'::jsonb,
                result JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)

        # Create indexes for processing queue
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_queue_status ON ai_processing_queue(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_queue_user_id ON ai_processing_queue(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_queue_priority ON ai_processing_queue(priority, created_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_queue_task_type ON ai_processing_queue(task_type, status);")

        print("✅ AI insights cache tables created successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())