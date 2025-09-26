#!/usr/bin/env python3
"""
Test script to verify database session management coexistence.

Tests both AsyncPG and SQLAlchemy async sessions to ensure they work together
without conflicts.
"""

import asyncio
import logging
import sys
import os

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from server.app.databases.database import db_manager, init_database, close_database
from server.app.configs.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_asyncpg_connection():
    """Test AsyncPG connection functionality."""
    logger.info("Testing AsyncPG connection...")
    try:
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info(f"AsyncPG test query result: {result}")
            assert result == 1, "AsyncPG connection test failed"
            logger.info("✅ AsyncPG connection test passed")
            return True
    except Exception as e:
        logger.error(f"❌ AsyncPG connection test failed: {e}")
        return False


async def test_sqlalchemy_session():
    """Test SQLAlchemy async session functionality."""
    logger.info("Testing SQLAlchemy async session...")
    try:
        async with db_manager.get_sqlalchemy_session() as session:
            # Test basic query
            result = await session.execute("SELECT 1 as test_value")
            row = result.fetchone()
            test_value = row[0] if row else None

            logger.info(f"SQLAlchemy test query result: {test_value}")
            assert test_value == 1, "SQLAlchemy session test failed"
            logger.info("✅ SQLAlchemy session test passed")
            return True
    except Exception as e:
        logger.error(f"❌ SQLAlchemy session test failed: {e}")
        return False


async def test_concurrent_access():
    """Test concurrent access with both connection types."""
    logger.info("Testing concurrent access...")

    async def asyncpg_task():
        async with db_manager.get_connection() as conn:
            await asyncio.sleep(0.1)  # Simulate some work
            result = await conn.fetchval("SELECT 'asyncpg_task' as source")
            logger.info(f"AsyncPG concurrent task result: {result}")
            return result == 'asyncpg_task'

    async def sqlalchemy_task():
        async with db_manager.get_sqlalchemy_session() as session:
            await asyncio.sleep(0.1)  # Simulate some work
            result = await session.execute("SELECT 'sqlalchemy_task' as source")
            row = result.fetchone()
            source = row[0] if row else None
            logger.info(f"SQLAlchemy concurrent task result: {source}")
            return source == 'sqlalchemy_task'

    try:
        # Run both tasks concurrently
        asyncpg_success, sqlalchemy_success = await asyncio.gather(
            asyncpg_task(),
            sqlalchemy_task()
        )

        if asyncpg_success and sqlalchemy_success:
            logger.info("✅ Concurrent access test passed")
            return True
        else:
            logger.error("❌ Concurrent access test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Concurrent access test failed: {e}")
        return False


async def test_database_information():
    """Get database information from both connection types."""
    logger.info("Testing database information retrieval...")

    try:
        # Test with AsyncPG
        async with db_manager.get_connection() as conn:
            asyncpg_version = await conn.fetchval("SELECT version()")
            logger.info(f"Database version (AsyncPG): {asyncpg_version[:50]}...")

        # Test with SQLAlchemy
        async with db_manager.get_sqlalchemy_session() as session:
            result = await session.execute("SELECT version()")
            row = result.fetchone()
            sqlalchemy_version = row[0] if row else None
            logger.info(f"Database version (SQLAlchemy): {sqlalchemy_version[:50]}...")

        # They should be the same since it's the same database
        if asyncpg_version == sqlalchemy_version:
            logger.info("✅ Database information test passed")
            return True
        else:
            logger.error("❌ Database information mismatch")
            return False

    except Exception as e:
        logger.error(f"❌ Database information test failed: {e}")
        return False


async def main():
    """Run all database session tests."""
    logger.info("🔧 Starting database session coexistence tests...")
    logger.info(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    try:
        # Initialize database connections
        logger.info("Initializing database connections...")
        await init_database()

        # Run tests
        tests = [
            ("AsyncPG Connection", test_asyncpg_connection),
            ("SQLAlchemy Session", test_sqlalchemy_session),
            ("Concurrent Access", test_concurrent_access),
            ("Database Information", test_database_information),
        ]

        results = []
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} Test ---")
            success = await test_func()
            results.append((test_name, success))

        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        passed = 0
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
            if success:
                passed += 1

        total_tests = len(results)
        logger.info(f"\nTests passed: {passed}/{total_tests}")

        if passed == total_tests:
            logger.info("🎉 All database session tests passed!")
            return True
        else:
            logger.error(f"💥 {total_tests - passed} test(s) failed!")
            return False

    except Exception as e:
        logger.error(f"💥 Test suite failed with error: {e}")
        return False

    finally:
        # Clean up
        logger.info("Cleaning up database connections...")
        await close_database()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)