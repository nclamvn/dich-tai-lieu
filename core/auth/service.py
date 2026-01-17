#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Service

Provides authentication logic including:
- User registration and login
- Password hashing with bcrypt
- JWT token generation and validation
"""

import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt
from passlib.context import CryptContext

from .models import (
    User, UserCreate, UserRole, UserStatus,
    TokenPair, TokenPayload, LoginRequest
)
from .database import UserDatabase, get_user_db

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


class AuthService:
    """Authentication service."""

    def __init__(self, db: Optional[UserDatabase] = None):
        """Initialize auth service."""
        self.db = db or get_user_db()
        self._ensure_admin_exists()

    def _ensure_admin_exists(self):
        """Ensure default admin user exists."""
        admin = self.db.get_user_by_email("admin@aipublisher.local")
        if not admin:
            # Create default admin (change password on first login!)
            default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123456")
            admin_user = User(
                email="admin@aipublisher.local",
                username="admin",
                password_hash=self.hash_password(default_password),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE
            )
            self.db.create_user(admin_user)
            logger.warning(
                "Default admin user created. Please change password immediately!"
            )

    # ========================================================================
    # Password Operations
    # ========================================================================

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # ========================================================================
    # User Registration
    # ========================================================================

    def register_user(self, data: UserCreate) -> Tuple[User, TokenPair]:
        """
        Register a new user.

        Returns:
            Tuple of (User, TokenPair) on success

        Raises:
            ValueError: If email or username already exists
        """
        # Check if email exists
        if self.db.get_user_by_email(data.email):
            raise ValueError("Email already registered")

        # Check if username exists
        if self.db.get_user_by_username(data.username):
            raise ValueError("Username already taken")

        # Create user
        user = User(
            email=data.email.lower(),
            username=data.username,
            password_hash=self.hash_password(data.password),
            full_name=data.full_name,
            organization=data.organization,
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )

        user = self.db.create_user(user)
        logger.info(f"User registered: {user.email}")

        # Generate tokens
        tokens = self.create_tokens(user)

        return user, tokens

    # ========================================================================
    # Login / Logout
    # ========================================================================

    def login(self, data: LoginRequest) -> Tuple[User, TokenPair]:
        """
        Authenticate user and return tokens.

        Returns:
            Tuple of (User, TokenPair) on success

        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email
        user = self.db.get_user_by_email(data.email.lower())

        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not self.verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")

        # Check user status
        if user.status != UserStatus.ACTIVE:
            raise ValueError(f"Account is {user.status.value}")

        # Update last login
        self.db.update_last_login(user.id)

        # Generate tokens
        tokens = self.create_tokens(user)

        logger.info(f"User logged in: {user.email}")
        return user, tokens

    def logout(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.

        Returns:
            True if token was revoked
        """
        token_hash = self._hash_token(refresh_token)
        return self.db.revoke_refresh_token(token_hash)

    def logout_all(self, user_id: int) -> int:
        """
        Logout user from all devices.

        Returns:
            Number of tokens revoked
        """
        count = self.db.revoke_all_user_tokens(user_id)
        logger.info(f"Revoked {count} tokens for user {user_id}")
        return count

    # ========================================================================
    # Token Operations
    # ========================================================================

    def create_tokens(self, user: User) -> TokenPair:
        """Create access and refresh tokens for user."""
        now = datetime.utcnow()

        # Access token (short-lived)
        access_expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "exp": access_expires,
            "iat": now,
            "type": "access"
        }
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Refresh token (long-lived)
        refresh_expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_payload = {
            "sub": str(user.id),
            "exp": refresh_expires,
            "iat": now,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)  # unique token ID
        }
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Store refresh token hash in database
        self.db.store_refresh_token(
            user_id=user.id,
            token_hash=self._hash_token(refresh_token),
            expires_at=datetime.fromtimestamp(refresh_expires.timestamp())
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    def verify_access_token(self, token: str) -> TokenPayload:
        """
        Verify access token and return payload.

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "access":
                raise ValueError("Invalid token type")

            return TokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                type=payload["type"]
            )

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

    def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.

        Returns:
            New TokenPair

        Raises:
            ValueError: If refresh token is invalid or revoked
        """
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            # Check if token is revoked
            token_hash = self._hash_token(refresh_token)
            stored_token = self.db.get_refresh_token(token_hash)

            if not stored_token:
                raise ValueError("Token not found or revoked")

            if stored_token["expires_at"] < datetime.now():
                raise ValueError("Refresh token expired")

            # Get user
            user_id = int(payload["sub"])
            user = self.db.get_user_by_id(user_id)

            if not user:
                raise ValueError("User not found")

            if user.status != UserStatus.ACTIVE:
                raise ValueError(f"Account is {user.status.value}")

            # Revoke old refresh token
            self.db.revoke_refresh_token(token_hash)

            # Create new tokens
            return self.create_tokens(user)

        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid refresh token: {e}")

    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    # ========================================================================
    # Password Operations
    # ========================================================================

    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Raises:
            ValueError: If current password is wrong
        """
        user = self.db.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        if not self.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        new_hash = self.hash_password(new_password)
        self.db.update_password(user_id, new_hash)

        # Revoke all refresh tokens (force re-login)
        self.logout_all(user_id)

        logger.info(f"Password changed for user {user_id}")
        return True

    def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Create password reset token.

        Returns:
            Reset token if user exists, None otherwise
        """
        user = self.db.get_user_by_email(email.lower())

        if not user:
            # Don't reveal if user exists
            return None

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        self.db.store_password_reset_token(
            user_id=user.id,
            token_hash=self._hash_token(reset_token),
            expires_at=expires_at
        )

        logger.info(f"Password reset token created for {email}")
        return reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token.

        Raises:
            ValueError: If token is invalid or expired
        """
        token_hash = self._hash_token(token)
        stored_token = self.db.get_password_reset_token(token_hash)

        if not stored_token:
            raise ValueError("Invalid or expired reset token")

        # Update password
        new_hash = self.hash_password(new_password)
        self.db.update_password(stored_token["user_id"], new_hash)

        # Mark token as used
        self.db.mark_password_reset_used(token_hash)

        # Revoke all refresh tokens
        self.logout_all(stored_token["user_id"])

        logger.info(f"Password reset for user {stored_token['user_id']}")
        return True

    # ========================================================================
    # User Operations
    # ========================================================================

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.get_user_by_email(email.lower())

    def update_user_role(self, user_id: int, role: UserRole, admin_id: int) -> User:
        """
        Update user role (admin only).

        Raises:
            ValueError: If user not found or invalid operation
        """
        user = self.db.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        if user_id == admin_id:
            raise ValueError("Cannot change own role")

        user.role = role
        self.db.update_user(user)

        logger.info(f"User {user_id} role changed to {role.value} by admin {admin_id}")
        return user

    def update_user_status(self, user_id: int, status: UserStatus, admin_id: int) -> User:
        """
        Update user status (admin only).

        Raises:
            ValueError: If user not found or invalid operation
        """
        user = self.db.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        if user_id == admin_id:
            raise ValueError("Cannot change own status")

        user.status = status
        self.db.update_user(user)

        # If suspended, revoke all tokens
        if status in [UserStatus.SUSPENDED, UserStatus.INACTIVE]:
            self.logout_all(user_id)

        logger.info(f"User {user_id} status changed to {status.value} by admin {admin_id}")
        return user


# Global instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
