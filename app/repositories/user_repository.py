"""
User repository for authentication and user management operations.
Handles user CRUD operations, authentication, and user-specific queries.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.user import UserInDB, UserCreate, UserUpdate
from app.repositories.base_repository import BaseRepository, RecordNotFoundError, DuplicateRecordError
from uuid import UUID

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[UserInDB]):
    """Repository for user operations"""

    def __init__(self):
        super().__init__("users")

    def _record_to_model(self, record: asyncpg.Record) -> UserInDB:
        """Convert database record to UserInDB model"""
        return UserInDB(
            id=record['id'],
            email=record['email'],
            full_name=record['full_name'],
            monthly_income=record['monthly_income'],
            phone_number=None,  # Not in current schema
            notification_preferences={},  # Not in current schema
            hashed_password=record['password_hash'],
            is_verified=False,  # Not in current schema
            is_active=record['is_active'],
            plaid_access_token=None,  # Not in current schema
            created_at=record['created_at'],
            updated_at=record['updated_at']
        )

    def _model_to_dict(self, model: UserInDB) -> Dict[str, Any]:
        """Convert UserInDB model to dictionary for database operations"""
        return {
            'id': str(model.id),
            'email': model.email,
            'full_name': model.full_name,
            'monthly_income': model.monthly_income,
            'password_hash': model.hashed_password,
            'is_active': model.is_active,
            'created_at': model.created_at,
            'updated_at': model.updated_at
            # Excluding: phone_number, notification_preferences, is_verified, plaid_access_token (not in current schema)
        }

    async def create_user(self, user_create: UserCreate) -> UserInDB:
        """
        Create a new user account.
        
        Args:
            user_create: User creation data
            
        Returns:
            Created user
            
        Raises:
            DuplicateRecordError: If email already exists
            DatabaseError: For other database errors
        """
        # Check if email already exists
        existing_user = await self.get_by_email(user_create.email)
        if existing_user:
            raise DuplicateRecordError(f"User with email {user_create.email} already exists")

        user_in_db = UserInDB(
            email=user_create.email,
            full_name=user_create.full_name,
            monthly_income=user_create.monthly_income,
            phone_number=user_create.phone_number,
            notification_preferences=user_create.notification_preferences,
            hashed_password=user_create.hashed_password,
            is_verified=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return await self.create(user_in_db)

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User if found, None otherwise
        """
        return await self.find_one_by_field('email', email)

    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> Optional[UserInDB]:
        """
        Update user information.
        
        Args:
            user_id: User's ID
            user_update: Update data
            
        Returns:
            Updated user if found, None otherwise
        """
        update_data = user_update.model_dump(exclude_unset=True)
        return await self.update(user_id, update_data)

    async def verify_user(self, user_id: UUID) -> Optional[UserInDB]:
        """
        Mark user as verified.
        
        Args:
            user_id: User's ID
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'is_verified': True})

    async def deactivate_user(self, user_id: UUID) -> Optional[UserInDB]:
        """
        Deactivate user account (soft delete).
        
        Args:
            user_id: User's ID
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'is_active': False})

    async def activate_user(self, user_id: UUID) -> Optional[UserInDB]:
        """
        Reactivate user account.
        
        Args:
            user_id: User's ID
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'is_active': True})

    async def update_password_hash(self, user_id: UUID, new_password_hash: str) -> Optional[UserInDB]:
        """
        Update user's password hash.
        
        Args:
            user_id: User's ID
            new_password_hash: New hashed password
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'password_hash': new_password_hash})

    async def set_plaid_access_token(self, user_id: UUID, access_token: str) -> Optional[UserInDB]:
        """
        Set Plaid access token for user.
        
        Args:
            user_id: User's ID
            access_token: Plaid access token
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'plaid_access_token': access_token})

    async def get_active_users(self, limit: Optional[int] = None, offset: int = 0) -> List[UserInDB]:
        """
        Get all active users.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of active users
        """
        query = """
            SELECT * FROM users 
            WHERE is_active = true 
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
            
        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def get_verified_users(self, limit: Optional[int] = None, offset: int = 0) -> List[UserInDB]:
        """
        Get all verified users.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of verified users
        """
        query = """
            SELECT * FROM users 
            WHERE is_verified = true AND is_active = true 
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
            
        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def get_users_with_plaid(self) -> List[UserInDB]:
        """
        Get users who have Plaid integration enabled.
        
        Returns:
            List of users with Plaid access tokens
        """
        query = """
            SELECT * FROM users 
            WHERE plaid_access_token IS NOT NULL 
            AND is_active = true 
            ORDER BY created_at DESC
        """
        
        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def search_users(self, search_term: str, limit: Optional[int] = None) -> List[UserInDB]:
        """
        Search users by name or email.
        
        Args:
            search_term: Term to search for
            limit: Maximum number of results
            
        Returns:
            List of matching users
        """
        query = """
            SELECT * FROM users 
            WHERE (full_name ILIKE $1 OR email ILIKE $1)
            AND is_active = true
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        search_pattern = f"%{search_term}%"
        records = await self._fetch_all_with_error_handling(query, search_pattern)
        return [self._record_to_model(record) for record in records]

    async def get_user_stats(self) -> Dict[str, int]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_active = true) as active_users,
                COUNT(*) FILTER (WHERE is_verified = true) as verified_users,
                COUNT(*) FILTER (WHERE plaid_access_token IS NOT NULL) as plaid_users,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as recent_users
            FROM users
        """
        
        record = await self._fetch_one_with_error_handling(stats_query)
        
        if record:
            return {
                'total_users': record['total_users'],
                'active_users': record['active_users'],
                'verified_users': record['verified_users'],
                'plaid_users': record['plaid_users'],
                'recent_users': record['recent_users']
            }
        
        return {
            'total_users': 0,
            'active_users': 0,
            'verified_users': 0,
            'plaid_users': 0,
            'recent_users': 0
        }

    async def update_notification_preferences(
        self, 
        user_id: UUID, 
        preferences: Dict[str, bool]
    ) -> Optional[UserInDB]:
        """
        Update user's notification preferences.
        
        Args:
            user_id: User's ID
            preferences: New notification preferences
            
        Returns:
            Updated user if found, None otherwise
        """
        return await self.update(user_id, {'notification_preferences': preferences})

    async def get_users_for_notifications(self, notification_type: str) -> List[UserInDB]:
        """
        Get users who have enabled a specific notification type.
        
        Args:
            notification_type: Type of notification (email, sms, etc.)
            
        Returns:
            List of users with the notification type enabled
        """
        query = """
            SELECT * FROM users 
            WHERE is_active = true 
            AND is_verified = true
            AND notification_preferences ->> $1 = 'true'
            ORDER BY created_at DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, notification_type)
        return [self._record_to_model(record) for record in records]

    async def delete_user_permanently(self, user_id: UUID) -> bool:
        """
        Permanently delete a user and all related data.
        WARNING: This is irreversible!
        
        Args:
            user_id: User's ID
            
        Returns:
            True if user was deleted, False if not found
        """
        # This should cascade delete all related records due to foreign key constraints
        return await self.delete(user_id)

    async def get_user_with_debt_summary(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get user with basic debt summary information.
        
        Args:
            user_id: User's ID
            
        Returns:
            User data with debt summary if found, None otherwise
        """
        query = """
            SELECT 
                u.*,
                COALESCE(COUNT(d.id), 0) as debt_count,
                COALESCE(SUM(d.current_balance), 0) as total_debt,
                COALESCE(SUM(d.minimum_payment), 0) as total_minimum_payments
            FROM users u
            LEFT JOIN debts d ON u.id = d.user_id AND d.is_active = true
            WHERE u.id = $1 AND u.is_active = true
            GROUP BY u.id
        """
        
        record = await self._fetch_one_with_error_handling(query, str(user_id))
        
        if record:
            user = self._record_to_model(record)
            return {
                'user': user,
                'debt_summary': {
                    'debt_count': record['debt_count'],
                    'total_debt': float(record['total_debt']),
                    'total_minimum_payments': float(record['total_minimum_payments'])
                }
            }
        
        return None



