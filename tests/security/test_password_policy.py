"""Tests for password complexity validation."""

import pytest
from pydantic import ValidationError
from core.auth.models import UserCreate, PasswordChange, PasswordResetConfirm


class TestPasswordPolicyUserCreate:
    """Password validation on UserCreate model."""

    def test_valid_password_accepted(self):
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123!",
        )
        assert user.password == "SecurePass123!"

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Short1!",
            )
        assert "at least 12 characters" in str(exc_info.value).lower() or "string_too_short" in str(exc_info.value)

    def test_no_uppercase_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="alllowercase123!",
            )
        assert "uppercase" in str(exc_info.value).lower()

    def test_no_lowercase_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="ALLUPPERCASE123!",
            )
        assert "lowercase" in str(exc_info.value).lower()

    def test_no_digit_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="NoDigitsHere!!AA",
            )
        assert "digit" in str(exc_info.value).lower()

    def test_no_special_char_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="NoSpecialChar123A",
            )
        assert "special" in str(exc_info.value).lower()


class TestPasswordPolicyPasswordChange:
    """Password validation on PasswordChange model."""

    def test_valid_new_password(self):
        pc = PasswordChange(
            current_password="oldpass",
            new_password="NewSecure123!@",
        )
        assert pc.new_password == "NewSecure123!@"

    def test_weak_new_password_rejected(self):
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="oldpass",
                new_password="weak",
            )


class TestPasswordPolicyPasswordReset:
    """Password validation on PasswordResetConfirm model."""

    def test_valid_reset_password(self):
        pr = PasswordResetConfirm(
            token="some-reset-token",
            new_password="ResetPass123!@",
        )
        assert pr.new_password == "ResetPass123!@"

    def test_weak_reset_password_rejected(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                token="some-reset-token",
                new_password="nouppercase123!",
            )
