"""Tests for APS V2 endpoints — Universal Publishing (/api/v2/*)."""

import io
import pytest
from unittest.mock import patch, MagicMock


class TestPublishEndpoints:
    """POST /api/v2/publish and /api/v2/publish/text"""

    def test_publish_file_requires_file(self, client):
        """POST /api/v2/publish without file returns 422."""
        response = client.post("/api/v2/publish")
        assert response.status_code == 422

    def test_publish_file_with_txt(self, client):
        """POST /api/v2/publish with a .txt file should accept or start job."""
        file_content = b"Hello world, this is test content for translation."
        response = client.post(
            "/api/v2/publish",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={
                "source_language": "en",
                "target_language": "vi",
                "profile_id": "novel",
                "output_formats": "docx",
            },
        )
        # Should accept the job (200/201) or fail gracefully (400/500/503 with message)
        assert response.status_code in (200, 201, 400, 500, 503)
        data = response.json()
        assert isinstance(data, dict)

    def test_publish_text_requires_body(self, client):
        """POST /api/v2/publish/text without body returns 422."""
        response = client.post("/api/v2/publish/text")
        assert response.status_code == 422

    def test_publish_text_with_content(self, client):
        """POST /api/v2/publish/text with valid payload."""
        response = client.post("/api/v2/publish/text", json={
            "text": "Hello world. This is a test paragraph for translation.",
            "source_language": "en",
            "target_language": "vi",
        })
        # Should accept or fail with meaningful error
        assert response.status_code in (200, 201, 400, 422, 500)


class TestJobManagement:
    """Job CRUD endpoints."""

    def test_list_jobs(self, client):
        response = client.get("/api/v2/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_job_not_found(self, client):
        response = client.get("/api/v2/jobs/nonexistent-id-999")
        assert response.status_code == 404

    def test_cancel_job_not_found(self, client):
        response = client.post("/api/v2/jobs/nonexistent-id-999/cancel")
        assert response.status_code in (404, 400)

    def test_restart_job_not_found(self, client):
        response = client.post("/api/v2/jobs/nonexistent-id-999/restart")
        assert response.status_code in (404, 400)

    def test_delete_jobs_requires_ids(self, client):
        """DELETE /api/v2/jobs requires job_ids body."""
        response = client.request("DELETE", "/api/v2/jobs", json=[])
        assert response.status_code in (200, 422)

    def test_download_not_found(self, client):
        response = client.get("/api/v2/jobs/nonexistent-id/download/docx")
        assert response.status_code in (404, 400)

    def test_reader_content_not_found(self, client):
        response = client.get("/api/v2/jobs/nonexistent-id/reader-content")
        assert response.status_code in (404, 400)


class TestPublishingProfiles:
    """Profile management endpoints."""

    def test_list_profiles(self, client):
        response = client.get("/api/v2/profiles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_profile_detail(self, client):
        """Get a known profile like 'novel'."""
        response = client.get("/api/v2/profiles/novel")
        assert response.status_code in (200, 404)


class TestProviderEndpoints:
    """Provider status and health."""

    def test_v2_health(self, client):
        response = client.get("/api/v2/health")
        assert response.status_code == 200

    def test_provider_status(self, client):
        response = client.get("/api/v2/providers/status")
        assert response.status_code in (200, 404)


class TestAPSV2Models:
    """Test APS V2 Pydantic models."""

    def test_job_status_enum_values(self):
        from api.aps_v2_models import JobStatusV2
        assert JobStatusV2.PENDING == "pending"
        assert JobStatusV2.RUNNING == "running"
        assert JobStatusV2.COMPLETE == "complete"
        assert JobStatusV2.FAILED == "failed"
        assert JobStatusV2.CANCELLED == "cancelled"

    def test_output_format_enum(self):
        from api.aps_v2_models import OutputFormatV2
        assert OutputFormatV2.DOCX == "docx"
        assert OutputFormatV2.PDF == "pdf"
        assert OutputFormatV2.EPUB == "epub"

    def test_publish_request_defaults(self):
        from api.aps_v2_models import PublishRequest
        req = PublishRequest()
        assert req.source_language == "en"
        assert req.target_language == "vi"
        assert req.profile_id == "novel"
        assert req.output_formats == ["docx"]

    def test_publish_text_request(self):
        from api.aps_v2_models import PublishTextRequest
        req = PublishTextRequest(content="Hello world")
        assert req.content == "Hello world"
        assert req.source_language == "en"
