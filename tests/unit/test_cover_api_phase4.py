"""Phase 4 API surface for the cover picker: preview + upload endpoints and the
request-model fields the front-end sends. No API key; uses TestClient in dev
mode (auth disabled)."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="module")
def client():
    import api.main as m

    return TestClient(m.app)


def _png_bytes(w=60, h=96, color="#123f39"):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    buf.seek(0)
    return buf


def test_catalog_lists_twelve(client):
    r = client.get("/api/cover-templates")
    assert r.status_code == 200
    assert len(r.json()["templates"]) == 12


def test_catalog_includes_preview_version(client):
    # Cache-busting fingerprint for preview URLs: stable within a process,
    # changes when the bundled fonts / template registry change.
    r = client.get("/api/cover-templates")
    v = r.json().get("preview_version")
    assert isinstance(v, str) and len(v) >= 6
    assert client.get("/api/cover-templates").json()["preview_version"] == v


def test_preview_returns_png(client):
    r = client.get("/api/cover-templates/noir/preview")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 1000


def test_preview_unknown_is_404(client):
    assert client.get("/api/cover-templates/nope/preview").status_code == 404


def test_cover_upload_stores_and_returns_path(client):
    r = client.post("/api/cover-upload", files={"file": ("my.png", _png_bytes(), "image/png")})
    assert r.status_code == 200
    path = r.json()["path"]
    assert path.endswith(".png")
    assert "uploads/covers" in path.replace("\\", "/")


def test_cover_upload_rejects_non_image(client):
    r = client.post("/api/cover-upload", files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")})
    assert r.status_code == 400


def test_cover_upload_rejects_empty(client):
    r = client.post("/api/cover-upload", files={"file": ("e.png", io.BytesIO(b""), "image/png")})
    assert r.status_code == 400


def test_publish_text_request_carries_cover_fields():
    from api.aps_v2_models import PublishTextRequest

    r = PublishTextRequest(content="Xin chào", cover_template="noir", cover_image="/x/covers/a.png")
    assert r.cover_template == "noir"
    assert r.cover_image == "/x/covers/a.png"
    # defaults are None (no cover) so existing callers are unaffected
    base = PublishTextRequest(content="Xin chào")
    assert base.cover_template is None and base.cover_image is None
