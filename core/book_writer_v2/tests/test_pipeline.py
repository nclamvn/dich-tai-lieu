"""
Tests for the pipeline orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.pipeline import BookWriterPipeline
from core.book_writer_v2.models import BookStatus


@pytest.fixture
def pipeline_config():
    """Config for pipeline tests"""
    return BookWriterConfig(
        words_per_page=300,
        target_words_per_section=1500,
        max_expansion_attempts=1,
        max_total_expansion_rounds=1,
    )


@pytest.fixture
def mock_ai():
    """Mock AI client for pipeline"""
    client = MagicMock()
    client.generate = AsyncMock(return_value="word " * 1500)
    return client


class TestBookWriterPipeline:
    """Tests for BookWriterPipeline"""

    def test_initialization(self, pipeline_config, mock_ai):
        pipeline = BookWriterPipeline(pipeline_config, mock_ai)
        assert pipeline.analyst is not None
        assert pipeline.architect is not None
        assert pipeline.outliner is not None
        assert pipeline.writer is not None
        assert pipeline.expander is not None
        assert pipeline.enricher is not None
        assert pipeline.editor is not None
        assert pipeline.quality_gate is not None
        assert pipeline.publisher is not None

    def test_progress_callback(self, pipeline_config, mock_ai):
        callback = MagicMock()
        pipeline = BookWriterPipeline(pipeline_config, mock_ai, progress_callback=callback)
        pipeline._report_progress("test-id", "test message", 50.0)
        callback.assert_called_once_with("test-id", "test message", 50.0)

    def test_no_progress_callback(self, pipeline_config, mock_ai):
        pipeline = BookWriterPipeline(pipeline_config, mock_ai)
        # Should not raise even without callback
        pipeline._report_progress("test-id", "test message", 50.0)
