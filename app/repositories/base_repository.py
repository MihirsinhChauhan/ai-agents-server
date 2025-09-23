"""
Base repository class providing common CRUD operations and utilities.
All specific repositories inherit from this base class.
"""

import asyncpg
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Generic
from uuid import UUID
from datetime import datetime

from app.databases.database import db_manager

logger = logging.getLogger(__name__)

# Generic type for models
T = TypeVar('T')


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class RecordNotFoundError(DatabaseError):
    """Exception raised when a record is not found"""
    pass


class DuplicateRecordError(DatabaseError):
    """Exception raised when trying to create a duplicate record"""
    pass


class BaseRepository(ABC, Generic[T]):
    """
    Base repository class providing common database operations.
    
    All repositories should inherit from this class and implement
    the abstract methods for their specific table operations.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db_manager = db_manager

    @abstractmethod
    def _record_to_model(self, record: asyncpg.Record) -> T:
        """Convert a database record to a model instance"""
        pass

    @abstractmethod
    def _model_to_dict(self, model: T) -> Dict[str, Any]:
        """Convert a model instance to a dictionary for database operations"""
        pass

    async def _execute_with_error_handling(self, query: str, *args) -> Any:
        """Execute a query with proper error handling"""
        try:
            async with self.db_manager.get_connection() as conn:
                return await conn.execute(query, *args)
        except asyncpg.UniqueViolationError as e:
            logger.error(f"Unique constraint violation: {e}")
            raise DuplicateRecordError(f"Record already exists: {e}")
        except asyncpg.ForeignKeyViolationError as e:
            logger.error(f"Foreign key constraint violation: {e}")
            raise DatabaseError(f"Foreign key constraint violated: {e}")
        except asyncpg.PostgresError as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in query execution: {e}")
            raise DatabaseError(f"Unexpected database error: {e}")

    async def _fetch_one_with_error_handling(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch one record with proper error handling"""
        try:
            async with self.db_manager.get_connection() as conn:
                return await conn.fetchrow(query, *args)
        except asyncpg.PostgresError as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database query failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in query execution: {e}")
            raise DatabaseError(f"Unexpected database error: {e}")

    async def _fetch_all_with_error_handling(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all records with proper error handling"""
        try:
            async with self.db_manager.get_connection() as conn:
                return await conn.fetch(query, *args)
        except asyncpg.PostgresError as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database query failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in query execution: {e}")
            raise DatabaseError(f"Unexpected database error: {e}")

    async def create(self, model: T) -> T:
        """
        Create a new record in the database.
        
        Args:
            model: The model instance to create
            
        Returns:
            The created model with database-generated fields
            
        Raises:
            DuplicateRecordError: If record already exists
            DatabaseError: For other database errors
        """
        model_dict = self._model_to_dict(model)
        
        # Remove None values and prepare for insert
        insert_data = {k: v for k, v in model_dict.items() if v is not None}
        
        # Build dynamic INSERT query
        columns = list(insert_data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(insert_data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                record = await conn.fetchrow(query, *values)
                if record:
                    return self._record_to_model(record)
                else:
                    raise DatabaseError("Failed to create record - no data returned")
        except asyncpg.UniqueViolationError as e:
            logger.error(f"Unique constraint violation: {e}")
            raise DuplicateRecordError(f"Record already exists: {e}")
        except asyncpg.ForeignKeyViolationError as e:
            logger.error(f"Foreign key constraint violation: {e}")
            raise DatabaseError(f"Foreign key constraint violated: {e}")
        except asyncpg.PostgresError as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in create operation: {e}")
            raise DatabaseError(f"Unexpected database error: {e}")

    async def get_by_id(self, record_id: Union[str, UUID]) -> Optional[T]:
        """
        Get a record by its ID.
        
        Args:
            record_id: The ID of the record to retrieve
            
        Returns:
            The model instance if found, None otherwise
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = $1"
        record = await self._fetch_one_with_error_handling(query, str(record_id))
        
        if record:
            return self._record_to_model(record)
        return None

    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all records with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
            
        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def update(self, record_id: Union[str, UUID], updates: Dict[str, Any]) -> Optional[T]:
        """
        Update a record by its ID.
        
        Args:
            record_id: The ID of the record to update
            updates: Dictionary of field names and new values
            
        Returns:
            The updated model instance if found, None otherwise
            
        Raises:
            DatabaseError: For database errors
        """
        if not updates:
            return await self.get_by_id(record_id)
        
        # Remove None values and add updated_at
        update_data = {k: v for k, v in updates.items() if v is not None}
        update_data['updated_at'] = datetime.now()
        
        # Build dynamic UPDATE query
        set_clauses = [f"{column} = ${i+2}" for i, column in enumerate(update_data.keys())]
        values = [str(record_id)] + list(update_data.values())
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """
        
        record = await self._fetch_one_with_error_handling(query, *values)
        
        if record:
            return self._record_to_model(record)
        return None

    async def delete(self, record_id: Union[str, UUID]) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            record_id: The ID of the record to delete
            
        Returns:
            True if record was deleted, False if not found
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"DELETE FROM {self.table_name} WHERE id = $1"
        result = await self._execute_with_error_handling(query, str(record_id))
        
        # Extract the number of affected rows from the result
        if hasattr(result, 'split'):
            # Result format is "DELETE n" where n is the number of rows
            rows_affected = int(result.split()[-1])
            return rows_affected > 0
        return False

    async def soft_delete(self, record_id: Union[str, UUID]) -> Optional[T]:
        """
        Soft delete a record by setting is_active to False.
        
        Args:
            record_id: The ID of the record to soft delete
            
        Returns:
            The updated model instance if found, None otherwise
            
        Raises:
            DatabaseError: For database errors
        """
        return await self.update(record_id, {'is_active': False})

    async def exists(self, record_id: Union[str, UUID]) -> bool:
        """
        Check if a record exists by its ID.
        
        Args:
            record_id: The ID of the record to check
            
        Returns:
            True if record exists, False otherwise
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE id = $1)"
        record = await self._fetch_one_with_error_handling(query, str(record_id))
        return bool(record[0]) if record else False

    async def count(self, where_clause: str = "", *args) -> int:
        """
        Count records in the table with optional WHERE clause.
        
        Args:
            where_clause: Optional WHERE clause (without WHERE keyword)
            *args: Parameters for the WHERE clause
            
        Returns:
            Number of records
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
            
        record = await self._fetch_one_with_error_handling(query, *args)
        return int(record[0]) if record else 0

    async def find_by_field(self, field_name: str, field_value: Any) -> List[T]:
        """
        Find records by a specific field value.
        
        Args:
            field_name: Name of the field to search
            field_value: Value to search for
            
        Returns:
            List of model instances
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT * FROM {self.table_name} WHERE {field_name} = $1 ORDER BY created_at DESC"
        records = await self._fetch_all_with_error_handling(query, field_value)
        return [self._record_to_model(record) for record in records]

    async def find_one_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """
        Find a single record by a specific field value.
        
        Args:
            field_name: Name of the field to search
            field_value: Value to search for
            
        Returns:
            The model instance if found, None otherwise
            
        Raises:
            DatabaseError: For database errors
        """
        query = f"SELECT * FROM {self.table_name} WHERE {field_name} = $1 LIMIT 1"
        record = await self._fetch_one_with_error_handling(query, field_value)
        
        if record:
            return self._record_to_model(record)
        return None

    async def execute_transaction(self, operations: List[tuple]) -> List[Any]:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of tuples (query, *args) to execute
            
        Returns:
            List of results from each operation
            
        Raises:
            DatabaseError: For database errors
        """
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    results = []
                    for query, *args in operations:
                        result = await conn.execute(query, *args)
                        results.append(result)
                    return results
        except asyncpg.PostgresError as e:
            logger.error(f"Transaction failed: {e}")
            raise DatabaseError(f"Transaction failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in transaction: {e}")
            raise DatabaseError(f"Unexpected transaction error: {e}")

    async def execute_raw_query(self, query: str, *args) -> List[asyncpg.Record]:
        """
        Execute a raw SQL query.
        
        Args:
            query: The SQL query to execute
            *args: Parameters for the query
            
        Returns:
            List of database records
            
        Raises:
            DatabaseError: For database errors
        """
        return await self._fetch_all_with_error_handling(query, *args)

    async def get_health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the repository.
        
        Returns:
            Dictionary with health check information
        """
        try:
            count = await self.count()
            async with self.db_manager.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return {
                "table": self.table_name,
                "status": "healthy",
                "record_count": count,
                "connection": "ok"
            }
        except Exception as e:
            return {
                "table": self.table_name,
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }



