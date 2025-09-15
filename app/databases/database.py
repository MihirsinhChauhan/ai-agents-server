"""
Database connection and management for DebtEase application.
Implements connection pooling with AsyncPG as specified in the Backend Implementation Plan.
"""

import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from app.configs.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager class for handling PostgreSQL connections with AsyncPG.
    Implements connection pooling for optimal performance.
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build the PostgreSQL connection string from settings."""
        return (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    
    async def create_pool(self) -> None:
        """
        Create the connection pool.
        Uses settings from config for pool size and connection parameters.
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=settings.DB_MIN_SIZE,
                max_size=settings.DB_MAX_SIZE,
                command_timeout=60,
            )
            logger.info(f"Database pool created successfully with {settings.DB_MIN_SIZE}-{settings.DB_MAX_SIZE} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def close_pool(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get a connection from the pool using context manager.
        Automatically handles connection acquisition and release.
        """
        if not self.pool:
            await self.create_pool()
        
        if not self.pool:
            raise RuntimeError("Database pool is not available")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def test_connection(self) -> bool:
        """
        Test database connectivity.
        Returns True if connection is successful, False otherwise.
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test failed: unexpected result")
                    return False
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def execute_query(self, query: str, *args) -> None:
        """
        Execute a query without returning results (e.g., INSERT, UPDATE, DELETE).
        """
        try:
            async with self.get_connection() as conn:
                await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    async def fetch_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Fetch a single record from the database.
        """
        try:
            async with self.get_connection() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            logger.error(f"Failed to fetch record: {e}")
            raise
    
    async def fetch_all(self, query: str, *args) -> list[asyncpg.Record]:
        """
        Fetch all records matching the query.
        """
        try:
            async with self.get_connection() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            logger.error(f"Failed to fetch records: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency function for FastAPI to get database connection.
    """
    async with db_manager.get_connection() as conn:
        yield conn


async def init_database() -> None:
    """
    Initialize the database connection pool.
    Should be called during application startup.
    """
    await db_manager.create_pool()


async def close_database() -> None:
    """
    Close the database connection pool.
    Should be called during application shutdown.
    """
    await db_manager.close_pool()
