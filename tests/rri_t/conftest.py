"""
RRI-T (Reverse Requirements Interview - Testing) shared fixtures.

Provides reusable fixtures for all 6 sprints:
- rri_client: TestClient with auth overrides
- mock_ai_client: deterministic AI responses
- mock_queue: pre-configured JobQueue mock
- temp_sqlite_db: fresh SQLiteBackend per test
- mock_progress_callback: captures progress calls
"""

import os
import time
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "rri_t: RRI-T framework test")
    config.addinivalue_line("markers", "p0: Priority 0 — must pass for release")
    config.addinivalue_line("markers", "p1: Priority 1 — should pass for release")
    config.addinivalue_line("markers", "p2: Priority 2 — nice to have")


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def rri_client():
    """TestClient wrapping the FastAPI app with auth disabled."""
    from api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Mock AI Client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ai_client():
    """Returns a mock AI client that produces deterministic translations."""
    client = MagicMock()
    client.provider = "mock"
    client.model = "mock-v1"

    async def _translate(text, **kwargs):
        return f"[TRANSLATED] {text[:80]}"

    client.translate = AsyncMock(side_effect=_translate)
    client.generate = AsyncMock(return_value="Generated text")

    # Usage stats
    stats = MagicMock()
    stats.input_tokens = 100
    stats.output_tokens = 50
    stats.total_tokens = 150
    stats.cost_usd = 0.001
    stats.elapsed_seconds = 0.5
    client.last_usage = stats

    return client


# ---------------------------------------------------------------------------
# Mock Job Queue
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_queue():
    """Pre-configured JobQueue mock."""
    q = MagicMock()

    def _make_job(job_id="test-job-1", status="pending", **kw):
        job = MagicMock()
        job.job_id = job_id
        job.job_name = kw.get("job_name", "Test Job")
        job.status = status
        job.priority = kw.get("priority", 5)
        job.progress = kw.get("progress", 0.0)
        job.source_lang = kw.get("source_lang", "en")
        job.target_lang = kw.get("target_lang", "vi")
        job.created_at = kw.get("created_at", time.time())
        job.started_at = kw.get("started_at", None)
        job.completed_at = kw.get("completed_at", None)
        job.avg_quality_score = kw.get("avg_quality_score", 0.0)
        job.total_cost_usd = kw.get("total_cost_usd", 0.0)
        job.error_message = kw.get("error_message", None)
        job.metadata = kw.get("metadata", {})
        job.output_file = kw.get("output_file", "output.docx")
        job.output_format = kw.get("output_format", "docx")
        job.total_chunks = kw.get("total_chunks", 10)
        job.completed_chunks = kw.get("completed_chunks", 0)
        return job

    q._make_job = _make_job
    q.create_job.return_value = _make_job()
    q.get_job.return_value = _make_job()
    q.list_jobs.return_value = [_make_job()]
    q.cancel_job.return_value = True
    q.delete_job.return_value = True
    q.restart_job.return_value = _make_job(status="pending")
    return q


# ---------------------------------------------------------------------------
# Temp SQLite Database
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_sqlite_db(tmp_path):
    """Fresh SQLite database for each test via tmp_path."""
    db_path = tmp_path / "test.db"
    return db_path


# ---------------------------------------------------------------------------
# Mock Progress Callback
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_progress_callback():
    """Captures progress calls for verification."""
    calls = []

    async def _callback(progress: float, message: str = "", **kwargs):
        calls.append({"progress": progress, "message": message, **kwargs})

    cb = AsyncMock(side_effect=_callback)
    cb.calls = calls
    return cb


# ---------------------------------------------------------------------------
# Sample Files
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_txt_file(tmp_path):
    """Create a sample text file for upload/job tests."""
    f = tmp_path / "sample.txt"
    f.write_text("This is a test document for translation. " * 50)
    return f


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a minimal PDF file with valid magic bytes."""
    f = tmp_path / "sample.pdf"
    # Minimal valid PDF structure
    f.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n115\n%%EOF"
    )
    return f


@pytest.fixture
def sample_docx_file(tmp_path):
    """Create a minimal DOCX file (ZIP with PK magic bytes)."""
    import zipfile
    f = tmp_path / "sample.docx"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
    return f
