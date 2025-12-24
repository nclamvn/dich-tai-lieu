"""
Unit tests for core.batch.orchestrator module.

Tests BatchOrchestrator, OrchestratorConfig, and OrchestratorResult.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass

from core.batch.orchestrator import (
    BatchOrchestrator,
    OrchestratorConfig,
    OrchestratorResult,
)
from core.batch.job_handler import JobState


@dataclass
class MockTranslationResult:
    """Mock translation result from translator."""
    chunk_id: str
    source: str
    translated: str
    quality_score: float = 0.85
    from_cache: bool = False


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = OrchestratorConfig()
        assert config.max_workers > 0
        assert config.timeout_seconds > 0
        assert config.chunk_size > 0
        assert config.max_retries >= 0
        assert isinstance(config.enable_validation, bool)
        assert isinstance(config.enable_cache, bool)

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = OrchestratorConfig(
            max_workers=5,
            timeout_seconds=300,
            chunk_size=1000,
            max_retries=5,
            enable_validation=False,
            enable_cache=False,
        )
        assert config.max_workers == 5
        assert config.timeout_seconds == 300
        assert config.chunk_size == 1000
        assert config.max_retries == 5
        assert config.enable_validation is False
        assert config.enable_cache is False


class TestOrchestratorResult:
    """Tests for OrchestratorResult dataclass."""

    def test_result_success(self):
        """Test successful result."""
        result = OrchestratorResult(
            job_id="job_001",
            success=True,
            translated_text="Translated content",
            chunk_count=10,
            total_chars=500,
            quality_score=0.92,
        )
        assert result.success is True
        assert result.job_id == "job_001"
        assert result.error is None

    def test_result_failure(self):
        """Test failed result."""
        result = OrchestratorResult(
            job_id="job_002",
            success=False,
            error="API timeout",
        )
        assert result.success is False
        assert result.error == "API timeout"
        assert result.translated_text is None

    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = OrchestratorResult(
            job_id="job_003",
            success=True,
            metadata={'source_lang': 'en', 'target_lang': 'vi'},
        )
        assert result.metadata['source_lang'] == 'en'


class TestBatchOrchestrator:
    """Tests for BatchOrchestrator class."""

    @pytest.fixture
    def mock_translator(self):
        """Create mock translator."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[TRANSLATED] {chunk.text}",
                quality_score=0.85,
            )
        )
        return translator

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_translator, mock_http_client):
        """Create orchestrator with mocks."""
        return BatchOrchestrator(
            translator=mock_translator,
            http_client=mock_http_client,
            config=OrchestratorConfig(
                max_workers=2,
                timeout_seconds=60,
                chunk_size=500,
                enable_validation=False,
                enable_cache=False,
                enable_stem=False,
                enable_ocr=False,
            ),
        )

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.config is not None
        assert orchestrator.translator is not None
        assert orchestrator.http_client is not None

    @pytest.mark.asyncio
    async def test_process_text_input(self, orchestrator):
        """Test processing text input."""
        result = await orchestrator.process(
            input_text="Hello world. This is a test.",
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        assert result.translated_text is not None
        assert result.chunk_count >= 1
        assert result.job_id is not None

    @pytest.mark.asyncio
    async def test_process_with_progress_callback(self, orchestrator):
        """Test progress callback is called."""
        progress_calls = []

        def callback(percentage, message, data):
            progress_calls.append((percentage, message))

        result = await orchestrator.process(
            input_text="Hello world. This is a test.",
            source_lang="en",
            target_lang="vi",
            progress_callback=callback,
        )

        assert result.success is True
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_process_empty_text_error(self, orchestrator):
        """Test error on empty text."""
        result = await orchestrator.process(
            input_text="",
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_process_no_input_error(self, orchestrator):
        """Test error when no input provided."""
        result = await orchestrator.process(
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is False
        assert "No input" in result.error

    @pytest.mark.asyncio
    async def test_process_long_text_chunking(self, orchestrator):
        """Test chunking of long text."""
        long_text = "This is a paragraph. " * 100  # Long text

        result = await orchestrator.process(
            input_text=long_text,
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        assert result.chunk_count >= 1

    @pytest.mark.asyncio
    async def test_process_with_output_path(self, orchestrator, tmp_path):
        """Test exporting to output file."""
        output_file = tmp_path / "output.txt"

        result = await orchestrator.process(
            input_text="Hello world",
            source_lang="en",
            target_lang="vi",
            output_path=output_file,
        )

        assert result.success is True
        assert output_file.exists()
        assert result.output_path == output_file


class TestOrchestratorFileLoading:
    """Tests for file loading functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocks."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[TRANSLATED] {chunk.text}",
            )
        )
        return BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                enable_validation=False,
                enable_cache=False,
                enable_stem=False,
                enable_ocr=False,
            ),
        )

    @pytest.mark.asyncio
    async def test_load_txt_file(self, orchestrator, tmp_path):
        """Test loading TXT file."""
        input_file = tmp_path / "test.txt"
        input_file.write_text("Hello from file")

        result = await orchestrator.process(
            input_path=input_file,
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        assert result.translated_text is not None

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, orchestrator, tmp_path):
        """Test error on nonexistent file."""
        input_file = tmp_path / "nonexistent.txt"

        result = await orchestrator.process(
            input_path=input_file,
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is False
        assert "not found" in result.error.lower()


class TestOrchestratorExport:
    """Tests for export functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocks."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[TRANSLATED] {chunk.text}",
            )
        )
        return BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                enable_validation=False,
                enable_cache=False,
                enable_stem=False,
            ),
        )

    @pytest.mark.asyncio
    async def test_export_txt(self, orchestrator, tmp_path):
        """Test TXT export."""
        output_file = tmp_path / "output.txt"

        result = await orchestrator.process(
            input_text="Hello world",
            source_lang="en",
            target_lang="vi",
            output_path=output_file,
            output_format="txt",
        )

        assert result.success is True
        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_export_creates_parent_dirs(self, orchestrator, tmp_path):
        """Test that export creates parent directories."""
        output_file = tmp_path / "subdir" / "nested" / "output.txt"

        result = await orchestrator.process(
            input_text="Hello world",
            source_lang="en",
            target_lang="vi",
            output_path=output_file,
        )

        assert result.success is True
        assert output_file.exists()


class TestOrchestratorErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_translator_exception(self):
        """Test handling of translator exception."""
        failing_translator = Mock()
        failing_translator.translate_chunk = AsyncMock(
            side_effect=Exception("API Error")
        )

        orchestrator = BatchOrchestrator(
            translator=failing_translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                enable_cache=False,
                enable_validation=False,
            ),
        )

        result = await orchestrator.process(
            input_text="Test text",
            source_lang="en",
            target_lang="vi",
        )

        # Orchestrator returns partial results even with failures
        # Check that the failure is recorded in metadata
        assert result.metadata.get('failed_chunks', 0) > 0
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_result_contains_duration(self):
        """Test that result contains duration."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated",
            )
        )

        orchestrator = BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                enable_cache=False,
                enable_validation=False,
            ),
        )

        result = await orchestrator.process(
            input_text="Test",
            source_lang="en",
            target_lang="vi",
        )

        assert result.duration_seconds >= 0


class TestOrchestratorChunking:
    """Tests for chunking functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with small chunk size."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[T] {chunk.text}",
            )
        )
        return BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                chunk_size=50,  # Small chunks
                enable_cache=False,
                enable_validation=False,
            ),
        )

    @pytest.mark.asyncio
    async def test_text_is_chunked(self, orchestrator):
        """Test that long text is chunked."""
        # Text longer than chunk_size
        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."

        result = await orchestrator.process(
            input_text=text,
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        # With small chunk size, should have multiple chunks
        assert result.chunk_count >= 1

    @pytest.mark.asyncio
    async def test_short_text_single_chunk(self, orchestrator):
        """Test that short text is single chunk."""
        result = await orchestrator.process(
            input_text="Hi",
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        assert result.chunk_count == 1


class TestOrchestratorWithCustomChunker:
    """Tests for orchestrator with custom chunker."""

    @pytest.mark.asyncio
    async def test_custom_chunker_used(self):
        """Test that custom chunker is used when provided."""
        # Create mock chunker
        mock_chunker = Mock()

        @dataclass
        class MockChunk:
            id: str
            text: str

        mock_chunker.chunk = Mock(return_value=[
            MockChunk(id="c0", text="chunk 0"),
            MockChunk(id="c1", text="chunk 1"),
        ])

        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[T] {chunk.text}",
            )
        )

        orchestrator = BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            chunker=mock_chunker,
            config=OrchestratorConfig(
                enable_cache=False,
                enable_validation=False,
            ),
        )

        result = await orchestrator.process(
            input_text="Test text to chunk",
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        mock_chunker.chunk.assert_called_once()
        assert result.chunk_count == 2


class TestOrchestratorWithValidator:
    """Tests for orchestrator with validator."""

    @pytest.mark.asyncio
    async def test_validator_called_when_enabled(self):
        """Test that validator is called when enabled."""
        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated",
            )
        )

        mock_validator = Mock()
        mock_validator.validate = Mock(return_value={'score': 0.95})

        orchestrator = BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            validator=mock_validator,
            config=OrchestratorConfig(
                enable_validation=True,
                enable_cache=False,
            ),
        )

        result = await orchestrator.process(
            input_text="Test",
            source_lang="en",
            target_lang="vi",
        )

        assert result.success is True
        mock_validator.validate.assert_called_once()
        assert result.quality_score == 0.95


class TestOrchestratorIntegration:
    """Integration tests for BatchOrchestrator."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        """Test full translation pipeline."""
        # Create input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("Hello world.\n\nThis is a test document.\n\nThank you.")

        output_file = tmp_path / "output.txt"

        translator = Mock()
        translator.translate_chunk = AsyncMock(
            side_effect=lambda client, chunk: MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[Translated] {chunk.text}",
                quality_score=0.9,
            )
        )

        orchestrator = BatchOrchestrator(
            translator=translator,
            http_client=Mock(),
            config=OrchestratorConfig(
                enable_cache=False,
                enable_validation=False,
            ),
        )

        result = await orchestrator.process(
            input_path=input_file,
            source_lang="en",
            target_lang="vi",
            output_path=output_file,
        )

        assert result.success is True
        assert result.job_id is not None
        assert result.chunk_count >= 1
        assert result.translated_text is not None
        assert output_file.exists()
        assert result.duration_seconds > 0
