from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from app.configs.config import settings
from app.database import SupabaseDB, get_db
from app.models.user import User
from app.blockchain_interface import BlockchainInterface

# OAuth2 password bearer token URL
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: SupabaseDB = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Get user from database
    user_data = await db.get_user(user_id)
    if not user_data:
        raise credentials_exception
    
    # Create User model
    user = User(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        phone_number=user_data.get("phone_number"),
        notification_preferences=user_data.get("notification_preferences", {}),
        is_active=user_data["is_active"],
        is_verified=user_data["is_verified"],
        created_at=user_data["created_at"],
        updated_at=user_data["updated_at"],
        last_login=user_data.get("last_login")
    )
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_blockchain():
    """
    Get blockchain interface
    """
    return BlockchainInterface(settings.BLOCKCHAIN_NODE_URL)