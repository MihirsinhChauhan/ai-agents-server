"""
Database connection and management for DebtEase application.
Implements connection pooling with AsyncPG as specified in the Backend Implementation Plan.
"""

import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
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
        if settings.DATABASE_URL:
            # Use DATABASE_URL if provided (production)
            return settings.DATABASE_URL
        else:
            # Build from individual components (development)
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
            if settings.DATABASE_URL:
                # Use DATABASE_URL for production (Render, Heroku, etc.)
                self.pool = await asyncpg.create_pool(
                    dsn=settings.DATABASE_URL,
                    min_size=settings.DB_MIN_SIZE,
                    max_size=settings.DB_MAX_SIZE,
                    command_timeout=60,
                )
                logger.info(f"Database pool created from DATABASE_URL with {settings.DB_MIN_SIZE}-{settings.DB_MAX_SIZE} connections")
            else:
                # Use individual connection parameters for development
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
                logger.info(f"Database pool created with individual params: {settings.DB_MIN_SIZE}-{settings.DB_MAX_SIZE} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise


# Database management for DebtEase (PostgreSQL with AsyncPG)
# No Supabase dependencies needed
    
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

# SQLAlchemy setup for AI cache service
def get_sqlalchemy_url() -> str:
    """Get SQLAlchemy-compatible database URL"""
    if settings.DATABASE_URL:
        # Convert postgres:// to postgresql+asyncpg://
        url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return url.replace("postgres://", "postgresql+asyncpg://")
    else:
        return (
            f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )

# Create async engine and session maker
async_engine = None
async_session_maker = None

def init_sqlalchemy():
    """Initialize SQLAlchemy engine and session maker"""
    global async_engine, async_session_maker

    if async_engine is None:
        sqlalchemy_url = get_sqlalchemy_url()
        async_engine = create_async_engine(
            sqlalchemy_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,  # Set to True for SQL debugging
        )
        async_session_maker = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("SQLAlchemy engine initialized successfully")

# Declarative base for SQLAlchemy models
Base = declarative_base()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency function for FastAPI to get database connection.
    """
    async with db_manager.get_connection() as conn:
        yield conn


async def init_database() -> None:
    """
    Initialize the database connection pool and SQLAlchemy engine.
    Should be called during application startup.
    """
    await db_manager.create_pool()
    init_sqlalchemy()
    logger.info("✅ Database connection pool and SQLAlchemy engine initialized successfully")


async def close_database() -> None:
    """
    Close the database connection pool and SQLAlchemy engine.
    Should be called during application shutdown.
    """
    global async_engine

    await db_manager.close_pool()

    if async_engine is not None:
        await async_engine.dispose()
        logger.info("SQLAlchemy engine disposed")


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get SQLAlchemy AsyncSession.
    Used for AI cache service and other SQLAlchemy operations.
    """
    if async_session_maker is None:
        init_sqlalchemy()

    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


# Compatibility layer for existing routes expecting SupabaseDB interface
class SupabaseDB:
    """Compatibility wrapper for routes expecting SupabaseDB interface."""

    def __init__(self):
        self.db_manager = db_manager

    async def rpc(self, procedure_name: str, **kwargs):
        """Mock RPC call for compatibility."""
        # This is a placeholder for Supabase RPC calls
        # In a real implementation, this would call stored procedures
        return None

    async def table(self, table_name: str):
        """Mock table access for compatibility."""
        # This is a placeholder for Supabase table access
        return None


# Global SupabaseDB instance for compatibility
supabase_db = SupabaseDB()


async def get_db():
    """Get database connection for dependency injection."""
    async with db_manager.get_connection() as conn:
        yield conn

