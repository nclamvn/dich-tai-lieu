"""Tests for core.job_queue — JobStatus, JobPriority, TranslationJob."""

import pytest
import time
from core.job_queue import JobStatus, JobPriority, TranslationJob


class TestJobStatusEnum:
    """JobStatus enum values and behavior."""

    def test_pending_value(self):
        assert JobStatus.PENDING == "pending"

    def test_running_value(self):
        assert JobStatus.RUNNING == "running"

    def test_completed_value(self):
        assert JobStatus.COMPLETED == "completed"

    def test_failed_value(self):
        assert JobStatus.FAILED == "failed"

    def test_cancelled_value(self):
        assert JobStatus.CANCELLED == "cancelled"

    def test_all_statuses_are_strings(self):
        for status in JobStatus:
            assert isinstance(status.value, str)

    def test_status_count(self):
        assert len(JobStatus) >= 7


class TestJobPriorityEnum:
    """JobPriority enum values."""

    def test_low_less_than_normal(self):
        assert JobPriority.LOW < JobPriority.NORMAL

    def test_normal_less_than_high(self):
        assert JobPriority.NORMAL < JobPriority.HIGH

    def test_high_less_than_urgent(self):
        assert JobPriority.HIGH < JobPriority.URGENT

    def test_urgent_less_than_critical(self):
        assert JobPriority.URGENT < JobPriority.CRITICAL

    def test_priorities_are_integers(self):
        for p in JobPriority:
            assert isinstance(p.value, int)


class TestTranslationJob:
    """TranslationJob dataclass."""

    @pytest.fixture
    def job(self):
        return TranslationJob(
            job_id="test-001",
            job_name="Test Translation",
            input_file="/tmp/input.txt",
            output_file="/tmp/output.txt",
        )

    def test_create_job(self, job):
        assert job.job_id == "test-001"
        assert job.job_name == "Test Translation"
        assert job.status == JobStatus.PENDING

    def test_default_languages(self, job):
        assert job.source_lang == "en"
        assert job.target_lang == "vi"

    def test_default_progress(self, job):
        assert job.progress == 0.0
        assert job.completed_chunks == 0

    def test_mark_started(self, job):
        job.mark_started()
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_mark_completed(self, job):
        job.mark_started()
        job.mark_completed(avg_quality=0.95, total_cost=0.50)
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 1.0
        assert job.avg_quality_score == 0.95
        assert job.total_cost_usd == 0.50
        assert job.completed_at is not None

    def test_mark_failed(self, job):
        job.mark_started()
        job.mark_failed("API timeout")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "API timeout"
        assert job.completed_at is not None

    def test_update_progress(self, job):
        job.update_progress(completed=5, total=10)
        assert job.completed_chunks == 5
        assert job.total_chunks == 10
        assert job.progress == 0.5

    def test_update_progress_zero_total(self, job):
        job.update_progress(completed=0, total=0)
        assert job.progress == 0.0

    def test_can_retry_default(self, job):
        job.mark_failed("error")
        assert job.can_retry()

    def test_to_dict(self, job):
        d = job.to_dict()
        assert isinstance(d, dict)
        assert d["job_id"] == "test-001"
        assert d["status"] in ("pending", JobStatus.PENDING)

    def test_from_dict(self, job):
        d = job.to_dict()
        restored = TranslationJob.from_dict(d)
        assert restored.job_id == job.job_id
        assert restored.job_name == job.job_name

    def test_cancellation_flag(self, job):
        assert job.cancellation_requested is False
        job.cancellation_requested = True
        assert job.cancellation_requested is True

    def test_metadata_default_empty(self, job):
        assert job.metadata == {}
        assert job.tags == []
