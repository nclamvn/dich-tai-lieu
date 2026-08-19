"""Production observability: request-ID + structured access logging middleware."""

import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api.middleware.request_context import REQUEST_ID_HEADER, RequestContextMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping(request: Request):
        return {"request_id": request.state.request_id}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return TestClient(app, raise_server_exceptions=False)


def test_response_has_request_id_header():
    resp = _client().get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get(REQUEST_ID_HEADER)


def test_state_request_id_matches_header():
    resp = _client().get("/ping")
    assert resp.json()["request_id"] == resp.headers.get(REQUEST_ID_HEADER)


def test_inbound_request_id_is_propagated():
    resp = _client().get("/ping", headers={REQUEST_ID_HEADER: "trace-123"})
    assert resp.headers.get(REQUEST_ID_HEADER) == "trace-123"


def test_access_log_line_emitted(caplog):
    with caplog.at_level(logging.INFO, logger="api.request"):
        _client().get("/ping")
    messages = [r.getMessage() for r in caplog.records if r.name == "api.request"]
    assert any("status=200" in m and "path=/ping" in m for m in messages)


def test_error_is_logged_and_reraised(caplog):
    with caplog.at_level(logging.ERROR, logger="api.request"):
        resp = _client().get("/boom")
    assert resp.status_code == 500
    errors = [r.getMessage() for r in caplog.records if r.name == "api.request"]
    assert any("request.error" in m for m in errors)
