"""
RRI-T Sprint 2: Authentication service tests.

Persona coverage: Security Auditor, QA Destroyer
Dimensions: D4 (Security), D5 (Data Integrity), D7 (Edge Cases)
"""

import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.auth.service import AuthService, pwd_context
from core.auth.database import UserDatabase
from core.auth.models import (
    User, UserCreate, UserRole, UserStatus,
    TokenPair, TokenPayload, LoginRequest
)


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_db(tmp_path):
    """Fresh UserDatabase in temp directory."""
    db = UserDatabase(db_path=tmp_path / "users.db")
    return db


@pytest.fixture
def auth_service(user_db):
    """AuthService with fresh temp database (admin auto-create patched)."""
    with patch.object(AuthService, "_ensure_admin_exists"):
        service = AuthService(db=user_db)
    return service


@pytest.fixture
def registered_user(auth_service):
    """Create and return a registered user + tokens."""
    data = UserCreate(
        email="test@example.com",
        username="testuser",
        password="SecureP@ss123",
        full_name="Test User",
    )
    user, tokens = auth_service.register_user(data)
    return user, tokens


# ===========================================================================
# AUTH-001: Token expiration -> ValueError
# ===========================================================================

class TestTokenExpiration:
    """Security Auditor persona — expired tokens must be rejected."""

    @pytest.mark.p0
    def test_auth_001_expired_token_raises(self, auth_service):
        """AUTH-001 | Security | Expired access token -> ValueError"""
        import jwt as pyjwt
        from core.auth.service import JWT_SECRET_KEY, JWT_ALGORITHM

        expired_payload = {
            "sub": "1",
            "email": "test@example.com",
            "username": "testuser",
            "role": "user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access"
        }
        expired_token = pyjwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        with pytest.raises(ValueError, match="expired"):
            auth_service.verify_access_token(expired_token)

    @pytest.mark.p0
    def test_auth_001b_valid_token_verifies(self, auth_service, registered_user):
        """AUTH-001b | Security | Valid access token -> TokenPayload"""
        _, tokens = registered_user
        payload = auth_service.verify_access_token(tokens.access_token)
        assert payload.email == "test@example.com"
        assert payload.type == "access"

    @pytest.mark.p0
    def test_auth_001c_wrong_type_token_rejected(self, auth_service, registered_user):
        """AUTH-001c | Security | Refresh token passed as access -> ValueError"""
        _, tokens = registered_user
        with pytest.raises(ValueError, match="[Ii]nvalid token"):
            auth_service.verify_access_token(tokens.refresh_token)


# ===========================================================================
# AUTH-002: SQL injection prevention
# ===========================================================================

class TestSQLInjection:
    """Security Auditor persona — SQL injection in login blocked."""

    @pytest.mark.p0
    def test_auth_002_sql_injection_email(self, auth_service):
        """AUTH-002 | Security | SQL injection in email -> rejected by Pydantic validation"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoginRequest(
                email="' OR '1'='1' --",
                password="anything"
            )

    @pytest.mark.p0
    def test_auth_002b_sql_injection_password(self, auth_service, registered_user):
        """AUTH-002b | Security | SQL injection in password -> ValueError"""
        data = LoginRequest(
            email="test@example.com",
            password="' OR '1'='1"
        )
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            auth_service.login(data)


# ===========================================================================
# AUTH-003: Passwords hashed (not plaintext)
# ===========================================================================

class TestPasswordHashing:
    """Security Auditor persona — no plaintext passwords."""

    @pytest.mark.p0
    def test_auth_003_password_hashed_not_plaintext(self, auth_service):
        """AUTH-003 | Security | Stored password is hashed, not plaintext"""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are ~60 chars
        assert hashed.startswith("$2")  # bcrypt prefix

    @pytest.mark.p0
    def test_auth_003b_verify_correct_password(self, auth_service):
        """AUTH-003b | Security | Correct password verifies"""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True

    @pytest.mark.p0
    def test_auth_003c_verify_wrong_password(self, auth_service):
        """AUTH-003c | Security | Wrong password fails verification"""
        hashed = auth_service.hash_password("correct_password")
        assert auth_service.verify_password("wrong_password", hashed) is False

    @pytest.mark.p1
    def test_auth_003d_same_password_different_hashes(self, auth_service):
        """AUTH-003d | Security | Same password -> different hashes (salted)"""
        password = "SamePassword"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        assert hash1 != hash2  # bcrypt uses random salt


# ===========================================================================
# AUTH-004: Registration and login
# ===========================================================================

class TestRegistrationLogin:
    """End User + QA Destroyer — registration and login flows."""

    @pytest.mark.p0
    def test_auth_004_register_success(self, auth_service):
        """AUTH-004 | End User | Register new user -> User + TokenPair"""
        data = UserCreate(
            email="new@example.com",
            username="newuser",
            password="StrongPass1!",
            full_name="New User",
        )
        user, tokens = auth_service.register_user(data)
        assert user.email == "new@example.com"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.ACTIVE
        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.expires_in > 0

    @pytest.mark.p0
    def test_auth_004b_duplicate_email_rejected(self, auth_service, registered_user):
        """AUTH-004b | QA Destroyer | Duplicate email -> ValueError"""
        data = UserCreate(
            email="test@example.com",  # same as registered_user
            username="different",
            password="Pass123!",
            full_name="Another User",
        )
        with pytest.raises(ValueError, match="[Ee]mail already"):
            auth_service.register_user(data)

    @pytest.mark.p0
    def test_auth_004c_duplicate_username_rejected(self, auth_service, registered_user):
        """AUTH-004c | QA Destroyer | Duplicate username -> ValueError"""
        data = UserCreate(
            email="different@example.com",
            username="testuser",  # same as registered_user
            password="Pass123!",
            full_name="Another User",
        )
        with pytest.raises(ValueError, match="[Uu]sername already"):
            auth_service.register_user(data)

    @pytest.mark.p0
    def test_auth_004d_login_success(self, auth_service, registered_user):
        """AUTH-004d | End User | Login with correct credentials -> tokens"""
        data = LoginRequest(email="test@example.com", password="SecureP@ss123")
        user, tokens = auth_service.login(data)
        assert user.email == "test@example.com"
        assert tokens.access_token

    @pytest.mark.p0
    def test_auth_004e_login_wrong_password(self, auth_service, registered_user):
        """AUTH-004e | QA Destroyer | Login with wrong password -> ValueError"""
        data = LoginRequest(email="test@example.com", password="WrongPassword")
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            auth_service.login(data)

    @pytest.mark.p0
    def test_auth_004f_login_nonexistent_user(self, auth_service):
        """AUTH-004f | QA Destroyer | Login non-existent user -> ValueError"""
        data = LoginRequest(email="ghost@example.com", password="anything")
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            auth_service.login(data)


# ===========================================================================
# AUTH-005: Logout and token revocation
# ===========================================================================

class TestLogout:
    """Security Auditor persona — logout revokes tokens."""

    @pytest.mark.p1
    def test_auth_005_logout_revokes_refresh(self, auth_service, registered_user):
        """AUTH-005 | Security | Logout revokes refresh token"""
        _, tokens = registered_user
        result = auth_service.logout(tokens.refresh_token)
        assert result is True

    @pytest.mark.p1
    def test_auth_005b_logout_all(self, auth_service, registered_user):
        """AUTH-005b | Security | Logout all revokes all sessions"""
        user, _ = registered_user
        # Login again to create another session
        data = LoginRequest(email="test@example.com", password="SecureP@ss123")
        auth_service.login(data)

        count = auth_service.logout_all(user.id)
        assert count >= 1

    @pytest.mark.p1
    def test_auth_005c_refresh_after_revoke_fails(self, auth_service, registered_user):
        """AUTH-005c | Security | Refresh after revocation -> ValueError"""
        _, tokens = registered_user
        auth_service.logout(tokens.refresh_token)

        with pytest.raises(ValueError):
            auth_service.refresh_tokens(tokens.refresh_token)


# ===========================================================================
# AUTH-006: Password change + reset
# ===========================================================================

class TestPasswordChange:
    """Security Auditor persona — password management."""

    @pytest.mark.p1
    def test_auth_006_change_password_success(self, auth_service, registered_user):
        """AUTH-006 | Security | Change password with correct current -> True"""
        user, _ = registered_user
        result = auth_service.change_password(user.id, "SecureP@ss123", "NewPass456!")
        assert result is True

        # Login with new password
        data = LoginRequest(email="test@example.com", password="NewPass456!")
        u2, t2 = auth_service.login(data)
        assert u2.email == "test@example.com"

    @pytest.mark.p1
    def test_auth_006b_change_password_wrong_current(self, auth_service, registered_user):
        """AUTH-006b | Security | Change password with wrong current -> ValueError"""
        user, _ = registered_user
        with pytest.raises(ValueError, match="[Cc]urrent password"):
            auth_service.change_password(user.id, "WrongCurrent", "NewPass")

    @pytest.mark.p1
    def test_auth_006c_password_reset_flow(self, auth_service, registered_user):
        """AUTH-006c | Security | Password reset token -> reset -> login"""
        reset_token = auth_service.create_password_reset_token("test@example.com")
        assert reset_token is not None

        auth_service.reset_password(reset_token, "ResetPass789!")

        # Login with new password
        data = LoginRequest(email="test@example.com", password="ResetPass789!")
        user, tokens = auth_service.login(data)
        assert user.email == "test@example.com"

    @pytest.mark.p1
    def test_auth_006d_reset_nonexistent_email(self, auth_service):
        """AUTH-006d | Security | Reset for non-existent email -> None (no leak)"""
        result = auth_service.create_password_reset_token("ghost@example.com")
        assert result is None  # Don't reveal if user exists


# ===========================================================================
# AUTH-007: Inactive user login blocked
# ===========================================================================

class TestInactiveUser:
    """Security Auditor persona — suspended/inactive users blocked."""

    @pytest.mark.p1
    def test_auth_007_suspended_user_cannot_login(self, auth_service, registered_user):
        """AUTH-007 | Security | Suspended user -> login ValueError"""
        user, _ = registered_user
        # Create an admin user for the update operation
        admin_data = UserCreate(
            email="admin@example.com",
            username="admin_test",
            password="AdminPass1!",
            full_name="Admin User",
        )
        admin, _ = auth_service.register_user(admin_data)
        admin.role = UserRole.ADMIN
        auth_service.db.update_user(admin)

        auth_service.update_user_status(user.id, UserStatus.SUSPENDED, admin.id)

        data = LoginRequest(email="test@example.com", password="SecureP@ss123")
        with pytest.raises(ValueError, match="suspended"):
            auth_service.login(data)


# ===========================================================================
# AUTH-008: Admin auto-creation
# ===========================================================================

class TestAdminAutoCreation:
    """DevOps persona — default admin exists on startup."""

    @pytest.mark.p0
    def test_auth_008_ensure_admin_called_on_init(self, user_db):
        """AUTH-008 | DevOps | _ensure_admin_exists called on service init"""
        with patch.object(AuthService, "_ensure_admin_exists") as mock_ensure:
            AuthService(db=user_db)
        mock_ensure.assert_called_once()
