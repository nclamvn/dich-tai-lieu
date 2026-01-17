#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Module for AI Publisher Pro

Provides:
- User management with SQLite storage
- Password hashing with bcrypt
- JWT token authentication
- Role-based access control (RBAC)
"""

from .models import User, UserRole, UserStatus, TokenPair
from .database import UserDatabase, get_user_db
from .service import AuthService, get_auth_service
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_role
)

__all__ = [
    # Models
    'User',
    'UserRole',
    'UserStatus',
    'TokenPair',
    # Database
    'UserDatabase',
    'get_user_db',
    # Service
    'AuthService',
    'get_auth_service',
    # Dependencies
    'get_current_user',
    'get_current_active_user',
    'get_optional_user',
    'require_role',
]
