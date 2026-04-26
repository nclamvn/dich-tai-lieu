"""Shared fixtures for API endpoint tests."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root on path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test env vars before importing app
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SECURITY_MODE", "development")
os.environ.setdefault("SESSION_AUTH_ENABLED", "false")


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient for the main app."""
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.fixture
def test_password():
    """A password that meets the new complexity requirements."""
    return "SecurePass123!@"


@pytest.fixture
def register_payload(test_password):
    """Valid registration payload."""
    import uuid
    unique = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{unique}@example.com",
        "username": f"testuser_{unique}",
        "password": test_password,
        "full_name": "Test User",
    }
