from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
import uuid

from app.configs.config import settings
from app.database import SupabaseDB, get_db
from app.models.user import UserCreate, User, UserInDB

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


@router.post("/register", response_model=User)
async def register_user(
    user_in: UserCreate,
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Register a new user
    """
    # Check if user exists
    existing_user = await db.get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user ID
    user_id = str(uuid.uuid4())
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user_data = {
        "id": user_id,
        "email": user_in.email,
        "full_name": user_in.full_name,
        "phone_number": user_in.phone_number,
        "hashed_password": hashed_password,
        "notification_preferences": user_in.notification_preferences,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert user into database
    created_user = await db.create_user(user_data)
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Return user without sensitive information
    user_response = {
        "id": created_user["id"],
        "email": created_user["email"],
        "full_name": created_user["full_name"],
        "phone_number": created_user["phone_number"],
        "notification_preferences": created_user["notification_preferences"],
        "is_active": created_user["is_active"],
        "is_verified": created_user["is_verified"],
        "created_at": created_user["created_at"],
        "updated_at": created_user["updated_at"]
    }
    
    return User(**user_response)


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Find user by email
    user = await db.get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=access_token_expires
    )
    
    # Update last login time
    await db.update_user(
        user["id"],
        {"last_login": datetime.utcnow().isoformat()}
    )
    
    # Return token
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }