"""
Authentication utilities for session-based authentication.
Provides password hashing, session management, and authentication helpers.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from fastapi import HTTPException, status
import uuid

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session storage (in production, use Redis or database)
# For simplicity, using in-memory storage with cleanup
_sessions: Dict[str, Dict[str, Any]] = {}
_session_cleanup_interval = timedelta(minutes=30)
_last_cleanup = datetime.now()


class AuthUtils:
    """Authentication utility class for password and session management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_session_token() -> str:
        """
        Generate a secure session token.
        
        Returns:
            32-character hex session token
        """
        return secrets.token_hex(32)
    
    @staticmethod
    def create_session(user_id: str, user_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User's unique identifier
            user_data: Optional user data to store in session
            
        Returns:
            Session token string
        """
        session_token = AuthUtils.generate_session_token()
        expires_at = datetime.now() + timedelta(hours=24)  # 24 hour sessions
        
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'last_accessed': datetime.now(),
            'user_data': user_data or {}
        }
        
        _sessions[session_token] = session_data
        AuthUtils._cleanup_expired_sessions()
        
        return session_token
    
    @staticmethod
    def get_session(session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by token.
        
        Args:
            session_token: Session token to look up
            
        Returns:
            Session data if valid, None if expired or not found
        """
        if not session_token or session_token not in _sessions:
            return None
        
        session_data = _sessions[session_token]
        
        # Check if session is expired
        if datetime.now() > session_data['expires_at']:
            del _sessions[session_token]
            return None
        
        # Update last accessed time
        session_data['last_accessed'] = datetime.now()
        return session_data
    
    @staticmethod
    def update_session(session_token: str, user_data: Dict[str, Any]) -> bool:
        """
        Update session with new user data.
        
        Args:
            session_token: Session token to update
            user_data: New user data to store
            
        Returns:
            True if updated successfully, False if session not found
        """
        session_data = AuthUtils.get_session(session_token)
        if not session_data:
            return False
        
        session_data['user_data'].update(user_data)
        session_data['last_accessed'] = datetime.now()
        return True
    
    @staticmethod
    def extend_session(session_token: str, hours: int = 24) -> bool:
        """
        Extend session expiration time.
        
        Args:
            session_token: Session token to extend
            hours: Number of hours to extend (default: 24)
            
        Returns:
            True if extended successfully, False if session not found
        """
        session_data = AuthUtils.get_session(session_token)
        if not session_data:
            return False
        
        session_data['expires_at'] = datetime.now() + timedelta(hours=hours)
        session_data['last_accessed'] = datetime.now()
        return True
    
    @staticmethod
    def delete_session(session_token: str) -> bool:
        """
        Delete a session (logout).
        
        Args:
            session_token: Session token to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        if session_token in _sessions:
            del _sessions[session_token]
            return True
        return False
    
    @staticmethod
    def delete_user_sessions(user_id: str) -> int:
        """
        Delete all sessions for a specific user.
        
        Args:
            user_id: User ID whose sessions to delete
            
        Returns:
            Number of sessions deleted
        """
        sessions_to_delete = []
        for token, session_data in _sessions.items():
            if session_data['user_id'] == user_id:
                sessions_to_delete.append(token)
        
        for token in sessions_to_delete:
            del _sessions[token]
        
        return len(sessions_to_delete)
    
    @staticmethod
    def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID to get sessions for
            
        Returns:
            List of session data dictionaries
        """
        user_sessions = []
        current_time = datetime.now()
        
        for token, session_data in _sessions.items():
            if (session_data['user_id'] == user_id and 
                current_time <= session_data['expires_at']):
                
                # Don't include the token in the response for security
                session_info = {
                    'created_at': session_data['created_at'],
                    'expires_at': session_data['expires_at'],
                    'last_accessed': session_data['last_accessed']
                }
                user_sessions.append(session_info)
        
        return user_sessions
    
    @staticmethod
    def _cleanup_expired_sessions() -> int:
        """
        Clean up expired sessions to prevent memory leaks.
        
        Returns:
            Number of sessions cleaned up
        """
        global _last_cleanup
        current_time = datetime.now()
        
        # Only run cleanup every 30 minutes
        if current_time - _last_cleanup < _session_cleanup_interval:
            return 0
        
        expired_tokens = []
        for token, session_data in _sessions.items():
            if current_time > session_data['expires_at']:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del _sessions[token]
        
        _last_cleanup = current_time
        return len(expired_tokens)
    
    @staticmethod
    def get_session_stats() -> Dict[str, Any]:
        """
        Get session statistics for monitoring.
        
        Returns:
            Dictionary with session statistics
        """
        current_time = datetime.now()
        active_sessions = 0
        expired_sessions = 0
        
        for session_data in _sessions.values():
            if current_time <= session_data['expires_at']:
                active_sessions += 1
            else:
                expired_sessions += 1
        
        return {
            'total_sessions': len(_sessions),
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'last_cleanup': _last_cleanup.isoformat()
        }
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength and return requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'requirements': {
                'min_length': len(password) >= 8,
                'has_uppercase': any(c.isupper() for c in password),
                'has_lowercase': any(c.islower() for c in password),
                'has_digit': any(c.isdigit() for c in password),
                'has_special': any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
            }
        }
        
        # Check each requirement
        if not result['requirements']['min_length']:
            result['errors'].append('Password must be at least 8 characters long')
            result['is_valid'] = False
        
        if not result['requirements']['has_uppercase']:
            result['errors'].append('Password must contain at least one uppercase letter')
            result['is_valid'] = False
        
        if not result['requirements']['has_lowercase']:
            result['errors'].append('Password must contain at least one lowercase letter')
            result['is_valid'] = False
        
        if not result['requirements']['has_digit']:
            result['errors'].append('Password must contain at least one digit')
            result['is_valid'] = False
        
        # Special character is optional but recommended
        if not result['requirements']['has_special']:
            result['warnings'] = ['Consider using special characters for stronger security']
        
        return result


# Exception classes for authentication errors
class AuthenticationError(HTTPException):
    """Base authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Session"}
        )


class InvalidSessionError(AuthenticationError):
    """Invalid or expired session error"""
    def __init__(self):
        super().__init__("Invalid or expired session")


class InvalidCredentialsError(AuthenticationError):
    """Invalid login credentials error"""
    def __init__(self):
        super().__init__("Invalid email or password")


class InactiveUserError(HTTPException):
    """Inactive user account error"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )


class WeakPasswordError(HTTPException):
    """Weak password error"""
    def __init__(self, errors: List[str]):
        detail = "Password does not meet requirements: " + ", ".join(errors)
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
