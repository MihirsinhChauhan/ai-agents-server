"""
Authentication middleware and dependency functions for FastAPI.
Provides session-based authentication and route protection.
"""

from typing import Optional, Annotated
from datetime import datetime
from fastapi import Depends, Request, Response, Cookie, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.auth import AuthUtils, InvalidSessionError, InactiveUserError
from app.repositories.user_repository import UserRepository
from app.models.user import UserInDB, UserProfileResponse


# Optional bearer token security scheme (for compatibility)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_session_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[str]:
    """
    Extract session token from Authorization header (Bearer token only).

    Args:
        authorization: Authorization header credentials

    Returns:
        Session token if found, None otherwise
    """
    # Only use Authorization header with Bearer scheme
    if authorization and authorization.scheme.lower() == "bearer":
        return authorization.credentials

    return None


async def get_current_session(
    session_token: Optional[str] = Depends(get_session_token)
) -> Optional[dict]:
    """
    Get current session data if valid.
    
    Args:
        session_token: Session token from dependency
        
    Returns:
        Session data if valid, None otherwise
    """
    if not session_token:
        return None
    
    return AuthUtils.get_session(session_token)


async def get_current_user(
    session_data: Optional[dict] = Depends(get_current_session)
) -> Optional[UserInDB]:
    """
    Get current authenticated user from session.
    
    Args:
        session_data: Session data from dependency
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not session_data:
        return None
    
    user_repo = UserRepository()
    user = await user_repo.get_by_id(session_data['user_id'])
    
    if not user or not user.is_active:
        return None
    
    return user


async def require_authentication(
    current_user: Optional[UserInDB] = Depends(get_current_user)
) -> UserInDB:
    """
    Require valid authentication for protected routes.
    
    Args:
        current_user: Current user from dependency
        
    Returns:
        Authenticated user object
        
    Raises:
        InvalidSessionError: If no valid session
        InactiveUserError: If user account is inactive
    """
    if not current_user:
        raise InvalidSessionError()
    
    if not current_user.is_active:
        raise InactiveUserError()
    
    return current_user


async def require_verified_user(
    current_user: UserInDB = Depends(require_authentication)
) -> UserInDB:
    """
    Require verified user account for certain operations.
    
    Args:
        current_user: Authenticated user from dependency
        
    Returns:
        Verified user object
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required for this operation"
        )
    
    return current_user


def create_session_cookie(
    session_token: str,
    response: Response,
    max_age: int = 86400,  # 24 hours
    secure: bool = True,
    same_site: str = "lax"
) -> None:
    """
    Create a secure session cookie.
    
    Args:
        session_token: Session token to store in cookie
        response: FastAPI response object
        max_age: Cookie max age in seconds (default: 24 hours)
        secure: Whether cookie should be secure (HTTPS only)
        same_site: SameSite cookie attribute
    """
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=max_age,
        httponly=True,  # Prevent XSS
        secure=secure,  # HTTPS only in production
        samesite=same_site,  # CSRF protection
        path="/"  # Available for all paths
    )


def clear_session_cookie(response: Response) -> None:
    """
    Clear the session cookie (logout).
    
    Args:
        response: FastAPI response object
    """
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )


class AuthMiddleware:
    """
    Authentication middleware class for additional session management.
    """
    
    @staticmethod
    async def extend_session_on_activity(
        session_token: Optional[str] = Depends(get_session_token)
    ) -> None:
        """
        Extend session expiration on user activity.
        
        Args:
            session_token: Current session token
        """
        if session_token:
            # Extend session by 24 hours on activity
            AuthUtils.extend_session(session_token, hours=24)
    
    @staticmethod
    async def log_authentication_attempt(
        request: Request,
        user_id: Optional[str] = None,
        success: bool = False
    ) -> None:
        """
        Log authentication attempts for security monitoring.
        
        Args:
            request: FastAPI request object
            user_id: User ID if known
            success: Whether authentication was successful
        """
        # In production, log to proper logging system
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_id": user_id,
            "success": success,
            "endpoint": str(request.url)
        }
        
        # For now, just print (in production, use proper logging)
        print(f"Auth attempt: {log_data}")


# Convenience type aliases for dependency injection
CurrentUser = Annotated[UserInDB, Depends(require_authentication)]
VerifiedUser = Annotated[UserInDB, Depends(require_verified_user)]
OptionalUser = Annotated[Optional[UserInDB], Depends(get_current_user)]
SessionData = Annotated[Optional[dict], Depends(get_current_session)]
