"""Tests for security headers middleware."""

import pytest


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    def test_x_content_type_options(self, client):
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_x_xss_protection(self, client):
        response = client.get("/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        response = client.get("/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy_present(self, client):
        response = client.get("/health")
        csp = response.headers.get("content-security-policy")
        assert csp is not None
        assert "default-src" in csp

    def test_permissions_policy_present(self, client):
        response = client.get("/health")
        pp = response.headers.get("permissions-policy")
        assert pp is not None
        assert "camera=()" in pp

    def test_headers_on_json_endpoint(self, client):
        """Security headers should be on API endpoints too."""
        response = client.get("/api/system/info")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"

    def test_headers_on_error_response(self, client):
        """Security headers should be on 404 responses too."""
        response = client.get("/nonexistent-endpoint")
        assert response.headers.get("x-content-type-options") == "nosniff"
