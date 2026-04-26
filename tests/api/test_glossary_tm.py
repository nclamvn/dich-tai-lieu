"""Tests for glossary and translation memory endpoints."""

import pytest


class TestGlossaryEndpoints:
    """Glossary management routes (/api/glossary/*)."""

    # Note: glossary router mounted at /api/glossary with its own /api/glossary prefix
    GLOSSARY_BASE = "/api/glossary/api/glossary"

    def test_glossary_list(self, client):
        response = client.get(f"{self.GLOSSARY_BASE}/")
        assert response.status_code == 200

    def test_glossary_list_returns_data(self, client):
        response = client.get(f"{self.GLOSSARY_BASE}/")
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_glossary_domains(self, client):
        response = client.get(f"{self.GLOSSARY_BASE}/domains")
        assert response.status_code == 200

    def test_glossary_languages(self, client):
        response = client.get(f"{self.GLOSSARY_BASE}/languages")
        assert response.status_code == 200

    def test_glossary_get_not_found(self, client):
        response = client.get(f"{self.GLOSSARY_BASE}/nonexistent-id")
        assert response.status_code in (404, 400)

    def test_glossary_create(self, client):
        payload = {
            "name": "test-glossary",
            "source_lang": "en",
            "target_lang": "vi",
        }
        response = client.post(f"{self.GLOSSARY_BASE}/", json=payload)
        assert response.status_code in (200, 201)

    def test_glossary_delete_not_found(self, client):
        response = client.delete(f"{self.GLOSSARY_BASE}/nonexistent-id")
        assert response.status_code in (404, 400, 200)


class TestTMEndpoints:
    """Translation Memory routes (/api/tm/*)."""

    def test_tm_list(self, client):
        response = client.get("/api/tm/")
        assert response.status_code == 200

    def test_tm_list_returns_data(self, client):
        response = client.get("/api/tm/")
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_tm_get_not_found(self, client):
        response = client.get("/api/tm/nonexistent-id")
        assert response.status_code in (404, 400)

    def test_tm_create(self, client):
        payload = {
            "name": "test-tm",
            "source_lang": "en",
            "target_lang": "vi",
        }
        response = client.post("/api/tm/", json=payload)
        assert response.status_code in (200, 201)

    def test_tm_delete_not_found(self, client):
        response = client.delete("/api/tm/nonexistent-id")
        assert response.status_code in (404, 400, 200)

    def test_tm_lookup(self, client):
        payload = {
            "text": "Hello world",
            "source_lang": "en",
            "target_lang": "vi",
        }
        response = client.post("/api/tm/lookup", json=payload)
        assert response.status_code in (200, 422)
