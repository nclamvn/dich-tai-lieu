"""
Unit tests for core.batch.job_handler module.

Tests JobHandler, JobState, JobResult, and JobTiming classes.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path

from core.batch.job_handler import (
    JobHandler,
    JobState,
    JobResult,
    JobTiming,
)


class TestJobState:
    """Tests for JobState enum."""

    def test_all_states_exist(self):
        """Verify all expected states exist."""
        expected_states = [
            'INITIALIZING', 'LOADING_INPUT', 'OCR_PROCESSING', 'PREPROCESSING',
            'CHUNKING', 'TRANSLATING', 'MERGING', 'POSTPROCESSING',
            'EXPORTING', 'FINALIZING', 'COMPLETED', 'FAILED'
        ]
        actual_states = [s.name for s in JobState]
        for state in expected_states:
            assert state in actual_states

    def test_state_values(self):
        """Verify state values are lowercase strings."""
        for state in JobState:
            assert state.value == state.name.lower()


class TestJobTiming:
    """Tests for JobTiming dataclass."""

    def test_timing_creation(self):
        """Test creating JobTiming with defaults."""
        timing = JobTiming()
        assert timing.started_at is None
        assert timing.completed_at is None
        assert timing.phase_times == {}

    def test_start(self):
        """Test starting timing."""
        timing = JobTiming()
        timing.start()
        assert timing.started_at is not None
        assert timing.started_at <= datetime.now()

    def test_complete(self):
        """Test completing timing."""
        timing = JobTiming()
        timing.start()
        time.sleep(0.01)  # Small delay
        timing.complete()
        assert timing.completed_at is not None
        assert timing.completed_at >= timing.started_at

    def test_total_duration(self):
        """Test total duration calculation."""
        timing = JobTiming()
        timing.start()
        time.sleep(0.05)
        timing.complete()

        duration = timing.total_duration
        assert duration is not None
        assert duration >= 0.04  # Allow some variance

    def test_total_duration_incomplete(self):
        """Test total duration when not complete."""
        timing = JobTiming()
        timing.start()
        assert timing.total_duration is None

    def test_record_phase(self):
        """Test recording phase times."""
        timing = JobTiming()
        timing.record_phase("loading", 1.5)
        timing.record_phase("translating", 10.0)

        assert timing.phase_times["loading"] == 1.5
        assert timing.phase_times["translating"] == 10.0


class TestJobResult:
    """Tests for JobResult dataclass."""

    def test_result_creation_success(self):
        """Test creating successful JobResult."""
        result = JobResult(
            job_id="job_001",
            success=True,
            output_path=Path("/output/result.docx"),
            translated_text="Translated content",
            chunk_count=10,
            quality_score=0.92
        )
        assert result.job_id == "job_001"
        assert result.success is True
        assert result.output_path == Path("/output/result.docx")
        assert result.quality_score == 0.92
        assert result.error_message is None

    def test_result_creation_failure(self):
        """Test creating failed JobResult."""
        result = JobResult(
            job_id="job_002",
            success=False,
            error_message="API rate limit exceeded"
        )
        assert result.success is False
        assert result.error_message == "API rate limit exceeded"
        assert result.output_path is None

    def test_result_with_metadata(self):
        """Test JobResult with metadata."""
        result = JobResult(
            job_id="job_003",
            success=True,
            metadata={'source_lang': 'en', 'target_lang': 'vi'}
        )
        assert result.metadata['source_lang'] == 'en'
        assert result.metadata['target_lang'] == 'vi'


class TestJobHandler:
    """Tests for JobHandler class."""

    @pytest.fixture
    def job_handler(self):
        """Create a fresh JobHandler instance."""
        return JobHandler(job_id="test_job_001")

    def test_handler_initialization(self, job_handler):
        """Test JobHandler starts in INITIALIZING state."""
        assert job_handler.job_id == "test_job_001"
        assert job_handler.state == JobState.INITIALIZING
        assert job_handler.retry_count == 0
        assert job_handler.error is None

    def test_handler_with_params(self):
        """Test JobHandler with custom params."""
        handler = JobHandler(
            job_id="test_002",
            job_name="Test Job",
            timeout=300,
            max_retries=5
        )
        assert handler.job_name == "Test Job"
        assert handler.timeout == 300
        assert handler.max_retries == 5

    def test_start_job(self, job_handler):
        """Test starting a job."""
        job_handler.start()
        assert job_handler.timing.started_at is not None
        assert job_handler.timing.started_at <= datetime.now()

    def test_transition_valid_states(self, job_handler):
        """Test valid state transitions."""
        job_handler.start()
        assert job_handler.state == JobState.INITIALIZING

        job_handler.transition_to(JobState.LOADING_INPUT)
        assert job_handler.state == JobState.LOADING_INPUT

        job_handler.transition_to(JobState.CHUNKING)
        assert job_handler.state == JobState.CHUNKING

        job_handler.transition_to(JobState.TRANSLATING)
        assert job_handler.state == JobState.TRANSLATING

        job_handler.transition_to(JobState.MERGING)
        assert job_handler.state == JobState.MERGING

        job_handler.transition_to(JobState.EXPORTING)
        assert job_handler.state == JobState.EXPORTING

    def test_complete_job(self, job_handler):
        """Test completing a job."""
        job_handler.start()
        job_handler.transition_to(JobState.LOADING_INPUT)
        job_handler.transition_to(JobState.TRANSLATING)
        job_handler.transition_to(JobState.EXPORTING)

        result = job_handler.complete(
            output_path=Path("/output/result.docx"),
            translated_text="Translated content",
            chunk_count=100,
            quality_score=0.9
        )

        assert job_handler.state == JobState.COMPLETED
        assert result.success is True
        assert result.chunk_count == 100
        assert result.quality_score == 0.9
        assert job_handler.timing.completed_at is not None

    def test_fail_job(self, job_handler):
        """Test failing a job."""
        job_handler.start()
        job_handler.transition_to(JobState.TRANSLATING)

        result = job_handler.fail(error="API rate limit exceeded")

        assert job_handler.state == JobState.FAILED
        assert job_handler.error == "API rate limit exceeded"
        assert result.success is False
        assert result.error_message == "API rate limit exceeded"

    def test_can_retry_within_limit(self, job_handler):
        """Test retry is allowed within retry limit."""
        assert job_handler.can_retry() is True
        assert job_handler.retry_count == 0

    def test_can_retry_at_limit(self, job_handler):
        """Test retry is not allowed at retry limit."""
        job_handler.retry_count = job_handler.max_retries
        assert job_handler.can_retry() is False

    def test_prepare_retry(self, job_handler):
        """Test preparing for retry resets state."""
        job_handler.start()
        job_handler.transition_to(JobState.TRANSLATING)
        job_handler.fail(error="Timeout")

        success = job_handler.prepare_retry()

        assert success is True
        assert job_handler.state == JobState.INITIALIZING
        assert job_handler.retry_count == 1
        assert job_handler.error is None

    def test_prepare_retry_at_limit(self, job_handler):
        """Test prepare_retry returns False at limit."""
        job_handler.retry_count = job_handler.max_retries

        success = job_handler.prepare_retry()

        assert success is False

    def test_multiple_retries(self, job_handler):
        """Test multiple retry cycles."""
        for i in range(job_handler.max_retries):
            job_handler.start()
            job_handler.transition_to(JobState.TRANSLATING)
            job_handler.fail(error=f"Error {i}")

            if job_handler.can_retry():
                success = job_handler.prepare_retry()
                assert success is True
                assert job_handler.retry_count == i + 1

        # Next retry should fail
        assert job_handler.can_retry() is False
        assert job_handler.prepare_retry() is False

    def test_get_state_summary(self, job_handler):
        """Test getting state summary."""
        job_handler.start()
        job_handler.transition_to(JobState.TRANSLATING)

        summary = job_handler.get_state_summary()

        assert summary['job_id'] == "test_job_001"
        assert summary['state'] == 'translating'
        assert summary['retry_count'] == 0
        assert 'timing' in summary
        assert summary['timing']['started_at'] is not None

    def test_add_metadata(self, job_handler):
        """Test adding metadata."""
        job_handler.add_metadata('source_lang', 'en')
        job_handler.add_metadata('target_lang', 'vi')

        job_handler.start()
        result = job_handler.complete()

        assert result.metadata['source_lang'] == 'en'
        assert result.metadata['target_lang'] == 'vi'

    def test_phase_timing_recorded(self, job_handler):
        """Test that phase transition times are recorded."""
        job_handler.start()
        time.sleep(0.02)
        job_handler.transition_to(JobState.LOADING_INPUT)
        time.sleep(0.02)
        job_handler.transition_to(JobState.TRANSLATING)

        # Check phase times are being recorded
        assert 'initializing' in job_handler.timing.phase_times
        assert job_handler.timing.phase_times['initializing'] >= 0.01


class TestJobHandlerEdgeCases:
    """Edge case tests for JobHandler."""

    def test_empty_job_id(self):
        """Test handler with empty job_id."""
        handler = JobHandler(job_id="")
        assert handler.job_id == ""
        handler.start()
        assert handler.timing.started_at is not None

    def test_complete_with_no_output(self):
        """Test completing job with no output path."""
        handler = JobHandler(job_id="job_001")
        handler.start()
        handler.transition_to(JobState.EXPORTING)

        result = handler.complete()

        assert result.success is True
        assert result.output_path is None
        assert result.translated_text is None

    def test_fail_with_empty_error(self):
        """Test failing job with empty error message."""
        handler = JobHandler(job_id="job_001")
        handler.start()

        result = handler.fail(error="")

        assert result.error_message == ""
        assert result.success is False

    def test_timing_accuracy(self):
        """Test timing accuracy within reasonable bounds."""
        handler = JobHandler(job_id="job_001")

        before = datetime.now()
        handler.start()
        after = datetime.now()

        assert before <= handler.timing.started_at <= after

    def test_total_chars_calculation(self):
        """Test total_chars is calculated from translated_text."""
        handler = JobHandler(job_id="job_001")
        handler.start()

        text = "Hello world! This is a test."
        result = handler.complete(translated_text=text)

        assert result.total_chars == len(text)

    def test_total_chars_none_text(self):
        """Test total_chars is 0 when translated_text is None."""
        handler = JobHandler(job_id="job_001")
        handler.start()

        result = handler.complete(translated_text=None)

        assert result.total_chars == 0

    def test_estimated_cost_passed_through(self):
        """Test estimated_cost is passed to result."""
        handler = JobHandler(job_id="job_001")
        handler.start()

        result = handler.complete(estimated_cost=1.25)

        assert result.estimated_cost == 1.25
