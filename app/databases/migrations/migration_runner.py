"""
Database migration runner for DebtEase application.
Executes SQL migration files in order to set up the database schema.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List
import asyncpg
from app.databases.database import db_manager

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Handles database migrations by executing SQL files in order.
    """
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent
        self.migrations_table = "schema_migrations"
    
    async def create_migrations_table(self, conn: asyncpg.Connection) -> None:
        """
        Create the schema_migrations table to track applied migrations.
        """
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        logger.info("Created schema_migrations table")
    
    async def get_applied_migrations(self, conn: asyncpg.Connection) -> set:
        """
        Get the list of already applied migrations.
        """
        try:
            rows = await conn.fetch(f"""
                SELECT migration_name FROM {self.migrations_table}
                ORDER BY applied_at;
            """)
            return {row['migration_name'] for row in rows}
        except Exception:
            # Table doesn't exist yet
            return set()
    
    def get_migration_files(self) -> List[Path]:
        """
        Get all SQL migration files sorted by filename.
        """
        migration_files = []
        for file_path in self.migrations_dir.glob("*.sql"):
            if file_path.is_file():
                migration_files.append(file_path)
        
        # Sort by filename to ensure proper order
        migration_files.sort(key=lambda x: x.name)
        return migration_files
    
    async def execute_migration(self, conn: asyncpg.Connection, migration_file: Path) -> None:
        """
        Execute a single migration file.
        """
        logger.info(f"Executing migration: {migration_file.name}")
        
        # Read and execute the SQL file
        sql_content = migration_file.read_text(encoding='utf-8')
        
        try:
            # Execute the migration SQL
            await conn.execute(sql_content)
            
            # Record the migration as applied
            await conn.execute(f"""
                INSERT INTO {self.migrations_table} (migration_name)
                VALUES ($1);
            """, migration_file.name)
            
            logger.info(f"Successfully applied migration: {migration_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration_file.name}: {e}")
            raise
    
    async def run_migrations(self) -> None:
        """
        Run all pending migrations.
        """
        logger.info("Starting database migrations")
        
        try:
            async with db_manager.get_connection() as conn:
                # Create migrations tracking table
                await self.create_migrations_table(conn)
                
                # Get applied migrations
                applied_migrations = await self.get_applied_migrations(conn)
                logger.info(f"Found {len(applied_migrations)} previously applied migrations")
                
                # Get all migration files
                migration_files = self.get_migration_files()
                logger.info(f"Found {len(migration_files)} migration files")
                
                # Execute pending migrations
                pending_count = 0
                for migration_file in migration_files:
                    if migration_file.name not in applied_migrations:
                        await self.execute_migration(conn, migration_file)
                        pending_count += 1
                
                if pending_count == 0:
                    logger.info("No pending migrations to apply")
                else:
                    logger.info(f"Successfully applied {pending_count} migrations")
                    
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    async def rollback_migration(self, migration_name: str) -> None:
        """
        Rollback a specific migration (if rollback SQL is available).
        Note: This is a basic implementation - rollback files would need to be created separately.
        """
        logger.warning(f"Rollback requested for {migration_name}")
        logger.warning("Rollback functionality would require separate rollback SQL files")
        raise NotImplementedError("Migration rollback not implemented")


async def run_all_migrations():
    """
    Convenience function to run all database migrations.
    """
    runner = MigrationRunner()
    await runner.run_migrations()


async def init_database_schema():
    """
    Initialize the complete database schema by running all migrations.
    Should be called during application startup.
    """
    logger.info("Initializing database schema")
    
    # Test database connection first
    connection_ok = await db_manager.test_connection()
    if not connection_ok:
        raise RuntimeError("Cannot connect to database")
    
    # Run migrations
    await run_all_migrations()
    
    logger.info("Database schema initialization completed")


if __name__ == "__main__":
    # Allow running migrations directly
    asyncio.run(init_database_schema())



