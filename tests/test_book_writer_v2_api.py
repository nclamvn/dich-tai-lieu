"""
Tests for Book Writer v2.0 API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Get test client."""
    from api.main import app
    return TestClient(app)


class TestBookWriterV2API:
    """Tests for Book Writer v2.0 API."""

    def test_preview_structure(self, client):
        """Test structure preview endpoint."""
        response = client.post(
            "/api/v2/books-v2/preview-structure",
            params={"target_pages": 300},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_pages"] == 300
        assert "num_parts" in data
        assert "total_chapters" in data
        assert "total_sections" in data
        assert "estimated_time_minutes" in data
        assert data["num_parts"] >= 1
        assert data["total_sections"] > 0

    def test_preview_structure_100_pages(self, client):
        response = client.post(
            "/api/v2/books-v2/preview-structure",
            params={"target_pages": 100},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_words"] > 0

    def test_preview_structure_invalid(self, client):
        response = client.post(
            "/api/v2/books-v2/preview-structure",
            params={"target_pages": 10},  # Below minimum 50
        )
        assert response.status_code == 422

    def test_create_book(self, client):
        """Test book creation endpoint."""
        response = client.post(
            "/api/v2/books-v2/",
            json={
                "title": "Test Book",
                "description": "A test book about testing software",
                "target_pages": 100,
                "genre": "technical",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] in ["created", "analyzing"]

    def test_create_book_validation(self, client):
        """Test creation with invalid data."""
        response = client.post(
            "/api/v2/books-v2/",
            json={
                "title": "",
                "description": "short",
                "target_pages": 10,
            },
        )
        assert response.status_code == 422

    def test_list_books(self, client):
        """Test book listing endpoint."""
        response = client.get("/api/v2/books-v2/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_nonexistent_book(self, client):
        """Test getting non-existent book."""
        response = client.get("/api/v2/books-v2/nonexistent-id-12345")
        assert response.status_code == 404

    def test_download_invalid_format(self, client):
        """Test download with invalid format."""
        response = client.get("/api/v2/books-v2/test-id/download/invalid")
        assert response.status_code == 400

    def test_download_nonexistent(self, client):
        """Test download for non-existent book."""
        response = client.get("/api/v2/books-v2/nonexistent/download/docx")
        assert response.status_code == 404

    def test_pause_nonexistent(self, client):
        """Test pausing non-existent project."""
        response = client.post("/api/v2/books-v2/nonexistent/pause")
        assert response.status_code == 400

    def test_delete_nonexistent(self, client):
        """Test deleting non-existent project."""
        response = client.delete("/api/v2/books-v2/nonexistent-id-12345")
        assert response.status_code == 404

    def test_content_nonexistent(self, client):
        """Test getting content for non-existent book."""
        response = client.get("/api/v2/books-v2/nonexistent/content")
        assert response.status_code == 404
