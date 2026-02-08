#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI Dependencies for Authentication

Provides dependency injection functions for protecting endpoints.
"""

import logging
from typing import Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import User, UserRole, TokenPayload
from .service import AuthService, get_auth_service

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenPayload:
    """
    Extract and verify JWT token from Authorization header.

    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = auth_service.verify_access_token(credentials.credentials)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    payload: TokenPayload = Depends(get_token_payload),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Get current authenticated user.

    Usage:
        @app.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    user = auth_service.get_user(int(payload.sub))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.

    Raises:
        HTTPException 403: If user is not active
    """
    from .models import UserStatus

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}"
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Usage for endpoints that work with or without auth:
        @app.get("/public")
        async def public_endpoint(user: Optional[User] = Depends(get_optional_user)):
            if user:
                # Authenticated user
            else:
                # Anonymous access
    """
    if not credentials:
        return None

    try:
        payload = auth_service.verify_access_token(credentials.credentials)
        user = auth_service.get_user(int(payload.sub))
        return user
    except (ValueError, Exception):
        return None


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(require_role(UserRole.ADMIN))
        ):
            # Only admins can delete users
    """
    async def role_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' not allowed. Required: {[r.value for r in allowed_roles]}"
            )
        return user

    return role_checker


def require_admin():
    """Shortcut for requiring admin role."""
    return require_role(UserRole.ADMIN)


def require_manager():
    """Shortcut for requiring manager or admin role."""
    return require_role(UserRole.ADMIN, UserRole.MANAGER)


# ============================================================================
# Legacy Session Support (for backward compatibility)
# ============================================================================

async def get_session_or_jwt_user(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """
    Support both legacy session tokens and JWT.

    Checks JWT first, then falls back to session token.
    This enables gradual migration from session-based to JWT auth.
    """
    # Try JWT first
    if credentials:
        try:
            payload = auth_service.verify_access_token(credentials.credentials)
            user = auth_service.get_user(int(payload.sub))
            if user:
                return user
        except (ValueError, Exception):
            pass

    # Fall back to legacy session token
    if x_session_token:
        from api.security import security_manager
        try:
            session = security_manager.validate_session(x_session_token)
            # Create a minimal user object from session
            return User(
                id=0,  # Legacy sessions don't have user IDs
                email=f"{session.username}@legacy.local",
                username=session.username,
                password_hash="",
                full_name=session.username,
                organization=session.organization,
                role=UserRole.USER
            )
        except Exception as e:
            logger.debug("Legacy session validation failed: %s", e)

    return None
