"""
Session-based authentication routes for DebtEase application.
Provides comprehensive user authentication, registration, session management,
and profile management with security features.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from app.repositories.user_repository import UserRepository
from app.models.user import UserCreate, UserInDB, UserProfileResponse, UserUpdate
from app.utils.auth import (
    AuthUtils, 
    InvalidCredentialsError, 
    InactiveUserError,
    WeakPasswordError
)
from app.middleware.auth import (
    CurrentUser,
    OptionalUser,
    create_session_cookie,
    clear_session_cookie,
    AuthMiddleware,
    get_session_token
)

router = APIRouter()


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")


class LoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class AuthResponse(BaseModel):
    """Authentication response model"""
    user: UserProfileResponse = Field(..., description="User profile data")
    session_expires_at: str = Field(..., description="Session expiration time")
    message: str = Field(..., description="Success message")


@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: RegisterRequest,
    response: Response,
    request: Request
) -> Any:
    """
    Register a new user account.
    
    Creates a new user with proper password validation and immediate login.
    """
    user_repo = UserRepository()
    
    # Validate password strength
    password_validation = AuthUtils.validate_password_strength(user_data.password)
    if not password_validation['is_valid']:
        raise WeakPasswordError(password_validation['errors'])
    
    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    # Hash password
    hashed_password = AuthUtils.hash_password(user_data.password)
    
    # Create user
    user_create = UserCreate(
        email=user_data.email,
        full_name=user_data.full_name,
        monthly_income=user_data.monthly_income,
        phone_number=user_data.phone_number,
        hashed_password=hashed_password
    )
    
    try:
        new_user = await user_repo.create_user(user_create)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )
    
    # Create session
    session_token = AuthUtils.create_session(
        user_id=str(new_user.id),
        user_data={
            'email': new_user.email,
            'full_name': new_user.full_name,
            'is_verified': new_user.is_verified
        }
    )
    
    # Set session cookie
    create_session_cookie(session_token, response)
    
    # Log registration
    await AuthMiddleware.log_authentication_attempt(
        request, 
        user_id=str(new_user.id), 
        success=True
    )
    
    # Get session data for response
    session_data = AuthUtils.get_session(session_token)
    
    return AuthResponse(
        user=UserProfileResponse.from_user_in_db(new_user),
        session_expires_at=session_data['expires_at'].isoformat(),
        message="Registration successful"
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: LoginRequest,
    response: Response = None,
    request: Request = None
) -> Any:
    """
    Login with email and password (JSON request).

    Creates a new session and sets secure cookie.
    """
    user_repo = UserRepository()

    # Find user by email
    user = await user_repo.get_by_email(credentials.email)
    if not user:
        await AuthMiddleware.log_authentication_attempt(request, success=False)
        raise InvalidCredentialsError()

    # Verify password
    if not AuthUtils.verify_password(credentials.password, user.hashed_password):
        await AuthMiddleware.log_authentication_attempt(
            request,
            user_id=str(user.id),
            success=False
        )
        raise InvalidCredentialsError()

    # Check if user is active
    if not user.is_active:
        await AuthMiddleware.log_authentication_attempt(
            request,
            user_id=str(user.id),
            success=False
        )
        raise InactiveUserError()

    # Create session
    session_token = AuthUtils.create_session(
        user_id=str(user.id),
        user_data={
            'email': user.email,
            'full_name': user.full_name,
            'is_verified': user.is_verified
        }
    )

    # Set session cookie (only if response is provided)
    if response:
        create_session_cookie(session_token, response)

    # Log successful login
    await AuthMiddleware.log_authentication_attempt(
        request,
        user_id=str(user.id),
        success=True
    )

    # Get session data for response
    session_data = AuthUtils.get_session(session_token)

    return AuthResponse(
        user=UserProfileResponse.from_user_in_db(user),
        session_expires_at=session_data['expires_at'].isoformat(),
        message="Login successful"
    )


@router.post("/login/form")
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None
) -> Any:
    """
    Primary OAuth2-compatible login endpoint for frontend form data.

    This is the main login endpoint used by the frontend. It accepts form data
    (username/password) and returns session tokens compatible with the /me endpoint.
    """
    try:
        user_repo = UserRepository()

        # Find user by email (username field in OAuth2 form)
        user = await user_repo.get_by_email(form_data.username)
        if not user:
            await AuthMiddleware.log_authentication_attempt(request, success=False)
            raise InvalidCredentialsError()

        # Verify password
        if not AuthUtils.verify_password(form_data.password, user.hashed_password):
            await AuthMiddleware.log_authentication_attempt(
                request,
                user_id=str(user.id),
                success=False
            )
            raise InvalidCredentialsError()

        # Check if user is active
        if not user.is_active:
            await AuthMiddleware.log_authentication_attempt(
                request,
                user_id=str(user.id),
                success=False
            )
            raise InactiveUserError()

        # Create session token
        session_token = AuthUtils.create_session(
            user_id=str(user.id),
            user_data={
                'email': user.email,
                'full_name': user.full_name,
                'is_verified': user.is_verified
            }
        )

        # Log successful login
        await AuthMiddleware.log_authentication_attempt(
            request,
            user_id=str(user.id),
            success=True
        )

        # Get session data for expiration
        session_data = AuthUtils.get_session(session_token)

        # Return OAuth2-compatible response with session token as access_token
        return {
            "access_token": session_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "monthly_income": user.monthly_income,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            },
            "expires_at": session_data['expires_at'].isoformat() if session_data else None
        }

    except (InvalidCredentialsError, InactiveUserError):
        # Re-raise authentication errors
        raise
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )



@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    response: Response,
    session_token: Optional[str] = Depends(get_session_token)
) -> Dict[str, str]:
    """
    Logout current user session.
    
    Destroys session and clears cookie.
    """
    if session_token:
        AuthUtils.delete_session(session_token)
    
    clear_session_cookie(response)
    
    return {"message": "Logout successful"}


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: CurrentUser,
    response: Response
) -> Dict[str, Any]:
    """
    Logout all sessions for current user.
    
    Useful for security when user suspects account compromise.
    """
    deleted_count = AuthUtils.delete_user_sessions(str(current_user.id))
    clear_session_cookie(response)
    
    return {
        "message": "All sessions logged out",
        "sessions_deleted": deleted_count
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: CurrentUser) -> UserProfileResponse:
    """
    Get current user's profile information.
    """
    return UserProfileResponse.from_user_in_db(current_user)


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserUpdate,
    current_user: CurrentUser
) -> UserProfileResponse:
    """
    Update current user's profile.
    
    Allows updating name, phone number, monthly income, and notification preferences.
    """
    user_repo = UserRepository()
    
    # Update user profile
    updated_user = await user_repo.update_user(current_user.id, profile_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfileResponse.from_user_in_db(updated_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    response: Response
) -> Dict[str, str]:
    """
    Change user's password.
    
    Requires current password for security.
    """
    user_repo = UserRepository()
    
    # Verify current password
    if not AuthUtils.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    password_validation = AuthUtils.validate_password_strength(password_data.new_password)
    if not password_validation['is_valid']:
        raise WeakPasswordError(password_validation['errors'])
    
    # Hash new password
    new_password_hash = AuthUtils.hash_password(password_data.new_password)
    
    # Update password
    await user_repo.update_password_hash(current_user.id, new_password_hash)
    
    # Logout all other sessions for security
    AuthUtils.delete_user_sessions(str(current_user.id))
    clear_session_cookie(response)
    
    return {"message": "Password changed successfully. Please log in again."}


@router.get("/sessions")
async def get_user_sessions(current_user: CurrentUser) -> Dict[str, Any]:
    """
    Get all active sessions for current user.
    
    Useful for security monitoring.
    """
    sessions = AuthUtils.get_user_sessions(str(current_user.id))
    
    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@router.get("/verify-session")
async def verify_session(current_user: CurrentUser) -> Dict[str, Any]:
    """
    Verify current session is valid.
    
    Can be used by frontend to check authentication status.
    """
    return {
        "authenticated": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active
    }


@router.post("/extend-session")
async def extend_session(
    current_user: CurrentUser,
    session_token: Optional[str] = Depends(get_session_token),
    hours: int = Query(default=24, ge=1, le=168, description="Hours to extend (1-168)")
) -> Dict[str, Any]:
    """
    Extend current session expiration.
    
    Useful for "remember me" functionality.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session to extend"
        )
    
    success = AuthUtils.extend_session(session_token, hours)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extend session"
        )
    
    session_data = AuthUtils.get_session(session_token)
    
    return {
        "message": f"Session extended by {hours} hours",
        "expires_at": session_data['expires_at'].isoformat()
    }
