#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit Tests for Phase 5.3 Streaming Components

Tests cover:
- StreamingBatchProcessor batch logic
- IncrementalDocxBuilder DOCX merging
- Progress streaming functionality
- Memory cleanup verification
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

from core.streaming import (
    StreamingBatchProcessor,
    ProgressStreamer,
    IncrementalDocxBuilder,
    IncrementalPdfBuilder,
    IncrementalTxtBuilder
)
from core.validator import TranslationResult
from core.chunker import TranslationChunk
from core.job_queue import TranslationJob, JobStatus


class TestIncrementalDocxBuilder:
    """Test Incremental DOCX Builder"""

    @pytest.fixture
    def temp_output(self):
        """Create temporary output file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file.close()
        yield Path(temp_file.name)
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_add_single_batch(self, temp_output):
        """Test adding a single batch"""
        builder = IncrementalDocxBuilder(temp_output)

        # Create sample results
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Translated {i}",
                quality_score=0.9
            )
            for i in range(10)
        ]

        # Add batch
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()
        assert builder.get_batch_count() == 1

    @pytest.mark.asyncio
    async def test_add_multiple_batches(self, temp_output):
        """Test adding multiple batches"""
        builder = IncrementalDocxBuilder(temp_output)

        # Add 3 batches
        for batch_idx in range(3):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 10 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Chunk {i}",
                    quality_score=0.9
                )
                for i in range(10)
            ]
            await builder.add_batch(results, batch_idx)

        assert builder.get_batch_count() == 3

    @pytest.mark.asyncio
    async def test_merge_batches(self, temp_output):
        """Test merging all batches into final DOCX"""
        builder = IncrementalDocxBuilder(temp_output)

        # Add 2 batches
        for batch_idx in range(2):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 5 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Text {i}",
                    quality_score=0.9
                )
                for i in range(5)
            ]
            await builder.add_batch(results, batch_idx)

        # Merge
        final_file = await builder.merge_all()

        assert final_file == temp_output
        assert temp_output.exists()
        assert temp_output.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_temp_cleanup(self, temp_output):
        """Test that temporary files are cleaned up after merge"""
        builder = IncrementalDocxBuilder(temp_output)

        # Add batch
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Text {i}",
                quality_score=0.9
            )
            for i in range(5)
        ]
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()

        # Merge (should cleanup temp files)
        await builder.merge_all()

        # Temp file should be deleted
        assert not batch_file.exists()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self, temp_output):
        """Test context manager ensures cleanup even on exception"""
        builder = IncrementalDocxBuilder(temp_output)

        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Text {i}",
                quality_score=0.9
            )
            for i in range(5)
        ]

        # Use context manager and raise exception
        try:
            async with builder:
                await builder.add_batch(results, 0)
                batch_file = builder.batch_files[0]
                assert batch_file.exists(), "Batch file should exist"

                # Raise exception before merge
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass  # Expected

        # Verify cleanup happened despite exception
        assert not batch_file.exists(), "Batch file should be cleaned up"


class TestIncrementalPdfBuilder:
    """Test Incremental PDF Builder"""

    @pytest.fixture
    def temp_output(self):
        """Create temporary output file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.close()
        yield Path(temp_file.name)
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_add_single_batch(self, temp_output):
        """Test adding a single batch"""
        builder = IncrementalPdfBuilder(temp_output)

        # Create sample results
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Translated {i}",
                quality_score=0.9
            )
            for i in range(10)
        ]

        # Add batch
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()
        assert builder.get_batch_count() == 1
        assert builder.get_format() == 'pdf'

    @pytest.mark.asyncio
    async def test_add_multiple_batches(self, temp_output):
        """Test adding multiple batches"""
        builder = IncrementalPdfBuilder(temp_output)

        # Add 3 batches
        for batch_idx in range(3):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 10 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Chunk {i}",
                    quality_score=0.9
                )
                for i in range(10)
            ]
            await builder.add_batch(results, batch_idx)

        assert builder.get_batch_count() == 3

    @pytest.mark.asyncio
    async def test_merge_batches(self, temp_output):
        """Test merging all batches into final PDF"""
        builder = IncrementalPdfBuilder(temp_output)

        # Add 2 batches
        for batch_idx in range(2):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 5 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Text {i}",
                    quality_score=0.9
                )
                for i in range(5)
            ]
            await builder.add_batch(results, batch_idx)

        # Merge
        final_file = await builder.merge_all()

        assert final_file == temp_output
        assert temp_output.exists()
        assert temp_output.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_temp_cleanup(self, temp_output):
        """Test that temporary files are cleaned up after merge"""
        builder = IncrementalPdfBuilder(temp_output)

        # Add batch
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Text {i}",
                quality_score=0.9
            )
            for i in range(5)
        ]
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()

        # Merge (should cleanup temp files)
        await builder.merge_all()

        # Temp file should be deleted
        assert not batch_file.exists()


class TestIncrementalTxtBuilder:
    """Test Incremental TXT Builder"""

    @pytest.fixture
    def temp_output(self):
        """Create temporary output file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        temp_file.close()
        yield Path(temp_file.name)
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_add_single_batch(self, temp_output):
        """Test adding a single batch"""
        builder = IncrementalTxtBuilder(temp_output)

        # Create sample results
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Translated {i}",
                quality_score=0.9
            )
            for i in range(10)
        ]

        # Add batch
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()
        assert builder.get_batch_count() == 1
        assert builder.get_format() == 'txt'

    @pytest.mark.asyncio
    async def test_add_multiple_batches(self, temp_output):
        """Test adding multiple batches"""
        builder = IncrementalTxtBuilder(temp_output)

        # Add 3 batches
        for batch_idx in range(3):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 10 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Chunk {i}",
                    quality_score=0.9
                )
                for i in range(10)
            ]
            await builder.add_batch(results, batch_idx)

        assert builder.get_batch_count() == 3

    @pytest.mark.asyncio
    async def test_merge_batches(self, temp_output):
        """Test merging all batches into final TXT"""
        builder = IncrementalTxtBuilder(temp_output)

        # Add 2 batches
        for batch_idx in range(2):
            results = [
                TranslationResult(
                    chunk_id=batch_idx * 5 + i,
                    source=f"Source {i}",
                    translated=f"Batch {batch_idx}, Text {i}",
                    quality_score=0.9
                )
                for i in range(5)
            ]
            await builder.add_batch(results, batch_idx)

        # Merge
        final_file = await builder.merge_all()

        assert final_file == temp_output
        assert temp_output.exists()
        assert temp_output.stat().st_size > 0

        # Verify content is readable
        content = temp_output.read_text(encoding='utf-8')
        assert len(content) > 0
        assert "Batch 0, Text 0" in content
        assert "Batch 1, Text 4" in content

    @pytest.mark.asyncio
    async def test_temp_cleanup(self, temp_output):
        """Test that temporary files are cleaned up after merge"""
        builder = IncrementalTxtBuilder(temp_output)

        # Add batch
        results = [
            TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Text {i}",
                quality_score=0.9
            )
            for i in range(5)
        ]
        batch_file = await builder.add_batch(results, 0)

        assert batch_file.exists()

        # Merge (should cleanup temp files)
        await builder.merge_all()

        # Temp file should be deleted
        assert not batch_file.exists()


class TestProgressStreamer:
    """Test Progress Streamer"""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager"""
        manager = AsyncMock()
        manager.broadcast = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_broadcast_job_started(self, mock_websocket_manager):
        """Test job started event broadcast"""
        streamer = ProgressStreamer(mock_websocket_manager)

        await streamer.broadcast_job_started(
            job_id="test_job",
            total_chunks=100,
            total_batches=10
        )

        mock_websocket_manager.broadcast.assert_called_once()
        call_args = mock_websocket_manager.broadcast.call_args[0][0]

        assert call_args["event"] == "job_started"
        assert call_args["job_id"] == "test_job"
        assert call_args["total_chunks"] == 100
        assert call_args["total_batches"] == 10

    @pytest.mark.asyncio
    async def test_broadcast_chunk_translated(self, mock_websocket_manager):
        """Test chunk translated event broadcast"""
        streamer = ProgressStreamer(mock_websocket_manager)

        await streamer.broadcast_chunk_translated(
            job_id="test_job",
            chunk_id="chunk_1",
            preview="This is a preview...",
            quality_score=0.92
        )

        call_args = mock_websocket_manager.broadcast.call_args[0][0]

        assert call_args["event"] == "chunk_translated"
        assert call_args["chunk_id"] == "chunk_1"
        assert call_args["quality_score"] == 0.92

    @pytest.mark.asyncio
    async def test_broadcast_batch_completed(self, mock_websocket_manager):
        """Test batch completed event broadcast"""
        streamer = ProgressStreamer(mock_websocket_manager)

        await streamer.broadcast_batch_completed(
            job_id="test_job",
            batch_idx=3,
            total_batches=10,
            progress=0.3,
            chunks_completed=30
        )

        call_args = mock_websocket_manager.broadcast.call_args[0][0]

        assert call_args["event"] == "batch_completed"
        assert call_args["batch"] == 3
        assert call_args["progress"] == 0.3

    @pytest.mark.asyncio
    async def test_broadcast_job_completed(self, mock_websocket_manager):
        """Test job completed event broadcast"""
        streamer = ProgressStreamer(mock_websocket_manager)

        await streamer.broadcast_job_completed(
            job_id="test_job",
            total_chunks=100,
            memory_saved_mb=150.5
        )

        call_args = mock_websocket_manager.broadcast.call_args[0][0]

        assert call_args["event"] == "job_completed"
        assert call_args["total_chunks"] == 100
        assert call_args["memory_saved_mb"] == 150.5

    @pytest.mark.asyncio
    async def test_broadcast_error_handling(self):
        """Test that broadcast errors don't crash the job"""
        # Create manager that raises exception
        failing_manager = AsyncMock()
        failing_manager.broadcast = AsyncMock(side_effect=Exception("WebSocket error"))

        streamer = ProgressStreamer(failing_manager)

        # Should not raise exception
        try:
            await streamer.broadcast_chunk_translated(
                job_id="test",
                chunk_id="chunk_1",
                preview="preview",
                quality_score=0.9
            )
        except Exception:
            pytest.fail("Broadcast error should be caught")


class TestStreamingBatchProcessorConfig:
    """Test StreamingBatchProcessor configuration and initialization"""

    def test_initialization_default(self):
        """Test default initialization"""
        processor = StreamingBatchProcessor()

        assert processor.batch_size == 100
        assert processor.enable_streaming is True
        assert processor.enable_partial_export is True

    def test_initialization_custom(self):
        """Test custom initialization"""
        mock_ws_manager = Mock()

        processor = StreamingBatchProcessor(
            batch_size=50,
            enable_streaming=False,
            enable_partial_export=False,
            websocket_manager=mock_ws_manager
        )

        assert processor.batch_size == 50
        assert processor.enable_streaming is False
        assert processor.enable_partial_export is False
        assert processor.websocket_manager == mock_ws_manager

    def test_get_statistics(self):
        """Test statistics retrieval"""
        processor = StreamingBatchProcessor(batch_size=75)

        stats = processor.get_statistics()

        assert stats['batch_size'] == 75
        assert stats['streaming_enabled'] is True
        assert 'has_websocket' in stats

    def test_builder_factory_docx(self):
        """Test factory creates correct DOCX builder"""
        processor = StreamingBatchProcessor()

        temp_file = Path(tempfile.mktemp(suffix='.docx'))
        builder = processor._create_builder('docx', temp_file)

        assert isinstance(builder, IncrementalDocxBuilder)
        assert builder.get_format() == 'docx'

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_builder_factory_pdf(self):
        """Test factory creates correct PDF builder"""
        processor = StreamingBatchProcessor()

        temp_file = Path(tempfile.mktemp(suffix='.pdf'))
        builder = processor._create_builder('pdf', temp_file)

        assert isinstance(builder, IncrementalPdfBuilder)
        assert builder.get_format() == 'pdf'

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_builder_factory_txt(self):
        """Test factory creates correct TXT builder"""
        processor = StreamingBatchProcessor()

        temp_file = Path(tempfile.mktemp(suffix='.txt'))
        builder = processor._create_builder('txt', temp_file)

        assert isinstance(builder, IncrementalTxtBuilder)
        assert builder.get_format() == 'txt'

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_builder_factory_unsupported(self):
        """Test factory raises error for unsupported format"""
        processor = StreamingBatchProcessor()

        temp_file = Path(tempfile.mktemp(suffix='.json'))

        with pytest.raises(ValueError, match="Unsupported output format"):
            processor._create_builder('json', temp_file)

        # Cleanup
        temp_file.unlink(missing_ok=True)


class TestStreamingBatchProcessorBatching:
    """Test batch logic and chunk distribution"""

    def test_batch_calculation(self):
        """Test batch size calculation"""
        processor = StreamingBatchProcessor(batch_size=100)

        # 250 chunks should create 3 batches (100, 100, 50)
        total_chunks = 250
        total_batches = (total_chunks + processor.batch_size - 1) // processor.batch_size

        assert total_batches == 3

    def test_batch_distribution(self):
        """Test how chunks are distributed across batches"""
        processor = StreamingBatchProcessor(batch_size=100)

        chunks = list(range(250))  # 250 items
        batches = []

        for batch_idx in range(3):
            start = batch_idx * processor.batch_size
            end = min(start + processor.batch_size, len(chunks))
            batch = chunks[start:end]
            batches.append(batch)

        assert len(batches[0]) == 100  # First batch: full
        assert len(batches[1]) == 100  # Second batch: full
        assert len(batches[2]) == 50   # Third batch: partial


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
