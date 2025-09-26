"""
Database connection and management for DebtEase application.
Implements connection pooling with AsyncPG as specified in the Backend Implementation Plan.
Also provides SQLAlchemy async session support for AI cache services.
"""

import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, async_sessionmaker
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
        self._sqlalchemy_connection_string = self._build_sqlalchemy_connection_string()
        self.sqlalchemy_engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None

    def _build_connection_string(self) -> str:
        """Build the PostgreSQL connection string from settings."""
        if settings.DATABASE_URL:
            return settings.DATABASE_URL
        return (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )

    def _build_sqlalchemy_connection_string(self) -> str:
        """Build the async PostgreSQL connection string for SQLAlchemy."""
        if settings.DATABASE_URL:
            # Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy
            db_url = settings.DATABASE_URL
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return db_url
        return (
            f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    
    async def create_pool(self) -> None:
        """
        Create the connection pool.
        Uses DATABASE_URL if available (production), otherwise individual settings (development).
        """
        try:
            if settings.DATABASE_URL:
                # Use DATABASE_URL for production (Render provides this)
                self.pool = await asyncpg.create_pool(
                    dsn=settings.DATABASE_URL,
                    min_size=settings.DB_MIN_SIZE,
                    max_size=settings.DB_MAX_SIZE,
                    command_timeout=60,
                )
                logger.info(f"Database pool created successfully using DATABASE_URL with {settings.DB_MIN_SIZE}-{settings.DB_MAX_SIZE} connections")
            else:
                # Use individual settings for development
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
                logger.info(f"Database pool created successfully with individual settings {settings.DB_MIN_SIZE}-{settings.DB_MAX_SIZE} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def create_sqlalchemy_engine(self) -> None:
        """
        Create SQLAlchemy async engine and session factory for AI cache services.
        """
        try:
            logger.info(f"Creating SQLAlchemy engine with connection string: {self._sqlalchemy_connection_string}")
            self.sqlalchemy_engine = create_async_engine(
                self._sqlalchemy_connection_string,
                pool_size=settings.DB_MAX_SIZE // 2,  # Use half the pool size for SQLAlchemy
                max_overflow=settings.DB_MAX_SIZE // 4,
                pool_timeout=30,
                echo=False,  # Set to True for SQL debugging
            )

            self.session_factory = async_sessionmaker(
                bind=self.sqlalchemy_engine,
                class_=AsyncSession,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )

            # Import SQLAlchemy models to register them with the metadata
            # This ensures relationships are properly configured
            from app.models.user_sqlalchemy import User
            from app.models.ai_insights_cache import AIInsightsCache, AIProcessingQueue
            from app.models.base import Base

            # Create all tables if they don't exist
            async with self.sqlalchemy_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("SQLAlchemy tables created successfully")

            logger.info("SQLAlchemy async engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create SQLAlchemy engine: {e}")
            raise


# Database management for DebtEase (PostgreSQL with AsyncPG)
# No Supabase dependencies needed
    
    async def close_pool(self) -> None:
        """Close the connection pools."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

        if self.sqlalchemy_engine:
            await self.sqlalchemy_engine.dispose()
            logger.info("SQLAlchemy engine closed")
    
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

    @asynccontextmanager
    async def get_sqlalchemy_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an SQLAlchemy async session using context manager.
        Automatically handles session lifecycle and rollback on error.
        """
        if not self.session_factory:
            await self.create_sqlalchemy_engine()

        if not self.session_factory:
            raise RuntimeError("SQLAlchemy session factory is not available")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
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
    Initialize the database connection pools.
    Should be called during application startup.
    """
    await db_manager.create_pool()
    await db_manager.create_sqlalchemy_engine()


async def close_database() -> None:
    """
    Close the database connection pool.
    Should be called during application shutdown.
    """
    await db_manager.close_pool()


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


async def get_sqlalchemy_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get SQLAlchemy session.
    Use this for services that need SQLAlchemy ORM functionality (like AI cache service).
    """
    async with db_manager.get_sqlalchemy_session() as session:
        yield session

