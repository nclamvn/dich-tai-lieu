"""
Unit tests for api/models.py — Pydantic model validation.
"""
import pytest
from pydantic import ValidationError

from api.models import (
    JobCreate, JobUpdate, JobResponse, QueueStats, SystemInfo,
    AnalyzeRequest, AnalyzeResponse, ProgressStep, JobProgressResponse,
    LoginRequest,
)
from core.job_queue import JobPriority


class TestJobCreate:
    """Test JobCreate model defaults and validation."""

    def test_minimal_required_fields(self):
        job = JobCreate(job_name="test", input_file="/tmp/a.txt", output_file="/tmp/b.txt")
        assert job.job_name == "test"
        assert job.source_lang == "en"
        assert job.target_lang == "vi"

    def test_default_values(self):
        job = JobCreate(job_name="t", input_file="a", output_file="b")
        assert job.priority == JobPriority.NORMAL
        assert job.provider == "openai"
        assert job.model == "gpt-4o-mini"
        assert job.concurrency == 5
        assert job.chunk_size == 3000
        assert job.output_format == "txt"
        assert job.domain is None
        assert job.glossary is None
        assert job.use_smart_tables is False
        assert job.enable_ocr is False
        assert job.layout_mode == "simple"
        assert job.engine == "auto"
        assert job.use_vision is True

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            JobCreate()

    def test_optional_ui_fields_none_by_default(self):
        job = JobCreate(job_name="t", input_file="a", output_file="b")
        assert job.ui_layout_mode is None
        assert job.output_formats is None
        assert job.advanced_options is None
        assert job.cover_image is None
        assert job.api_key is None

    def test_ui_layout_mode_accepted(self):
        job = JobCreate(
            job_name="t", input_file="a", output_file="b",
            ui_layout_mode="academic",
            output_formats=["docx", "pdf"],
            advanced_options={"chunk_size": 5000}
        )
        assert job.ui_layout_mode == "academic"
        assert job.output_formats == ["docx", "pdf"]
        assert job.advanced_options["chunk_size"] == 5000

    def test_all_priority_values(self):
        for p in [1, 5, 10, 20, 50]:
            job = JobCreate(job_name="t", input_file="a", output_file="b", priority=p)
            assert job.priority == p


class TestJobUpdate:
    """Test JobUpdate model."""

    def test_empty_update(self):
        update = JobUpdate()
        assert update.status is None
        assert update.priority is None

    def test_partial_update(self):
        update = JobUpdate(status="completed")
        assert update.status == "completed"
        assert update.priority is None

    def test_full_update(self):
        update = JobUpdate(status="running", priority=10)
        assert update.status == "running"
        assert update.priority == 10


class TestJobResponse:
    """Test JobResponse model and from_attributes config."""

    def test_creation(self):
        resp = JobResponse(
            job_id="abc", job_name="test", status="completed",
            priority=5, progress=1.0, source_lang="en", target_lang="vi",
            created_at=1000.0, started_at=1001.0, completed_at=1100.0,
            quality_score=0.95, total_cost_usd=0.50, error_message=None,
        )
        assert resp.job_id == "abc"
        assert resp.quality_score == 0.95

    def test_from_attributes_config(self):
        assert JobResponse.model_config.get("from_attributes") is True

    def test_optional_fields(self):
        resp = JobResponse(
            job_id="x", job_name="n", status="pending", priority=1,
            progress=0.0, source_lang="en", target_lang="vi",
            created_at=0.0, started_at=None, completed_at=None,
            quality_score=0.0, total_cost_usd=0.0, error_message=None,
        )
        assert resp.domain is None
        assert resp.metadata is None


class TestQueueStats:
    """Test QueueStats model."""

    def test_creation(self):
        qs = QueueStats(total=10, pending=2, queued=1, running=3, completed=3, failed=1, cancelled=0)
        assert qs.total == 10
        assert qs.running == 3

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            QueueStats(total=1, pending=0)  # missing queued, running, etc.


class TestSystemInfo:
    """Test SystemInfo model."""

    def test_creation(self):
        qs = QueueStats(total=0, pending=0, queued=0, running=0, completed=0, failed=0, cancelled=0)
        si = SystemInfo(version="2.4.0", uptime_seconds=100.0, processor_running=False, current_jobs=0, queue_stats=qs)
        assert si.version == "2.4.0"
        assert si.processor_running is False


class TestAnalyzeModels:
    """Test AnalyzeRequest and AnalyzeResponse."""

    def test_analyze_request(self):
        req = AnalyzeRequest(file_path="/tmp/doc.pdf")
        assert req.file_path == "/tmp/doc.pdf"

    def test_analyze_request_missing_field(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest()

    def test_analyze_response(self):
        resp = AnalyzeResponse(word_count=500, character_count=3000, detected_language="Tiếng Anh", chunks_estimate=1)
        assert resp.word_count == 500
        assert resp.detected_language == "Tiếng Anh"


class TestProgressStep:
    """Test ProgressStep model."""

    def test_creation(self):
        step = ProgressStep(name="upload", display_name="Tải file", status="completed")
        assert step.name == "upload"
        assert step.progress is None

    def test_with_progress(self):
        step = ProgressStep(name="translation", display_name="Dịch", status="in_progress", progress=0.5)
        assert step.progress == 0.5


class TestLoginRequest:
    """Test LoginRequest model defaults."""

    def test_defaults(self):
        req = LoginRequest()
        assert req.username == "user"
        assert req.organization == "Default Organization"

    def test_custom_values(self):
        req = LoginRequest(username="admin", organization="ACME")
        assert req.username == "admin"
