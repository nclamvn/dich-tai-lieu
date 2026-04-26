"""Tests for authentication endpoints (/api/auth/*)."""

import pytest


class TestAuthRegister:
    """POST /api/auth/register"""

    def test_register_success(self, client, register_payload):
        response = client.post("/api/auth/register", json=register_payload)
        assert response.status_code == 201
        data = response.json()
        assert "user" in data or "tokens" in data

    def test_register_duplicate_email(self, client, register_payload):
        # First registration
        client.post("/api/auth/register", json=register_payload)
        # Second attempt with same email
        response = client.post("/api/auth/register", json=register_payload)
        assert response.status_code in (400, 409, 422)

    def test_register_weak_password_too_short(self, client):
        payload = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "Short1!",  # < 12 chars
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_password_no_uppercase(self, client):
        payload = {
            "email": "weak2@example.com",
            "username": "weakuser2",
            "password": "alllowercase123!",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_password_no_digit(self, client):
        payload = {
            "email": "weak3@example.com",
            "username": "weakuser3",
            "password": "NoDigitsHere!!AA",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_password_no_special_char(self, client):
        payload = {
            "email": "weak4@example.com",
            "username": "weakuser4",
            "password": "NoSpecialChar123A",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        payload = {
            "email": "not-an-email",
            "username": "badmail",
            "password": "SecurePass123!@",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422


class TestAuthLogin:
    """POST /api/auth/login"""

    def test_login_invalid_credentials(self, client):
        payload = {
            "email": "nonexistent@example.com",
            "password": "WrongPass123!@",
        }
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code in (401, 404)

    def test_login_success(self, client, register_payload, test_password):
        # Register first
        client.post("/api/auth/register", json=register_payload)
        # Login
        response = client.post("/api/auth/login", json={
            "email": register_payload["email"],
            "password": test_password,
        })
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data or "access_token" in data

    def test_login_returns_token_fields(self, client, register_payload, test_password):
        client.post("/api/auth/register", json=register_payload)
        response = client.post("/api/auth/login", json={
            "email": register_payload["email"],
            "password": test_password,
        })
        data = response.json()
        tokens = data.get("tokens", data)
        assert "access_token" in tokens
        assert "refresh_token" in tokens


class TestAuthSession:
    """Session-related auth endpoints."""

    def test_session_check_no_auth(self, client):
        """GET /api/auth/session without auth should indicate no session."""
        response = client.get("/api/auth/session")
        # May return 200 with authenticated=false or 401
        assert response.status_code in (200, 401)

    def test_auth_me_no_token(self, client):
        """GET /api/auth/me without token should fail."""
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)
