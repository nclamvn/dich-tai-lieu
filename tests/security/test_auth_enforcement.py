"""P0 security invariants (TIP-P0) for the limited-public beta.

Two guarantees, locked with tests:
1. Production refuses to boot with insecure / incomplete security config.
2. ``get_current_user_id`` ENFORCES auth (HTTP 401) when auth is enabled and
   never silently falls through to ``"default_user"`` (the old fail-open).
"""

import secrets

import pytest
from fastapi import HTTPException

from config.settings import Settings

SECURE = secrets.token_hex(32)  # 64 hex chars, satisfies the >= 32 rule


# --------------------------------------------------------------------------- #
# 1. Production boot guard
# --------------------------------------------------------------------------- #
def _prod(**overrides):
    cfg = dict(
        security_mode="production",
        session_secret=SECURE,
        session_auth_enabled=True,
        cors_origins="https://app.example.com",
        jwt_secret_key=SECURE,
    )
    cfg.update(overrides)
    return Settings(**cfg)


def test_production_accepts_secure_config():
    assert _prod().security_mode == "production"


def test_production_rejects_insecure_session_secret():
    with pytest.raises(ValueError):
        _prod(session_secret="INSECURE-DEV-SECRET-CHANGE-IN-PRODUCTION")


def test_production_rejects_short_secret():
    with pytest.raises(ValueError):
        _prod(session_secret="tooshort")


def test_production_rejects_auth_disabled():
    with pytest.raises(ValueError):
        _prod(session_auth_enabled=False, api_key_auth_enabled=False)


def test_production_rejects_missing_cors():
    with pytest.raises(ValueError):
        _prod(cors_origins="")


def test_production_rejects_wildcard_cors():
    # allow_credentials=True + "*" is a real misconfiguration.
    with pytest.raises(ValueError):
        _prod(cors_origins="*")
    with pytest.raises(ValueError):
        _prod(cors_origins="https://ok.example.com,*")


def test_production_rejects_short_or_placeholder_csrf_secret():
    with pytest.raises(ValueError):
        _prod(csrf_enabled=True, csrf_secret_key="CHANGE_ME")
    with pytest.raises(ValueError):
        _prod(csrf_enabled=True, csrf_secret_key="tooshort")


def test_production_rejects_missing_jwt_secret():
    # Unset JWT_SECRET_KEY = random per-process secret: every restart
    # invalidates all JWTs and workers sign with different keys.
    with pytest.raises(ValueError):
        _prod(jwt_secret_key="")


def test_production_rejects_short_or_placeholder_jwt_secret():
    with pytest.raises(ValueError):
        _prod(jwt_secret_key="tooshort")
    with pytest.raises(ValueError):
        _prod(jwt_secret_key="change-me-64-random-chars")


def test_production_accepts_secure_csrf_secret():
    assert _prod(csrf_enabled=True, csrf_secret_key=SECURE).security_mode == "production"


def test_development_allows_defaults():
    assert Settings(security_mode="development").security_mode == "development"


# --------------------------------------------------------------------------- #
# 2. No auth fail-open in get_current_user_id
# --------------------------------------------------------------------------- #
@pytest.fixture
def set_auth(monkeypatch):
    class _S:
        def __init__(self, enabled):
            self.session_auth_enabled = enabled

    def _set(enabled):
        import config.settings as cs

        monkeypatch.setattr(cs, "get_settings", lambda: _S(enabled))

    return _set


def _mock_manager(monkeypatch, session=None, raises=False):
    import api.security as sec

    class _Mgr:
        def validate_session(self, token):
            if raises:
                raise ValueError("bad token")
            return session

    monkeypatch.setattr(sec, "security_manager", _Mgr(), raising=False)


async def test_auth_disabled_returns_default_user(set_auth):
    set_auth(False)
    from api.deps import get_current_user_id

    assert await get_current_user_id(None) == "default_user"
    assert await get_current_user_id("ignored-token") == "default_user"


async def test_auth_enabled_missing_token_is_401(set_auth):
    set_auth(True)
    from api.deps import get_current_user_id

    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(None)
    assert exc.value.status_code == 401


async def test_auth_enabled_invalid_token_is_401(set_auth, monkeypatch):
    set_auth(True)
    _mock_manager(monkeypatch, raises=True)
    from api.deps import get_current_user_id

    with pytest.raises(HTTPException) as exc:
        await get_current_user_id("bad-token")
    assert exc.value.status_code == 401


async def test_auth_enabled_valid_token_returns_user(set_auth, monkeypatch):
    set_auth(True)

    class _Session:
        user_id = "user-42"

    _mock_manager(monkeypatch, session=_Session())
    from api.deps import get_current_user_id

    assert await get_current_user_id("good-token") == "user-42"
