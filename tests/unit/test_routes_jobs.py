"""
Unit tests for api/routes/jobs.py — job CRUD, progress, cancel.
"""
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from core.job_queue import JobStatus


class TestJobProgress:
    """Test GET /api/jobs/{job_id}/progress — step generation for various states."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _make_job(self, status="pending", progress=0.0, metadata=None):
        job = MagicMock()
        job.job_id = "test-123"
        job.job_name = "Test Job"
        job.status = status
        job.progress = progress
        job.metadata = metadata or {}
        job.output_file = "output.docx"
        job.output_format = "docx"
        job.started_at = time.time() - 60 if status != "pending" else None
        job.completed_at = time.time() if status == "completed" else None
        job.total_chunks = 10
        job.completed_chunks = int(progress * 10)
        return job

    def test_progress_pending(self, client):
        job = self._make_job(status=JobStatus.PENDING)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["progress_percent"] == 0
        assert all(s["status"] == "pending" for s in data["steps"])

    def test_progress_completed(self, client):
        job = self._make_job(status=JobStatus.COMPLETED, progress=1.0)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress_percent"] == 100
        assert all(s["status"] == "completed" for s in data["steps"])
        assert data["output_file"] is not None

    def test_progress_failed(self, client):
        job = self._make_job(status=JobStatus.FAILED, progress=0.5)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        data = resp.json()
        assert data["status"] == "failed"
        assert any(s["status"] == "failed" for s in data["steps"])

    def test_progress_running(self, client):
        job = self._make_job(status=JobStatus.RUNNING, progress=0.5)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        data = resp.json()
        assert data["status"] == "running"
        assert any(s["status"] == "in_progress" for s in data["steps"])

    def test_progress_with_ocr_step(self, client):
        job = self._make_job(
            status=JobStatus.RUNNING, progress=0.3,
            metadata={"enable_ocr": True}
        )
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        data = resp.json()
        step_names = [s["name"] for s in data["steps"]]
        assert "ocr" in step_names

    def test_progress_with_omml_step(self, client):
        job = self._make_job(
            status=JobStatus.COMPLETED, progress=1.0,
            metadata={"equation_rendering_mode": "omml", "output_formats_requested": ["docx"]}
        )
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        step_names = [s["name"] for s in resp.json()["steps"]]
        assert "omml_equations" in step_names

    def test_progress_with_pdf_export_step(self, client):
        job = self._make_job(
            status=JobStatus.COMPLETED, progress=1.0,
            metadata={"output_formats_requested": ["docx", "pdf"]}
        )
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")

        step_names = [s["name"] for s in resp.json()["steps"]]
        assert "pdf_export" in step_names

    def test_progress_not_found(self, client):
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.get("/api/jobs/nope/progress")
        assert resp.status_code == 404


class TestCreateJob:
    """Test POST /api/jobs — UI v1.1 layout mode mapping."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _make_payload(self, tmp_path, **overrides):
        f = tmp_path / "input.txt"
        f.write_text("Test document content")
        payload = {
            "job_name": "Test",
            "input_file": str(f),
            "output_file": str(tmp_path / "out.docx"),
            "source_lang": "en",
            "target_lang": "vi",
        }
        payload.update(overrides)
        return payload

    def test_create_basic_layout(self, client, tmp_path):
        payload = self._make_payload(tmp_path, ui_layout_mode="basic")

        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.job_name = "Test"
        mock_job.status = "pending"
        mock_job.priority = 5
        mock_job.progress = 0.0
        mock_job.source_lang = "en"
        mock_job.target_lang = "vi"
        mock_job.created_at = time.time()
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.avg_quality_score = 0.0
        mock_job.total_cost_usd = 0.0
        mock_job.error_message = None
        mock_job.metadata = {}

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=payload)

        assert resp.status_code == 201
        # Verify layout_mode mapping was applied in create_job call
        call_kwargs = mock_q.create_job.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata", {})
        assert metadata["layout_mode"] == "simple"
        assert metadata["use_ast_pipeline"] is False

    def test_create_professional_layout(self, client, tmp_path):
        payload = self._make_payload(tmp_path, ui_layout_mode="professional")

        mock_job = MagicMock()
        mock_job.job_id = "j2"
        mock_job.job_name = "Test"
        mock_job.status = "pending"
        mock_job.priority = 5
        mock_job.progress = 0.0
        mock_job.source_lang = "en"
        mock_job.target_lang = "vi"
        mock_job.created_at = time.time()
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.avg_quality_score = 0.0
        mock_job.total_cost_usd = 0.0
        mock_job.error_message = None
        mock_job.metadata = {}

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=payload)

        assert resp.status_code == 201
        metadata = mock_q.create_job.call_args.kwargs.get("metadata") or \
                   mock_q.create_job.call_args[1].get("metadata", {})
        assert metadata["use_ast_pipeline"] is True
        assert metadata["layout_mode"] == "simple"

    def test_create_academic_layout(self, client, tmp_path):
        payload = self._make_payload(tmp_path, ui_layout_mode="academic")

        mock_job = MagicMock()
        mock_job.job_id = "j3"
        mock_job.job_name = "Test"
        mock_job.status = "pending"
        mock_job.priority = 5
        mock_job.progress = 0.0
        mock_job.source_lang = "en"
        mock_job.target_lang = "vi"
        mock_job.created_at = time.time()
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.avg_quality_score = 0.0
        mock_job.total_cost_usd = 0.0
        mock_job.error_message = None
        mock_job.metadata = {}

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=payload)

        assert resp.status_code == 201
        metadata = mock_q.create_job.call_args.kwargs.get("metadata") or \
                   mock_q.create_job.call_args[1].get("metadata", {})
        assert metadata["layout_mode"] == "academic"
        assert metadata["use_ast_pipeline"] is True
        assert metadata["equation_rendering_mode"] == "omml"

    def test_create_job_file_not_found(self, client):
        payload = {
            "job_name": "Test",
            "input_file": "/nonexistent/file.txt",
            "output_file": "/tmp/out.docx",
        }
        resp = client.post("/api/jobs", json=payload)
        assert resp.status_code == 404


class TestCancelJob:
    """Test POST /api/jobs/{job_id}/cancel."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_cancel_not_found(self, client):
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.post("/api/jobs/nope/cancel")
        assert resp.status_code == 404

    def test_cancel_running_no_processor(self, client):
        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.status = "running"
        mock_job.updated_at = 0

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.get_processor", return_value=None), \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/j1/cancel")

        assert resp.status_code == 200
        assert "force-cancelled" in resp.json()["message"]

    def test_cancel_running_with_processor(self, client):
        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.status = "running"

        mock_proc = MagicMock()
        mock_proc.is_running = True

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.get_processor", return_value=mock_proc), \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/j1/cancel")

        assert resp.status_code == 200
        assert "cancellation requested" in resp.json()["message"].lower()
        mock_job.request_cancellation.assert_called_once()

    def test_cancel_pending_job(self, client):
        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.status = "pending"

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_q.cancel_job.return_value = True
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/j1/cancel")

        assert resp.status_code == 200
        assert "cancelled" in resp.json()["status"]

    def test_cancel_completed_job_rejected(self, client):
        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.status = "completed"

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager"):
            mock_q.get_job.return_value = mock_job
            mock_q.cancel_job.return_value = False
            resp = client.post("/api/jobs/j1/cancel")

        assert resp.status_code == 400


class TestDeleteJob:
    """Test DELETE /api/jobs/{job_id}."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_delete_success(self, client):
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.delete_job.return_value = True
            mock_mgr.broadcast = AsyncMock()
            resp = client.delete("/api/jobs/j1")

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_not_allowed(self, client):
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.delete_job.return_value = False
            resp = client.delete("/api/jobs/j1")
        assert resp.status_code == 400
