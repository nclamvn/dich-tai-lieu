"""Tests for JobRepository."""

import pytest
from pathlib import Path
from datetime import datetime

from api.job_repository import JobRepository


@pytest.fixture
def repo(tmp_path):
    return JobRepository(db_path=str(tmp_path / "test_jobs.db"))


def _make_job(job_id="test-001", status="pending", progress=0.0):
    return {
        "job_id": job_id,
        "source_file": "test.pdf",
        "source_language": "en",
        "target_language": "vi",
        "profile_id": "novel",
        "output_formats": ["docx", "pdf"],
        "use_vision": True,
        "status": status,
        "progress": progress,
        "current_stage": "",
    }


class TestJobRepository:

    def test_save_and_get(self, repo):
        job = _make_job()
        repo.save(job)

        loaded = repo.get("test-001")
        assert loaded is not None
        assert loaded["job_id"] == "test-001"
        assert loaded["source_language"] == "en"
        assert loaded["output_formats"] == ["docx", "pdf"]

    def test_get_nonexistent(self, repo):
        assert repo.get("nonexistent") is None

    def test_update_progress(self, repo):
        repo.save(_make_job())
        repo.update_progress("test-001", 50.0, "Translating")

        job = repo.get("test-001")
        assert job["progress"] == 50.0
        assert job["current_stage"] == "Translating"

    def test_mark_complete(self, repo):
        repo.save(_make_job())
        repo.mark_complete("test-001", {"docx": "/out/test.docx"})

        job = repo.get("test-001")
        assert job["status"] == "complete"
        assert job["progress"] == 100.0
        assert job["output_paths"]["docx"] == "/out/test.docx"

    def test_mark_failed(self, repo):
        repo.save(_make_job())
        repo.mark_failed("test-001", "Something went wrong")

        job = repo.get("test-001")
        assert job["status"] == "failed"
        assert "Something went wrong" in job["error"]

    def test_delete(self, repo):
        repo.save(_make_job())
        assert repo.delete("test-001") is True
        assert repo.get("test-001") is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent") is False

    def test_get_pending_jobs(self, repo):
        repo.save(_make_job("job-1", status="pending"))
        repo.save(_make_job("job-2", status="running"))
        repo.save(_make_job("job-3", status="complete"))

        pending = repo.get_pending_jobs()
        assert len(pending) == 2  # pending + running

    def test_get_all_jobs(self, repo):
        for i in range(5):
            repo.save(_make_job(f"job-{i}"))

        jobs = repo.get_all_jobs(limit=3)
        assert len(jobs) == 3

    def test_save_with_datetime(self, repo):
        job = _make_job()
        job["created_at"] = datetime.now()
        job["completed_at"] = datetime.now()
        repo.save(job)

        loaded = repo.get("test-001")
        assert loaded is not None
