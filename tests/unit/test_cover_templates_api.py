"""The public cover-template catalog endpoint the front-end picker consumes."""


def test_cover_templates_endpoint_is_public_and_complete():
    from fastapi.testclient import TestClient

    import api.main as m

    client = TestClient(m.app)
    resp = client.get("/api/cover-templates")
    assert resp.status_code == 200

    templates = resp.json()["templates"]
    ids = {t["id"] for t in templates}
    assert len(ids) == 12
    assert {"classic", "noir", "emblem", "academic"} <= ids
    for t in templates:
        assert t["name"] and t["category"] and t["description"]
