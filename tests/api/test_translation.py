"""Tests for translation endpoints (/api/v2/*)."""

import io
import pytest


class TestTranslationEndpoints:
    """APS V2 translation routes."""

    def test_list_jobs_returns_200(self, client):
        response = client.get("/api/v2/jobs")
        assert response.status_code == 200

    def test_list_jobs_returns_list(self, client):
        response = client.get("/api/v2/jobs")
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_job_not_found(self, client):
        response = client.get("/api/v2/jobs/nonexistent-job-id")
        assert response.status_code == 404

    def test_cancel_job_not_found(self, client):
        response = client.post("/api/v2/jobs/nonexistent-job-id/cancel")
        assert response.status_code in (404, 400)

    def test_publish_text_no_body(self, client):
        response = client.post("/api/v2/publish/text")
        assert response.status_code == 422

    def test_publish_text_requires_content(self, client):
        response = client.post("/api/v2/publish/text", json={})
        assert response.status_code == 422

    def test_publish_requires_file(self, client):
        response = client.post("/api/v2/publish")
        assert response.status_code == 422

    def test_cancel_nonexistent_job(self, client):
        response = client.post("/api/v2/jobs/fake-id-123/cancel")
        assert response.status_code in (404, 400, 200)
