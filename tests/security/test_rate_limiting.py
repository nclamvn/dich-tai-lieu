"""Rate limiting — enforced in production, off in dev/tests (beta hardening).

The shared limiter (``api/rate_limiter.py``) is created disabled outside
production, so the test suite and local runs are never throttled; a live
``RATE_LIMIT_ENABLED`` env var overrides. When enabled, a per-route
``@limiter.limit`` + ``SlowAPIMiddleware`` returns HTTP 429 past the limit.
"""

import inspect

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.rate_limiter import _rate_limit_enabled, limiter, rate_limit_exceeded_handler


def _mini_app(enabled: bool) -> FastAPI:
    lim = Limiter(key_func=get_remote_address, enabled=enabled)
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/x")
    @lim.limit("3/minute")
    async def x(request: Request):  # slowapi requires the request param
        return {"ok": True}

    return app


# --------------------------------------------------------------------------- #
# Default-safe: off unless production
# --------------------------------------------------------------------------- #
def test_shared_limiter_disabled_by_default():
    # In the test/dev environment the app-wide limiter must be inert.
    assert limiter.enabled is False


def test_enabled_flag_follows_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    assert _rate_limit_enabled() is True
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    assert _rate_limit_enabled() is False
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)


# --------------------------------------------------------------------------- #
# Enforcement mechanism
# --------------------------------------------------------------------------- #
def test_429_past_the_limit_when_enabled():
    client = TestClient(_mini_app(enabled=True))
    codes = [client.get("/x").status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429


def test_429_body_shape():
    client = TestClient(_mini_app(enabled=True))
    for _ in range(3):
        client.get("/x")
    resp = client.get("/x")
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After")
    body = resp.json()
    assert body.get("error") == "rate_limit_exceeded"


def test_no_throttle_when_disabled():
    client = TestClient(_mini_app(enabled=False))
    assert all(client.get("/x").status_code == 200 for _ in range(10))


# --------------------------------------------------------------------------- #
# Wiring: the throttled endpoints keep the request param slowapi needs
# --------------------------------------------------------------------------- #
def test_throttled_endpoints_accept_request_param():
    from api.auth_router import login, register
    from api.routes.uploads import upload_file

    for fn in (login, register, upload_file):
        target = getattr(fn, "__wrapped__", fn)
        params = inspect.signature(target).parameters
        assert "request" in params, f"{fn.__name__} lost its request param (breaks slowapi)"
