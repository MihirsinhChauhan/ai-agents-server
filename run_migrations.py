#!/usr/bin/env python3
"""
Run database migrations for production deployment.
This can be executed as a one-time script in Render.
"""

import asyncio
import logging
import sys
from app.databases.migrations.migration_runner import init_database_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """
    Run all database migrations.
    """
    try:
        logger.info("Starting database migration process...")
        await init_database_schema()
        logger.info("✅ Database migrations completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)