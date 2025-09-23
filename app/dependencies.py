"""
Dependency injection functions for FastAPI routes.
Provides authentication and external service dependencies.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import UserInDB
from app.utils.auth import AuthUtils


# Security scheme for token authentication
security = HTTPBearer(auto_error=False)


async def get_current_active_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInDB:
    """
    Get the current authenticated active user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        UserInDB: The authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # For demo purposes, return a mock user
    # In production, this would validate the token and fetch from database
    from app.models.user import UserInDB
    import uuid
    from datetime import datetime

    return UserInDB(
        id=uuid.uuid4(),
        email="demo@example.com",
        full_name="Demo User",
        monthly_income=50000.0,
        password_hash="hashed_password",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class BlockchainInterface:
    """Mock blockchain interface for compatibility."""

    def __init__(self):
        self.connected = False

    async def connect(self):
        """Mock connection to blockchain."""
        self.connected = True
        return True

    async def disconnect(self):
        """Mock disconnection from blockchain."""
        self.connected = False
        return True

    async def record_transaction(self, transaction_data: dict):
        """Mock recording transaction on blockchain."""
        # In a real implementation, this would interact with blockchain
        return {"tx_hash": "mock_tx_hash", "status": "confirmed"}


# Global blockchain instance
blockchain_interface = BlockchainInterface()


async def get_blockchain() -> BlockchainInterface:
    """
    Get blockchain interface instance.

    Returns:
        BlockchainInterface: The blockchain interface
    """
    return blockchain_interface
