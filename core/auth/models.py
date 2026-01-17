#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Models

Defines User, Role, and Token models for the authentication system.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"           # Full access
    MANAGER = "manager"       # Manage users, view all jobs
    USER = "user"             # Standard user
    VIEWER = "viewer"         # Read-only access
    API = "api"               # API-only access (for integrations)


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"       # Email verification pending


class User(BaseModel):
    """User model."""
    id: Optional[int] = None
    email: EmailStr
    username: str
    password_hash: str = ""   # Never expose in API responses

    # Profile
    full_name: Optional[str] = None
    organization: Optional[str] = None

    # Access control
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    # Settings
    preferences: dict = Field(default_factory=dict)

    # Usage tracking
    jobs_count: int = 0
    tokens_used: int = 0

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = None
    organization: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    full_name: Optional[str] = None
    organization: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(BaseModel):
    """User response schema (excludes sensitive data)."""
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    organization: Optional[str] = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime] = None
    jobs_count: int = 0


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """JWT token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str          # user_id
    email: str
    username: str
    role: UserRole
    exp: datetime     # expiration
    iat: datetime     # issued at
    type: str         # "access" or "refresh"


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(min_length=8, max_length=100)
