"""
Unit tests for api/routes/batch_legacy.py — batch queue lifecycle.
"""
import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from api.routes import batch_legacy


class TestBatchLegacy:
    """Tests for the self-contained legacy batch queue."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_batch_state(self):
        """Reset module-level state before each test."""
        batch_legacy.batch_jobs_db.clear()
        batch_legacy.batch_queue_running = False
        yield
        batch_legacy.batch_jobs_db.clear()
        batch_legacy.batch_queue_running = False

    # --- GET /api/batch/status ---

    def test_status_empty(self, client):
        resp = client.get("/api/batch/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"]["total"] == 0
        assert data["is_running"] is False
        assert data["pages"]["progress"] == 0

    def test_status_with_jobs(self, client):
        batch_legacy.batch_jobs_db["j1"] = {
            "status": "pending", "total_pages": 10, "completed_pages": 0, "cost": 0
        }
        batch_legacy.batch_jobs_db["j2"] = {
            "status": "completed", "total_pages": 5, "completed_pages": 5, "cost": 0.02
        }
        resp = client.get("/api/batch/status")
        data = resp.json()
        assert data["jobs"]["total"] == 2
        assert data["jobs"]["pending"] == 1
        assert data["jobs"]["completed"] == 1
        assert data["pages"]["total"] == 15

    # --- POST /api/batch/upload ---

    def _make_pdf_file(self, name="test.pdf", size=1024):
        return ("files", (name, io.BytesIO(b"%PDF" + b"x" * size), "application/pdf"))

    def test_upload_pdf_files(self, client):
        files = [self._make_pdf_file("a.pdf"), self._make_pdf_file("b.pdf")]
        resp = client.post("/api/batch/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["jobs_created"] == 2
        assert len(batch_legacy.batch_jobs_db) == 2

    def test_upload_non_pdf_skipped(self, client):
        files = [("files", ("readme.txt", io.BytesIO(b"hello"), "text/plain"))]
        resp = client.post("/api/batch/upload", files=files)
        assert resp.status_code == 200
        assert resp.json()["jobs_created"] == 0

    def test_upload_with_mode(self, client):
        files = [self._make_pdf_file()]
        resp = client.post("/api/batch/upload?mode=quality", files=files)
        data = resp.json()
        assert data["jobs_created"] == 1
        job = list(batch_legacy.batch_jobs_db.values())[0]
        assert job["settings"]["mode"] == "quality"

    # --- GET /api/batch/jobs ---

    def test_list_empty(self, client):
        resp = client.get("/api/batch/jobs")
        assert resp.json()["jobs"] == []

    def test_list_sorted(self, client):
        batch_legacy.batch_jobs_db["a"] = {"status": "completed", "priority": 1}
        batch_legacy.batch_jobs_db["b"] = {"status": "processing", "priority": 2}
        batch_legacy.batch_jobs_db["c"] = {"status": "pending", "priority": 3}
        resp = client.get("/api/batch/jobs")
        statuses = [j["status"] for j in resp.json()["jobs"]]
        assert statuses == ["processing", "pending", "completed"]

    # --- GET /api/batch/jobs/{job_id} ---

    def test_get_job_found(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "pending"}
        resp = client.get("/api/batch/jobs/j1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "j1"

    def test_get_job_not_found(self, client):
        resp = client.get("/api/batch/jobs/nonexistent")
        assert resp.status_code == 404

    # --- PATCH /api/batch/jobs/{job_id} ---

    def test_update_status(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "pending", "priority": 1, "updated_at": ""}
        resp = client.patch("/api/batch/jobs/j1?status=paused")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_update_priority(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "pending", "priority": 1, "updated_at": ""}
        resp = client.patch("/api/batch/jobs/j1?priority=5")
        assert resp.status_code == 200
        assert resp.json()["priority"] == 5

    def test_update_not_found(self, client):
        resp = client.patch("/api/batch/jobs/nope?status=paused")
        assert resp.status_code == 404

    # --- DELETE /api/batch/jobs/{job_id} ---

    def test_delete_pending_job(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "pending"}
        resp = client.delete("/api/batch/jobs/j1")
        assert resp.status_code == 200
        assert "j1" not in batch_legacy.batch_jobs_db

    def test_delete_processing_job_cancels(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "processing"}
        resp = client.delete("/api/batch/jobs/j1")
        assert resp.status_code == 200
        assert batch_legacy.batch_jobs_db["j1"]["status"] == "cancelled"

    def test_delete_not_found(self, client):
        resp = client.delete("/api/batch/jobs/nope")
        assert resp.status_code == 404

    # --- POST /api/batch/jobs/{job_id}/retry ---

    def test_retry_failed_job(self, client):
        batch_legacy.batch_jobs_db["j1"] = {
            "id": "j1", "status": "failed", "progress": 50,
            "completed_pages": 5, "error": "timeout", "updated_at": ""
        }
        resp = client.post("/api/batch/jobs/j1/retry")
        assert resp.status_code == 200
        j = resp.json()
        assert j["status"] == "pending"
        assert j["progress"] == 0
        assert j["error"] is None

    def test_retry_cancelled_job(self, client):
        batch_legacy.batch_jobs_db["j1"] = {
            "id": "j1", "status": "cancelled", "progress": 0,
            "completed_pages": 0, "error": None, "updated_at": ""
        }
        resp = client.post("/api/batch/jobs/j1/retry")
        assert resp.status_code == 200

    def test_retry_pending_job_rejected(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"id": "j1", "status": "pending"}
        resp = client.post("/api/batch/jobs/j1/retry")
        assert resp.status_code == 400

    def test_retry_not_found(self, client):
        resp = client.post("/api/batch/jobs/nope/retry")
        assert resp.status_code == 404

    # --- POST /api/batch/queue/start ---

    def test_start_queue(self, client):
        with patch.object(batch_legacy, "process_batch_queue", return_value=None):
            resp = client.post("/api/batch/queue/start")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_start_queue_already_running(self, client):
        batch_legacy.batch_queue_running = True
        resp = client.post("/api/batch/queue/start")
        assert resp.json()["success"] is False

    # --- POST /api/batch/queue/pause ---

    def test_pause_queue(self, client):
        batch_legacy.batch_queue_running = True
        resp = client.post("/api/batch/queue/pause")
        assert resp.status_code == 200
        assert batch_legacy.batch_queue_running is False

    # --- POST /api/batch/queue/clear ---

    def test_clear_completed(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"status": "completed"}
        batch_legacy.batch_jobs_db["j2"] = {"status": "cancelled"}
        batch_legacy.batch_jobs_db["j3"] = {"status": "pending"}
        resp = client.post("/api/batch/queue/clear")
        assert resp.status_code == 200
        assert resp.json()["cleared"] == 2
        assert "j3" in batch_legacy.batch_jobs_db
        assert "j1" not in batch_legacy.batch_jobs_db

    def test_clear_nothing(self, client):
        batch_legacy.batch_jobs_db["j1"] = {"status": "pending"}
        resp = client.post("/api/batch/queue/clear")
        assert resp.json()["cleared"] == 0
