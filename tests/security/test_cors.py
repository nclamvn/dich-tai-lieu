"""Tests for CORS configuration."""

import pytest


class TestCORSConfiguration:
    """Verify CORS behavior."""

    def test_configured_origin_allowed(self, client):
        """Request from a configured dev origin should include CORS headers."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3001"},
        )
        acl = response.headers.get("access-control-allow-origin")
        assert acl == "http://localhost:3001"

    def test_unknown_origin_not_reflected(self, client):
        """Request from an unknown origin should NOT reflect it."""
        response = client.get(
            "/health",
            headers={"Origin": "http://evil.com"},
        )
        acl = response.headers.get("access-control-allow-origin")
        assert acl != "http://evil.com"

    def test_preflight_returns_methods(self, client):
        """OPTIONS preflight should return allowed methods."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
            },
        )
        methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in methods

    def test_allow_headers_not_wildcard(self, client):
        """allow-headers should NOT be '*' — we use a whitelist now."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        allow_headers = response.headers.get("access-control-allow-headers", "")
        # Should be specific headers, not wildcard
        assert allow_headers != "*"
