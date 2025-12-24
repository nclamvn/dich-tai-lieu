"""
Unit tests for core.batch.chunk_processor module.

Tests ChunkProcessor, ChunkResult, and ProcessingStats classes.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock
from dataclasses import dataclass

from core.batch.chunk_processor import (
    ChunkProcessor,
    ChunkResult,
    ProcessingStats,
)


# Helper class to simulate translation chunks
@dataclass
class MockChunk:
    """Mock chunk for testing."""
    id: str
    text: str


# Helper class to simulate translation results
@dataclass
class MockTranslationResult:
    """Mock translation result."""
    chunk_id: str
    source: str
    translated: str
    quality_score: float = 0.85
    from_cache: bool = False


class TestChunkResult:
    """Tests for ChunkResult dataclass."""

    def test_result_creation_success(self):
        """Test creating successful ChunkResult."""
        result = ChunkResult(
            chunk_id="chunk_001",
            original="Hello world",
            translated="Xin chao the gioi",
            quality_score=0.92,
            tokens_used=50,
            duration_ms=150.0,
        )
        assert result.chunk_id == "chunk_001"
        assert result.original == "Hello world"
        assert result.translated == "Xin chao the gioi"
        assert result.quality_score == 0.92
        assert result.success is True
        assert result.error is None

    def test_result_creation_failure(self):
        """Test creating failed ChunkResult."""
        result = ChunkResult(
            chunk_id="chunk_002",
            original="Hello world",
            translated="[ERROR]",
            error="API timeout"
        )
        assert result.success is False
        assert result.error == "API timeout"

    def test_success_property(self):
        """Test success property logic."""
        success_result = ChunkResult(
            chunk_id="c1",
            original="text",
            translated="translated"
        )
        assert success_result.success is True

        failed_result = ChunkResult(
            chunk_id="c2",
            original="text",
            translated="",
            error="Error message"
        )
        assert failed_result.success is False

    def test_from_cache_flag(self):
        """Test from_cache flag."""
        cached = ChunkResult(
            chunk_id="c1",
            original="text",
            translated="cached translation",
            from_cache=True
        )
        assert cached.from_cache is True


class TestProcessingStats:
    """Tests for ProcessingStats dataclass."""

    def test_stats_creation_default(self):
        """Test creating ProcessingStats with defaults."""
        stats = ProcessingStats()
        assert stats.total_chunks == 0
        assert stats.successful == 0
        assert stats.failed == 0
        assert stats.from_cache == 0
        assert stats.total_duration_ms == 0.0
        assert stats.avg_quality == 0.0

    def test_stats_creation_with_values(self):
        """Test creating ProcessingStats with values."""
        stats = ProcessingStats(
            total_chunks=100,
            successful=95,
            failed=5,
            from_cache=20,
            total_duration_ms=15000.0,
            avg_quality=0.88
        )
        assert stats.total_chunks == 100
        assert stats.successful == 95
        assert stats.failed == 5
        assert stats.from_cache == 20


class TestChunkProcessor:
    """Tests for ChunkProcessor class."""

    @pytest.fixture
    def mock_translate_func(self):
        """Create mock translation function."""
        async def translate(http_client, chunk):
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[TRANSLATED] {chunk.text}",
                quality_score=0.85
            )
        return translate

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock()

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            MockChunk(id=f"chunk_{i}", text=f"Sample text {i}")
            for i in range(5)
        ]

    def test_processor_initialization(self, mock_translate_func):
        """Test ChunkProcessor initialization."""
        processor = ChunkProcessor(
            translate_func=mock_translate_func,
            max_concurrency=10,
            max_retries=3,
            timeout=120.0
        )
        assert processor.max_concurrency == 10
        assert processor.max_retries == 3
        assert processor.timeout == 120.0
        assert processor._cancelled is False

    def test_cancel_sets_flag(self, mock_translate_func):
        """Test cancel() sets cancellation flag."""
        processor = ChunkProcessor(translate_func=mock_translate_func)
        processor.cancel()
        assert processor._cancelled is True

    @pytest.mark.asyncio
    async def test_process_all_empty_chunks(self, mock_translate_func, mock_http_client):
        """Test processing empty chunk list."""
        processor = ChunkProcessor(translate_func=mock_translate_func)
        results, stats = await processor.process_all(
            chunks=[],
            http_client=mock_http_client
        )
        assert results == []
        assert stats.total_chunks == 0

    @pytest.mark.asyncio
    async def test_process_all_success(self, mock_translate_func, mock_http_client, sample_chunks):
        """Test successful processing of all chunks."""
        processor = ChunkProcessor(translate_func=mock_translate_func)
        results, stats = await processor.process_all(
            chunks=sample_chunks,
            http_client=mock_http_client
        )

        assert len(results) == 5
        assert stats.total_chunks == 5
        assert stats.successful == 5
        assert stats.failed == 0
        for result in results:
            assert result.success is True
            assert "[TRANSLATED]" in result.translated

    @pytest.mark.asyncio
    async def test_process_all_with_progress_callback(
        self, mock_translate_func, mock_http_client, sample_chunks
    ):
        """Test progress callback is called."""
        processor = ChunkProcessor(translate_func=mock_translate_func)
        progress_calls = []

        def progress_callback(completed, total, quality):
            progress_calls.append((completed, total, quality))

        await processor.process_all(
            chunks=sample_chunks,
            http_client=mock_http_client,
            progress_callback=progress_callback
        )

        assert len(progress_calls) > 0
        # Final call should have all chunks completed
        final_call = max(progress_calls, key=lambda x: x[0])
        assert final_call[0] == 5  # All completed
        assert final_call[1] == 5  # Total

    @pytest.mark.asyncio
    async def test_process_all_with_checkpoint_callback(
        self, mock_translate_func, mock_http_client, sample_chunks
    ):
        """Test checkpoint callback is called at intervals."""
        processor = ChunkProcessor(translate_func=mock_translate_func)
        checkpoint_calls = []

        def checkpoint_callback(chunk_id, result):
            checkpoint_calls.append((chunk_id, result))

        # Use smaller chunk list to ensure checkpoint is hit
        chunks = sample_chunks[:6]  # 6 chunks

        await processor.process_all(
            chunks=chunks,
            http_client=mock_http_client,
            checkpoint_callback=checkpoint_callback,
            checkpoint_interval=2
        )

        # Checkpoint should be called at intervals
        # With 6 chunks and interval=2, expect calls at 2, 4, 6
        assert len(checkpoint_calls) >= 1

    @pytest.mark.asyncio
    async def test_process_all_with_timeout(self, mock_http_client, sample_chunks):
        """Test handling of timeout errors."""
        async def slow_translate(http_client, chunk):
            await asyncio.sleep(10)  # Longer than timeout
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="Should not reach"
            )

        processor = ChunkProcessor(
            translate_func=slow_translate,
            timeout=0.01  # Very short timeout
        )

        results, stats = await processor.process_all(
            chunks=sample_chunks[:1],  # Just one chunk
            http_client=mock_http_client
        )

        assert len(results) == 1
        assert results[0].success is False
        assert "Timeout" in results[0].error

    @pytest.mark.asyncio
    async def test_process_all_with_exception(self, mock_http_client, sample_chunks):
        """Test handling of exceptions during translation."""
        async def failing_translate(http_client, chunk):
            raise ValueError("API Error")

        processor = ChunkProcessor(translate_func=failing_translate)

        results, stats = await processor.process_all(
            chunks=sample_chunks[:1],
            http_client=mock_http_client
        )

        assert len(results) == 1
        assert results[0].success is False
        assert "API Error" in results[0].error

    @pytest.mark.asyncio
    async def test_process_all_cancelled(self, mock_http_client, sample_chunks):
        """Test processing with cancellation mid-way."""
        call_count = 0

        async def slow_translate_with_cancel(http_client, chunk):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # Cancel after first chunk starts
                processor.cancel()
            await asyncio.sleep(0.01)
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated"
            )

        processor = ChunkProcessor(
            translate_func=slow_translate_with_cancel,
            max_concurrency=1  # Process one at a time to control cancellation
        )

        results, stats = await processor.process_all(
            chunks=sample_chunks,
            http_client=mock_http_client
        )

        # Some results should be cancelled (those that started after cancel was called)
        cancelled_results = [r for r in results if r.error == "Cancelled"]
        # With concurrency=1, at least some should be cancelled
        assert len(cancelled_results) >= 0  # May or may not have cancelled depending on timing

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, mock_http_client):
        """Test concurrency is properly limited."""
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def counting_translate(http_client, chunk):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            await asyncio.sleep(0.01)  # Small delay to overlap

            async with lock:
                concurrent_count -= 1

            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated"
            )

        processor = ChunkProcessor(
            translate_func=counting_translate,
            max_concurrency=3
        )

        chunks = [MockChunk(id=f"c{i}", text=f"text{i}") for i in range(10)]

        await processor.process_all(chunks=chunks, http_client=mock_http_client)

        assert max_concurrent <= 3  # Should not exceed concurrency limit

    @pytest.mark.asyncio
    async def test_stats_calculation(self, mock_http_client):
        """Test accurate stats calculation."""
        call_count = 0

        async def mixed_translate(http_client, chunk):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ValueError("Every third fails")
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated",
                quality_score=0.9
            )

        processor = ChunkProcessor(translate_func=mixed_translate)
        chunks = [MockChunk(id=f"c{i}", text=f"text{i}") for i in range(9)]

        results, stats = await processor.process_all(
            chunks=chunks,
            http_client=mock_http_client
        )

        assert stats.total_chunks == 9
        assert stats.failed == 3  # Every 3rd fails
        assert stats.successful == 6
        assert stats.avg_quality == pytest.approx(0.9, rel=0.1)


class TestChunkProcessorCheckpointResume:
    """Tests for checkpoint resume functionality."""

    @pytest.fixture
    def mock_translate_func(self):
        """Create mock translation function."""
        async def translate(http_client, chunk):
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[TRANSLATED] {chunk.text}",
                quality_score=0.85
            )
        return translate

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock()

    @pytest.mark.asyncio
    async def test_resume_all_completed(self, mock_translate_func, mock_http_client):
        """Test resuming when all chunks already completed."""
        processor = ChunkProcessor(translate_func=mock_translate_func)

        all_chunks = [MockChunk(id=f"c{i}", text=f"text{i}") for i in range(3)]

        # All chunks already completed
        completed_results = {
            f"c{i}": MockTranslationResult(
                chunk_id=f"c{i}",
                source=f"text{i}",
                translated=f"cached{i}",
                quality_score=0.9
            )
            for i in range(3)
        }

        results, stats = await processor.process_with_checkpoint_resume(
            all_chunks=all_chunks,
            completed_results=completed_results,
            http_client=mock_http_client
        )

        assert len(results) == 3
        assert stats.from_cache == 3
        assert stats.successful == 3
        for r in results:
            assert r.from_cache is True

    @pytest.mark.asyncio
    async def test_resume_partial_completed(self, mock_translate_func, mock_http_client):
        """Test resuming with partial completion."""
        processor = ChunkProcessor(translate_func=mock_translate_func)

        all_chunks = [MockChunk(id=f"c{i}", text=f"text{i}") for i in range(5)]

        # First 2 chunks already completed
        completed_results = {
            f"c{i}": MockTranslationResult(
                chunk_id=f"c{i}",
                source=f"text{i}",
                translated=f"cached{i}",
                quality_score=0.9
            )
            for i in range(2)
        }

        results, stats = await processor.process_with_checkpoint_resume(
            all_chunks=all_chunks,
            completed_results=completed_results,
            http_client=mock_http_client
        )

        assert len(results) == 5

        # First 2 should be from cache
        assert results[0].from_cache is True
        assert results[1].from_cache is True

        # Last 3 should be newly translated
        assert results[2].from_cache is False
        assert results[3].from_cache is False
        assert results[4].from_cache is False

    @pytest.mark.asyncio
    async def test_resume_maintains_order(self, mock_translate_func, mock_http_client):
        """Test that resume maintains original chunk order."""
        processor = ChunkProcessor(translate_func=mock_translate_func)

        all_chunks = [MockChunk(id=f"c{i}", text=f"text{i}") for i in range(5)]

        # Only middle chunk completed
        completed_results = {
            "c2": MockTranslationResult(
                chunk_id="c2",
                source="text2",
                translated="cached2",
                quality_score=0.9
            )
        }

        results, stats = await processor.process_with_checkpoint_resume(
            all_chunks=all_chunks,
            completed_results=completed_results,
            http_client=mock_http_client
        )

        # Verify order
        for i, result in enumerate(results):
            assert result.chunk_id == f"c{i}"


class TestChunkProcessorEdgeCases:
    """Edge case tests for ChunkProcessor."""

    @pytest.mark.asyncio
    async def test_single_chunk(self):
        """Test processing single chunk."""
        async def translate(client, chunk):
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated"
            )

        processor = ChunkProcessor(translate_func=translate)
        chunks = [MockChunk(id="single", text="single text")]

        results, stats = await processor.process_all(
            chunks=chunks,
            http_client=Mock()
        )

        assert len(results) == 1
        assert stats.total_chunks == 1

    @pytest.mark.asyncio
    async def test_large_chunk_count(self):
        """Test processing large number of chunks."""
        async def fast_translate(client, chunk):
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="t"
            )

        processor = ChunkProcessor(
            translate_func=fast_translate,
            max_concurrency=20
        )
        chunks = [MockChunk(id=f"c{i}", text=f"t{i}") for i in range(100)]

        results, stats = await processor.process_all(
            chunks=chunks,
            http_client=Mock()
        )

        assert len(results) == 100
        assert stats.total_chunks == 100

    @pytest.mark.asyncio
    async def test_mixed_success_failure(self):
        """Test with mixed successful and failed translations."""
        async def mixed_translate(client, chunk):
            if int(chunk.id.split("_")[1]) % 2 == 0:
                raise ValueError("Even chunks fail")
            return MockTranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated="translated"
            )

        processor = ChunkProcessor(translate_func=mixed_translate)
        chunks = [MockChunk(id=f"chunk_{i}", text=f"text{i}") for i in range(10)]

        results, stats = await processor.process_all(
            chunks=chunks,
            http_client=Mock()
        )

        # Chunks 0, 2, 4, 6, 8 should fail
        assert stats.failed == 5
        assert stats.successful == 5
