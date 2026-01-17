#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit Tests for Authentication System

Tests for:
- Password hashing
- JWT token generation/validation
- User CRUD operations
- Role-based access control
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

# Set test environment
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests"


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password_returns_different_hash(self):
        """Hashing same password twice should produce different hashes (due to salt)."""
        from core.auth.service import AuthService

        service = AuthService.__new__(AuthService)
        service.db = None

        hash1 = service.hash_password("test123")
        hash2 = service.hash_password("test123")

        assert hash1 != hash2
        assert hash1.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        from core.auth.service import AuthService

        service = AuthService.__new__(AuthService)
        service.db = None

        password = "MySecurePassword123!"
        hashed = service.hash_password(password)

        assert service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Wrong password should fail verification."""
        from core.auth.service import AuthService

        service = AuthService.__new__(AuthService)
        service.db = None

        password = "MySecurePassword123!"
        hashed = service.hash_password(password)

        assert service.verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Empty password should fail verification."""
        from core.auth.service import AuthService

        service = AuthService.__new__(AuthService)
        service.db = None

        hashed = service.hash_password("real_password")

        assert service.verify_password("", hashed) is False


class TestUserModels:
    """Tests for user data models."""

    def test_user_create_model_validation(self):
        """UserCreate model should validate required fields."""
        from core.auth.models import UserCreate

        # Valid user
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123"
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_user_create_email_validation(self):
        """UserCreate should reject invalid emails."""
        from core.auth.models import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                username="testuser",
                password="password123"
            )

    def test_user_create_password_min_length(self):
        """UserCreate should reject short passwords."""
        from core.auth.models import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="short"  # Less than 8 characters
            )

    def test_user_create_username_min_length(self):
        """UserCreate should reject short usernames."""
        from core.auth.models import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="ab",  # Less than 3 characters
                password="password123"
            )

    def test_user_role_enum(self):
        """UserRole enum should have expected values."""
        from core.auth.models import UserRole

        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.USER.value == "user"
        assert UserRole.VIEWER.value == "viewer"

    def test_user_status_enum(self):
        """UserStatus enum should have expected values."""
        from core.auth.models import UserStatus

        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING.value == "pending"


class TestUserDatabase:
    """Tests for user database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_users.db"
            from core.auth.database import UserDatabase
            db = UserDatabase(db_path)
            yield db
            db.close()

    def test_create_user(self, temp_db):
        """Should create a user successfully."""
        from core.auth.models import User, UserRole, UserStatus

        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )

        created = temp_db.create_user(user)

        assert created.id is not None
        assert created.email == "test@example.com"
        assert created.username == "testuser"

    def test_get_user_by_email(self, temp_db):
        """Should retrieve user by email."""
        from core.auth.models import User, UserRole, UserStatus

        user = User(
            email="findme@example.com",
            username="findme",
            password_hash="hashed",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        temp_db.create_user(user)

        found = temp_db.get_user_by_email("findme@example.com")

        assert found is not None
        assert found.username == "findme"

    def test_get_user_by_email_not_found(self, temp_db):
        """Should return None for non-existent email."""
        found = temp_db.get_user_by_email("nonexistent@example.com")
        assert found is None

    def test_get_user_by_username(self, temp_db):
        """Should retrieve user by username."""
        from core.auth.models import User, UserRole, UserStatus

        user = User(
            email="user@example.com",
            username="uniqueuser",
            password_hash="hashed",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        temp_db.create_user(user)

        found = temp_db.get_user_by_username("uniqueuser")

        assert found is not None
        assert found.email == "user@example.com"

    def test_update_user(self, temp_db):
        """Should update user details."""
        from core.auth.models import User, UserRole, UserStatus

        user = User(
            email="update@example.com",
            username="updateuser",
            password_hash="hashed",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        created = temp_db.create_user(user)

        created.full_name = "Updated Name"
        created.organization = "New Org"
        updated = temp_db.update_user(created)

        assert updated.full_name == "Updated Name"
        assert updated.organization == "New Org"

    def test_list_users(self, temp_db):
        """Should list users with pagination."""
        from core.auth.models import User, UserRole, UserStatus

        # Create multiple users
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash="hashed",
                role=UserRole.USER,
                status=UserStatus.ACTIVE
            )
            temp_db.create_user(user)

        users = temp_db.list_users(limit=3)
        assert len(users) == 3

        all_users = temp_db.list_users(limit=10)
        assert len(all_users) == 5

    def test_count_users(self, temp_db):
        """Should count users correctly."""
        from core.auth.models import User, UserRole, UserStatus

        for i in range(3):
            user = User(
                email=f"count{i}@example.com",
                username=f"count{i}",
                password_hash="hashed",
                role=UserRole.USER,
                status=UserStatus.ACTIVE
            )
            temp_db.create_user(user)

        count = temp_db.count_users()
        assert count == 3


class TestTokenPair:
    """Tests for JWT token operations."""

    def test_token_pair_model(self):
        """TokenPair model should have required fields."""
        from core.auth.models import TokenPair

        tokens = TokenPair(
            access_token="access123",
            refresh_token="refresh456",
            expires_in=1800
        )

        assert tokens.access_token == "access123"
        assert tokens.refresh_token == "refresh456"
        assert tokens.token_type == "bearer"
        assert tokens.expires_in == 1800


class TestErrorIntegration:
    """Tests for error tracking integration."""

    def test_detect_error_category_api(self):
        """Should detect API errors correctly."""
        from core.error_integration import detect_error_category
        from core.error_tracker import ErrorCategory

        error = ConnectionError("API connection failed")
        category = detect_error_category(error)
        assert category == ErrorCategory.NETWORK_ERROR

    def test_detect_error_category_validation(self):
        """Should detect validation errors correctly."""
        from core.error_integration import detect_error_category
        from core.error_tracker import ErrorCategory

        error = ValueError("Invalid input")
        category = detect_error_category(error)
        assert category == ErrorCategory.VALIDATION_ERROR

    def test_detect_error_category_timeout(self):
        """Should detect timeout errors correctly."""
        from core.error_integration import detect_error_category
        from core.error_tracker import ErrorCategory

        error = TimeoutError("Request timed out")
        category = detect_error_category(error)
        assert category == ErrorCategory.TIMEOUT_ERROR

    def test_detect_error_severity(self):
        """Should detect error severity correctly."""
        from core.error_integration import detect_error_severity
        from core.error_tracker import ErrorCategory, ErrorSeverity

        # Database errors are critical
        error = Exception("Database error")
        severity = detect_error_severity(error, ErrorCategory.DATABASE_ERROR)
        assert severity == ErrorSeverity.CRITICAL

        # Validation errors are low
        error = ValueError("Invalid input")
        severity = detect_error_severity(error, ErrorCategory.VALIDATION_ERROR)
        assert severity == ErrorSeverity.LOW


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
