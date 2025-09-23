"""
Middleware package for DebtEase application.
Contains authentication and other middleware components.
"""

from .auth import (
    get_session_token,
    get_current_session,
    get_current_user,
    require_authentication,
    require_verified_user,
    create_session_cookie,
    clear_session_cookie,
    AuthMiddleware,
    CurrentUser,
    VerifiedUser,
    OptionalUser,
    SessionData
)

__all__ = [
    "get_session_token",
    "get_current_session",
    "get_current_user",
    "require_authentication",
    "require_verified_user",
    "create_session_cookie",
    "clear_session_cookie",
    "AuthMiddleware",
    "CurrentUser",
    "VerifiedUser",
    "OptionalUser",
    "SessionData"
]



