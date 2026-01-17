#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication API Router

Provides REST endpoints for user authentication:
- Registration
- Login / Logout
- Token refresh
- Password management
- User management (admin)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from core.auth import (
    AuthService, get_auth_service,
    User, UserRole, UserStatus,
    get_current_user, get_current_active_user, require_role
)
from core.auth.models import (
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, TokenPair,
    PasswordChange, PasswordReset, PasswordResetConfirm
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.

    Returns access and refresh tokens on success.
    """
    try:
        user, tokens = auth_service.register_user(data)
        return {
            "message": "Registration successful",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                organization=user.organization,
                role=user.role,
                status=user.status,
                created_at=user.created_at,
                last_login=user.last_login,
                jobs_count=user.jobs_count
            ).model_dump(),
            "tokens": tokens.model_dump()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=dict)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return tokens.
    """
    try:
        user, tokens = auth_service.login(data)
        return {
            "message": "Login successful",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                organization=user.organization,
                role=user.role,
                status=user.status,
                created_at=user.created_at,
                last_login=user.last_login,
                jobs_count=user.jobs_count
            ).model_dump(),
            "tokens": tokens.model_dump()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    """
    try:
        tokens = auth_service.refresh_tokens(refresh_token)
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/password/reset-request")
async def request_password_reset(
    data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset email.

    Note: Always returns success to prevent email enumeration.
    """
    token = auth_service.create_password_reset_token(data.email)

    # In production, send email with reset link
    # For now, return token directly (development only)
    return {
        "message": "If the email exists, a password reset link will be sent",
        # Remove in production:
        "_dev_token": token if token else None
    }


@router.post("/password/reset-confirm")
async def confirm_password_reset(
    data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset password using reset token.
    """
    try:
        auth_service.reset_password(data.token, data.new_password)
        return {"message": "Password reset successful"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Protected Endpoints (Auth Required)
# ============================================================================

@router.post("/logout")
async def logout(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
    user: User = Depends(get_current_active_user)
):
    """
    Logout current session (revoke refresh token).
    """
    auth_service.logout(refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(
    auth_service: AuthService = Depends(get_auth_service),
    user: User = Depends(get_current_active_user)
):
    """
    Logout from all devices (revoke all refresh tokens).
    """
    count = auth_service.logout_all(user.id)
    return {
        "message": f"Logged out from {count} sessions",
        "sessions_revoked": count
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_active_user)):
    """
    Get current user profile.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        organization=user.organization,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login,
        jobs_count=user.jobs_count
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update current user profile.
    """
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.organization is not None:
        user.organization = data.organization
    if data.preferences is not None:
        user.preferences = data.preferences

    auth_service.db.update_user(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        organization=user.organization,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login,
        jobs_count=user.jobs_count
    )


@router.post("/password/change")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change current user's password.
    """
    try:
        auth_service.change_password(
            user.id,
            data.current_password,
            data.new_password
        )
        return {"message": "Password changed successfully. Please login again."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/users", response_model=dict)
async def list_users(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    List all users (admin/manager only).
    """
    users = auth_service.db.list_users(
        role=role,
        status=status,
        limit=limit,
        offset=offset
    )
    total = auth_service.db.count_users(role=role, status=status)

    return {
        "users": [
            UserResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                organization=u.organization,
                role=u.role,
                status=u.status,
                created_at=u.created_at,
                last_login=u.last_login,
                jobs_count=u.jobs_count
            ).model_dump()
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get user by ID (admin/manager only).
    """
    user = auth_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        organization=user.organization,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login,
        jobs_count=user.jobs_count
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: UserRole,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user role (admin only).
    """
    try:
        user = auth_service.update_user_role(user_id, role, admin.id)
        return {
            "message": f"User role updated to {role.value}",
            "user_id": user_id,
            "new_role": role.value
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status: UserStatus,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user status (admin only).

    Setting status to 'suspended' or 'inactive' will revoke all tokens.
    """
    try:
        user = auth_service.update_user_status(user_id, status, admin.id)
        return {
            "message": f"User status updated to {status.value}",
            "user_id": user_id,
            "new_status": status.value
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Deactivate user (admin only).

    This performs a soft delete (sets status to inactive).
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    success = auth_service.db.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "User deactivated", "user_id": user_id}
