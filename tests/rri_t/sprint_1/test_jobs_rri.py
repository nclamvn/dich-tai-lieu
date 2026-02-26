"""
RRI-T Sprint 1: Jobs API endpoint tests.

Persona coverage: End User, QA Destroyer, Security Auditor, DevOps
Dimensions: D2 (API), D4 (Security), D5 (Data Integrity), D7 (Edge Cases)
"""

import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from core.job_queue import JobStatus


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_job(job_id="test-123", status="pending", progress=0.0, metadata=None, **kw):
    job = MagicMock()
    job.job_id = job_id
    job.job_name = kw.get("job_name", "Test Job")
    job.status = status
    job.priority = kw.get("priority", 5)
    job.progress = progress
    job.source_lang = kw.get("source_lang", "en")
    job.target_lang = kw.get("target_lang", "vi")
    job.created_at = kw.get("created_at", time.time())
    job.started_at = time.time() - 60 if status not in ("pending", "queued") else None
    job.completed_at = time.time() if status == "completed" else None
    job.avg_quality_score = kw.get("avg_quality_score", 0.0)
    job.total_cost_usd = kw.get("total_cost_usd", 0.0)
    job.error_message = kw.get("error_message", None)
    job.metadata = metadata or {}
    job.output_file = kw.get("output_file", "output.docx")
    job.output_format = kw.get("output_format", "docx")
    job.total_chunks = kw.get("total_chunks", 10)
    job.completed_chunks = int(progress * 10)
    return job


# ===========================================================================
# JOBS-001: Create job with valid payload -> 201
# ===========================================================================

class TestCreateJob:
    """End User persona — happy-path job creation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _payload(self, tmp_path, **overrides):
        f = tmp_path / "input.txt"
        f.write_text("Test document content for translation.")
        payload = {
            "job_name": "RRI-T Test",
            "input_file": str(f),
            "output_file": str(tmp_path / "out.docx"),
            "source_lang": "en",
            "target_lang": "vi",
        }
        payload.update(overrides)
        return payload

    @pytest.mark.p0
    def test_jobs_001_create_valid_payload_returns_201(self, client, tmp_path):
        """JOBS-001 | End User | Create job with valid payload -> 201"""
        mock_job = _make_job(job_id="j-new", status="pending")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=self._payload(tmp_path))

        assert resp.status_code == 201
        data = resp.json()
        assert data["job_id"] == "j-new"
        assert data["status"] == "pending"

    @pytest.mark.p0
    def test_jobs_001b_create_returns_all_fields(self, client, tmp_path):
        """JOBS-001b | End User | Response contains all required fields"""
        mock_job = _make_job(job_id="j-full")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=self._payload(tmp_path))

        data = resp.json()
        required_fields = ["job_id", "job_name", "status", "priority",
                           "progress", "source_lang", "target_lang", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ===========================================================================
# JOBS-002: source_lang == target_lang -> 400
# ===========================================================================

class TestSameLanguageRejection:
    """QA Destroyer persona — same-language validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_jobs_002_same_language_rejected(self, client, tmp_path):
        """JOBS-002 | QA Destroyer | source_lang == target_lang -> 400"""
        f = tmp_path / "input.txt"
        f.write_text("Test")
        payload = {
            "job_name": "Same Lang",
            "input_file": str(f),
            "output_file": str(tmp_path / "out.docx"),
            "source_lang": "en",
            "target_lang": "en",
        }
        resp = client.post("/api/jobs", json=payload)
        assert resp.status_code == 400
        assert "same" in resp.json()["detail"].lower()

    @pytest.mark.p0
    def test_jobs_002b_same_language_vi(self, client, tmp_path):
        """JOBS-002b | QA Destroyer | Vietnamese same-lang also rejected"""
        f = tmp_path / "input.txt"
        f.write_text("Test")
        payload = {
            "job_name": "Same Lang VI",
            "input_file": str(f),
            "output_file": str(tmp_path / "out.docx"),
            "source_lang": "vi",
            "target_lang": "vi",
        }
        resp = client.post("/api/jobs", json=payload)
        assert resp.status_code == 400


# ===========================================================================
# JOBS-003: User isolation (multi-tenancy)
# ===========================================================================

class TestUserIsolation:
    """Security Auditor persona — User A cannot see User B's jobs."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_jobs_003_list_filters_by_user_id(self, client):
        """JOBS-003 | Security Auditor | list_jobs called with user_id filter"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.list_jobs.return_value = []
            resp = client.get("/api/jobs")

        assert resp.status_code == 200
        # Verify user_id was passed to list_jobs
        mock_q.list_jobs.assert_called_once()
        call_kwargs = mock_q.list_jobs.call_args
        assert "user_id" in call_kwargs.kwargs or len(call_kwargs.args) > 0


# ===========================================================================
# JOBS-004: Non-existent job_id -> 404
# ===========================================================================

class TestJobNotFound:
    """QA Destroyer persona — non-existent resources."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_jobs_004_get_nonexistent_returns_404(self, client):
        """JOBS-004 | QA Destroyer | GET non-existent job_id -> 404"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.p0
    def test_jobs_004b_progress_nonexistent_returns_404(self, client):
        """JOBS-004b | QA Destroyer | Progress for non-existent job -> 404"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.get("/api/jobs/nonexistent-id/progress")
        assert resp.status_code == 404

    @pytest.mark.p0
    def test_jobs_004c_cancel_nonexistent_returns_404(self, client):
        """JOBS-004c | QA Destroyer | Cancel non-existent job -> 404"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.post("/api/jobs/nonexistent-id/cancel")
        assert resp.status_code == 404


# ===========================================================================
# JOBS-005: Cancel already-completed job -> 400
# ===========================================================================

class TestCancelCompleted:
    """QA Destroyer persona — invalid state transitions."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_005_cancel_completed_returns_400(self, client):
        """JOBS-005 | QA Destroyer | Cancel completed job -> 400"""
        mock_job = _make_job(status="completed", progress=1.0)
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager"):
            mock_q.get_job.return_value = mock_job
            mock_q.cancel_job.return_value = False
            resp = client.post("/api/jobs/test-123/cancel")
        assert resp.status_code == 400

    @pytest.mark.p1
    def test_jobs_005b_cancel_pending_succeeds(self, client):
        """JOBS-005b | QA Destroyer | Cancel pending job -> 200"""
        mock_job = _make_job(status="pending")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_q.cancel_job.return_value = True
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/test-123/cancel")
        assert resp.status_code == 200
        assert "cancelled" in resp.json()["status"]

    @pytest.mark.p1
    def test_jobs_005c_cancel_running_with_processor(self, client):
        """JOBS-005c | Cancel running job with active processor -> cancellation requested"""
        mock_job = _make_job(status="running", progress=0.5)
        mock_proc = MagicMock()
        mock_proc.is_running = True

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.get_processor", return_value=mock_proc), \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/test-123/cancel")

        assert resp.status_code == 200
        assert "cancellation requested" in resp.json()["message"].lower()
        mock_job.request_cancellation.assert_called_once()

    @pytest.mark.p1
    def test_jobs_005d_cancel_running_no_processor(self, client):
        """JOBS-005d | Cancel running job with no processor -> force-cancelled"""
        mock_job = _make_job(status="running", progress=0.3)
        mock_job.updated_at = 0

        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.get_processor", return_value=None), \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/test-123/cancel")

        assert resp.status_code == 200
        assert "force-cancelled" in resp.json()["message"]


# ===========================================================================
# JOBS-006: Negative/invalid offset and limit
# ===========================================================================

class TestPaginationEdgeCases:
    """QA Destroyer persona — pagination boundaries."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_006_zero_limit(self, client):
        """JOBS-006 | QA Destroyer | limit=0 -> returns empty list"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.list_jobs.return_value = []
            resp = client.get("/api/jobs?limit=0")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_jobs_006b_large_offset(self, client):
        """JOBS-006b | QA Destroyer | Very large offset -> empty list"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.list_jobs.return_value = []
            resp = client.get("/api/jobs?offset=999999")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# JOBS-007: Delete job (state checks)
# ===========================================================================

class TestDeleteJob:
    """QA Destroyer — delete state validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_jobs_007_delete_completed_succeeds(self, client):
        """JOBS-007 | Delete completed job -> 200"""
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.delete_job.return_value = True
            mock_mgr.broadcast = AsyncMock()
            resp = client.delete("/api/jobs/j1")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    @pytest.mark.p0
    def test_jobs_007b_delete_running_rejected(self, client):
        """JOBS-007b | Delete running job -> 400"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.delete_job.return_value = False
            resp = client.delete("/api/jobs/j1")
        assert resp.status_code == 400


# ===========================================================================
# JOBS-008: Restart job
# ===========================================================================

class TestRestartJob:
    """End User persona — restart failed jobs."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_008_restart_failed_succeeds(self, client):
        """JOBS-008 | End User | Restart failed job -> 200"""
        restarted = _make_job(job_id="j-restart", status="pending")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.restart_job.return_value = restarted
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs/j-restart/restart")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    @pytest.mark.p1
    def test_jobs_008b_restart_running_rejected(self, client):
        """JOBS-008b | Restart running job -> 400"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.restart_job.return_value = None
            resp = client.post("/api/jobs/j-running/restart")
        assert resp.status_code == 400


# ===========================================================================
# JOBS-009: Update job (PATCH)
# ===========================================================================

class TestUpdateJob:
    """End User persona — update priority."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_009_update_priority(self, client):
        """JOBS-009 | End User | Update job priority -> 200"""
        job = _make_job(job_id="j-update")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.get_job.return_value = job
            mock_mgr.broadcast = AsyncMock()
            resp = client.patch("/api/jobs/j-update", json={"priority": 1})
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_jobs_009b_update_nonexistent_returns_404(self, client):
        """JOBS-009b | Update non-existent job -> 404"""
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = None
            resp = client.patch("/api/jobs/nope", json={"priority": 1})
        assert resp.status_code == 404


# ===========================================================================
# JOBS-010: Input file not found -> 404
# ===========================================================================

class TestInputFileValidation:
    """QA Destroyer — file validation edge cases."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_jobs_010_file_not_found(self, client):
        """JOBS-010 | QA Destroyer | Non-existent input file -> 404"""
        payload = {
            "job_name": "Missing File",
            "input_file": "/nonexistent/file.txt",
            "output_file": "/tmp/out.docx",
            "source_lang": "en",
            "target_lang": "vi",
        }
        resp = client.post("/api/jobs", json=payload)
        assert resp.status_code == 404

    @pytest.mark.p1
    def test_jobs_010b_empty_job_name(self, client, tmp_path):
        """JOBS-010b | QA Destroyer | Empty job_name still accepted (no validation)"""
        f = tmp_path / "input.txt"
        f.write_text("content")
        payload = {
            "job_name": "",
            "input_file": str(f),
            "output_file": str(tmp_path / "out.docx"),
            "source_lang": "en",
            "target_lang": "vi",
        }
        mock_job = _make_job(job_name="")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json=payload)
        # Should still succeed (no validation on empty name)
        assert resp.status_code == 201


# ===========================================================================
# JOBS-011: Progress tracking fidelity
# ===========================================================================

class TestProgressTracking:
    """Business Analyst persona — progress accuracy."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_011_progress_0_to_100(self, client):
        """JOBS-011 | BA | Pending -> 0%, Completed -> 100%"""
        for status, expected_pct in [("pending", 0), ("completed", 100)]:
            job = _make_job(status=status, progress=1.0 if status == "completed" else 0.0)
            with patch("api.routes.jobs.queue") as mock_q:
                mock_q.get_job.return_value = job
                resp = client.get(f"/api/jobs/{job.job_id}/progress")
            assert resp.json()["progress_percent"] == expected_pct

    @pytest.mark.p1
    def test_jobs_011b_steps_include_upload_and_translation(self, client):
        """JOBS-011b | BA | Steps always include upload + translation + docx_render"""
        job = _make_job(status="pending")
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")
        step_names = [s["name"] for s in resp.json()["steps"]]
        assert "upload" in step_names
        assert "translation" in step_names
        assert "docx_render" in step_names

    @pytest.mark.p1
    def test_jobs_011c_ocr_step_when_enabled(self, client):
        """JOBS-011c | BA | OCR step included when enable_ocr=True"""
        job = _make_job(status="running", progress=0.3, metadata={"enable_ocr": True})
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")
        step_names = [s["name"] for s in resp.json()["steps"]]
        assert "ocr" in step_names

    @pytest.mark.p1
    def test_jobs_011d_pdf_export_step(self, client):
        """JOBS-011d | BA | PDF export step when pdf in output_formats"""
        job = _make_job(
            status="completed", progress=1.0,
            metadata={"output_formats_requested": ["docx", "pdf"]}
        )
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")
        step_names = [s["name"] for s in resp.json()["steps"]]
        assert "pdf_export" in step_names

    @pytest.mark.p1
    def test_jobs_011e_elapsed_time_calculated(self, client):
        """JOBS-011e | BA | Elapsed time calculated for running jobs"""
        job = _make_job(status="running", progress=0.5)
        job.started_at = time.time() - 120  # 2 minutes ago
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get("/api/jobs/test-123/progress")
        data = resp.json()
        assert data["elapsed_seconds"] > 100  # at least ~2 minutes


# ===========================================================================
# JOBS-012: Broadcast events
# ===========================================================================

class TestBroadcastEvents:
    """DevOps persona — WebSocket events emitted correctly."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_jobs_012_create_broadcasts_event(self, client, tmp_path):
        """JOBS-012 | DevOps | Create job broadcasts job_created event"""
        f = tmp_path / "input.txt"
        f.write_text("content")
        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            client.post("/api/jobs", json={
                "job_name": "Broadcast Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
            })
        mock_mgr.broadcast.assert_called_once()
        event = mock_mgr.broadcast.call_args[0][0]
        assert event["event"] == "job_created"

    @pytest.mark.p1
    def test_jobs_012b_delete_broadcasts_event(self, client):
        """JOBS-012b | DevOps | Delete broadcasts job_deleted event"""
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.delete_job.return_value = True
            mock_mgr.broadcast = AsyncMock()
            client.delete("/api/jobs/j1")
        mock_mgr.broadcast.assert_called_once()
        event = mock_mgr.broadcast.call_args[0][0]
        assert event["event"] == "job_deleted"
