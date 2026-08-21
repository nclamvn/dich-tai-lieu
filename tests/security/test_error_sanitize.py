"""500 responses never leak raised exception strings (beta hardening).

Many handlers did ``raise HTTPException(500, detail=f"...: {str(e)}")``, exposing
paths / DB errors to clients. A single sanitizing HTTPException handler
(``api.main._http_exception_handler``) replaces any 500 body with a generic
message + an error id (the real detail is logged server-side), while <500 and the
other 5xx (503/507 with deliberately friendly messages) keep their text.
"""

import asyncio
import json

from starlette.exceptions import HTTPException as HTTPExc
from starlette.requests import Request

from api.main import _http_exception_handler

_GENERIC = "An internal error occurred. Please try again or contact support."


def _request():
    return Request({"type": "http", "method": "GET", "path": "/x", "headers": []})


def _handle(status, detail):
    resp = asyncio.run(_http_exception_handler(_request(), HTTPExc(status_code=status, detail=detail)))
    return resp, resp.body.decode()


def test_500_is_sanitized_and_does_not_leak():
    resp, text = _handle(500, "/etc/app/secret.db: OperationalError near line 42")
    assert resp.status_code == 500
    assert "secret" not in text and "OperationalError" not in text and "line 42" not in text
    body = json.loads(text)
    assert body["detail"] == _GENERIC
    assert body.get("error_id")


def test_4xx_detail_is_preserved():
    resp, text = _handle(400, "Invalid file type. Allowed: .pdf, .docx")
    assert resp.status_code == 400
    assert "Invalid file type" in text


def test_other_5xx_message_is_preserved():
    # 507 disk-full carries a deliberately friendly, non-leaking message.
    resp, text = _handle(507, "Server disk is full. Please contact admin.")
    assert resp.status_code == 507
    assert "disk is full" in text
