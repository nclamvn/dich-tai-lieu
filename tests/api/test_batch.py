"""Tests for batch processing endpoints (/api/v2/batch/*)."""

import pytest


class TestBatchEndpoints:
    """Batch processing routes."""

    def test_batch_list_returns_200(self, client):
        response = client.get("/api/v2/batch/")
        assert response.status_code == 200

    def test_batch_list_returns_data(self, client):
        response = client.get("/api/v2/batch/")
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_batch_status_not_found(self, client):
        response = client.get("/api/v2/batch/nonexistent-batch/status")
        assert response.status_code in (404, 400)

    def test_batch_create_no_files(self, client):
        response = client.post("/api/v2/batch/create")
        assert response.status_code == 422

    def test_batch_cancel_not_found(self, client):
        response = client.post("/api/v2/batch/nonexistent-batch/cancel")
        assert response.status_code in (404, 400)
