"""Tests for Author Mode endpoints (/api/author/*)."""

import pytest


class TestAuthorPropose:
    """Book proposal endpoints."""

    def test_propose_requires_body(self, client):
        response = client.post("/api/author/propose")
        assert response.status_code == 422

    def test_propose_with_topic(self, client):
        response = client.post("/api/author/propose", json={
            "topic": "AI in healthcare",
            "style": "academic",
            "num_chapters": 5,
        })
        # May succeed or fail due to no API key, but shouldn't 404
        assert response.status_code != 404

    def test_brainstorm_requires_body(self, client):
        response = client.post("/api/author/brainstorm")
        assert response.status_code == 422

    def test_critique_requires_body(self, client):
        response = client.post("/api/author/critique")
        assert response.status_code == 422


class TestAuthorProjects:
    """Project CRUD endpoints."""

    def test_create_project_requires_body(self, client):
        response = client.post("/api/author/projects")
        assert response.status_code == 422

    def test_list_projects_for_author(self, client):
        response = client.get("/api/author/projects/test-author-id")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_styles(self, client):
        """GET /api/author/styles should return available writing styles."""
        response = client.get("/api/author/styles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestAuthorMemory:
    """Character/event/plot memory endpoints."""

    def test_add_character_requires_body(self, client):
        response = client.post("/api/author/memory/character")
        assert response.status_code == 422

    def test_get_characters(self, client):
        response = client.get("/api/author/memory/characters/test-author/test-project")
        assert response.status_code in (200, 404)

    def test_add_event_requires_body(self, client):
        response = client.post("/api/author/memory/event")
        assert response.status_code == 422

    def test_get_timeline(self, client):
        response = client.get("/api/author/memory/timeline/test-author/test-project")
        assert response.status_code in (200, 404)

    def test_search_memory_requires_body(self, client):
        response = client.post("/api/author/memory/search")
        assert response.status_code == 422


class TestAuthorExport:
    """Export endpoints."""

    def test_export_glossary_requires_body(self, client):
        response = client.post("/api/author/export/glossary")
        assert response.status_code == 422
