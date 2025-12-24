#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit Tests for Phase 5.2 Checkpoint Manager

Tests cover:
- Checkpoint save/load operations
- Resume state management
- Data serialization/deserialization
- Database persistence
- Cleanup operations
- Edge cases and error handling
"""

import pytest
import os
import tempfile
import time
from pathlib import Path

from core.cache.checkpoint_manager import (
    CheckpointManager,
    CheckpointState,
    serialize_translation_result,
    deserialize_translation_result
)
from core.validator import TranslationResult


class TestCheckpointManager:
    """Test CheckpointManager class operations"""

    @pytest.fixture
    def temp_checkpoint_manager(self):
        """Create temporary checkpoint manager for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        manager = CheckpointManager(temp_file.name)
        yield manager
        os.unlink(temp_file.name)

    def test_save_and_load_checkpoint(self, temp_checkpoint_manager):
        """Test basic save and load operations"""
        job_id = "test_job_001"
        completed_ids = ["chunk_1", "chunk_2", "chunk_3"]
        results_data = {
            "chunk_1": {"translated": "Result 1", "quality_score": 0.9},
            "chunk_2": {"translated": "Result 2", "quality_score": 0.85},
        }

        # Save checkpoint
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/path/to/input.pdf",
            output_file="/path/to/output.docx",
            total_chunks=10,
            completed_chunk_ids=completed_ids,
            results_data=results_data,
            job_metadata={"domain": "stem", "mode": "academic"}
        )

        # Load checkpoint
        checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)

        assert checkpoint is not None, "Checkpoint should be loaded"
        assert checkpoint.job_id == job_id
        assert checkpoint.total_chunks == 10
        assert checkpoint.completed_chunk_ids == completed_ids
        assert checkpoint.results_data == results_data
        assert checkpoint.job_metadata["domain"] == "stem"

    def test_has_checkpoint(self, temp_checkpoint_manager):
        """Test checkpoint existence check"""
        job_id = "test_job_002"

        # Before saving
        assert not temp_checkpoint_manager.has_checkpoint(job_id)

        # After saving
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=5,
            completed_chunk_ids=[],
            results_data={}
        )

        assert temp_checkpoint_manager.has_checkpoint(job_id)

    def test_update_checkpoint(self, temp_checkpoint_manager):
        """Test updating an existing checkpoint"""
        job_id = "test_job_003"

        # Initial save
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=10,
            completed_chunk_ids=["chunk_1"],
            results_data={"chunk_1": {"translated": "Result 1"}}
        )

        initial_checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)
        initial_created_at = initial_checkpoint.created_at

        # Wait a bit to ensure timestamp difference
        time.sleep(0.1)

        # Update with more chunks
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=10,
            completed_chunk_ids=["chunk_1", "chunk_2", "chunk_3"],
            results_data={
                "chunk_1": {"translated": "Result 1"},
                "chunk_2": {"translated": "Result 2"},
                "chunk_3": {"translated": "Result 3"}
            }
        )

        updated_checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)

        assert len(updated_checkpoint.completed_chunk_ids) == 3
        assert updated_checkpoint.created_at == initial_created_at  # Created time unchanged
        assert updated_checkpoint.updated_at > initial_checkpoint.updated_at  # Updated time changed

    def test_delete_checkpoint(self, temp_checkpoint_manager):
        """Test checkpoint deletion"""
        job_id = "test_job_004"

        # Save checkpoint
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=5,
            completed_chunk_ids=[],
            results_data={}
        )

        assert temp_checkpoint_manager.has_checkpoint(job_id)

        # Delete checkpoint
        deleted = temp_checkpoint_manager.delete_checkpoint(job_id)

        assert deleted is True
        assert not temp_checkpoint_manager.has_checkpoint(job_id)

        # Try deleting non-existent checkpoint
        deleted_again = temp_checkpoint_manager.delete_checkpoint(job_id)
        assert deleted_again is False

    def test_list_checkpoints(self, temp_checkpoint_manager):
        """Test listing all checkpoints"""
        # Save multiple checkpoints
        for i in range(5):
            temp_checkpoint_manager.save_checkpoint(
                job_id=f"job_{i}",
                input_file=f"/input_{i}.pdf",
                output_file=f"/output_{i}.docx",
                total_chunks=10,
                completed_chunk_ids=[],
                results_data={}
            )
            time.sleep(0.01)  # Ensure different timestamps

        checkpoints = temp_checkpoint_manager.list_checkpoints()

        assert len(checkpoints) == 5
        # Should be sorted by updated_at DESC
        assert checkpoints[0].job_id == "job_4"
        assert checkpoints[4].job_id == "job_0"

    def test_get_resume_info(self, temp_checkpoint_manager):
        """Test getting resume information"""
        job_id = "test_job_005"

        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=20,
            completed_chunk_ids=["c1", "c2", "c3", "c4", "c5"],
            results_data={}
        )

        resume_info = temp_checkpoint_manager.get_resume_info(job_id)

        assert resume_info is not None
        assert resume_info["total_chunks"] == 20
        assert resume_info["completed_chunks"] == 5
        assert resume_info["remaining_chunks"] == 15
        assert resume_info["completion_percentage"] == 0.25
        assert resume_info["can_resume"] is True

    def test_cleanup_old_checkpoints(self, temp_checkpoint_manager):
        """Test cleanup of old checkpoints"""
        # Create checkpoint with old timestamp
        job_id = "old_job"
        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=10,
            completed_chunk_ids=[],
            results_data={}
        )

        # Manually update timestamp to 10 days ago
        import sqlite3
        old_timestamp = time.time() - (10 * 86400)
        with sqlite3.connect(temp_checkpoint_manager.db_path) as conn:
            conn.execute(
                "UPDATE checkpoints SET updated_at = ? WHERE job_id = ?",
                (old_timestamp, job_id)
            )
            conn.commit()

        # Create recent checkpoint
        temp_checkpoint_manager.save_checkpoint(
            job_id="recent_job",
            input_file="/input2.pdf",
            output_file="/output2.docx",
            total_chunks=10,
            completed_chunk_ids=[],
            results_data={}
        )

        # Cleanup checkpoints older than 7 days
        deleted_count = temp_checkpoint_manager.cleanup_old_checkpoints(days=7)

        assert deleted_count == 1
        assert not temp_checkpoint_manager.has_checkpoint("old_job")
        assert temp_checkpoint_manager.has_checkpoint("recent_job")

    def test_get_statistics(self, temp_checkpoint_manager):
        """Test getting checkpoint statistics"""
        # Create several checkpoints with different completion rates
        temp_checkpoint_manager.save_checkpoint(
            job_id="job_1",
            input_file="/input1.pdf",
            output_file="/output1.docx",
            total_chunks=10,
            completed_chunk_ids=["c1", "c2", "c3", "c4", "c5"],  # 50% complete
            results_data={}
        )

        temp_checkpoint_manager.save_checkpoint(
            job_id="job_2",
            input_file="/input2.pdf",
            output_file="/output2.docx",
            total_chunks=20,
            completed_chunk_ids=[],  # 0% complete
            results_data={}
        )

        stats = temp_checkpoint_manager.get_statistics()

        assert stats["total_checkpoints"] == 2
        assert stats["total_chunks_tracked"] == 30
        assert stats["db_size_bytes"] > 0


class TestCheckpointState:
    """Test CheckpointState data class"""

    def test_completion_percentage(self):
        """Test completion percentage calculation"""
        state = CheckpointState(
            job_id="test",
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=20,
            completed_chunk_ids=["c1", "c2", "c3", "c4", "c5"],
            results_data={},
            job_metadata={},
            created_at=time.time(),
            updated_at=time.time()
        )

        assert state.completion_percentage() == 0.25  # 5/20 = 25%

    def test_remaining_chunks(self):
        """Test remaining chunks calculation"""
        state = CheckpointState(
            job_id="test",
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=100,
            completed_chunk_ids=["c" + str(i) for i in range(75)],
            results_data={},
            job_metadata={},
            created_at=time.time(),
            updated_at=time.time()
        )

        assert state.remaining_chunks() == 25

    def test_zero_chunks_edge_case(self):
        """Test edge case with zero total chunks"""
        state = CheckpointState(
            job_id="test",
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=0,
            completed_chunk_ids=[],
            results_data={},
            job_metadata={},
            created_at=time.time(),
            updated_at=time.time()
        )

        assert state.completion_percentage() == 0.0
        assert state.remaining_chunks() == 0


class TestSerializationHelpers:
    """Test serialization/deserialization helpers"""

    def test_serialize_translation_result(self):
        """Test serialization of TranslationResult"""
        result = TranslationResult(
            chunk_id="chunk_123",
            source="Hello world",
            translated="Xin chào thế giới",
            quality_score=0.92,
            warnings=["Warning 1", "Warning 2"]
        )

        serialized = serialize_translation_result(result)

        assert serialized["chunk_id"] == "chunk_123"
        assert serialized["source"] == "Hello world"
        assert serialized["translated"] == "Xin chào thế giới"
        assert serialized["quality_score"] == 0.92
        assert serialized["warnings"] == ["Warning 1", "Warning 2"]

    def test_deserialize_translation_result(self):
        """Test deserialization of TranslationResult"""
        data = {
            "chunk_id": "chunk_456",
            "source": "Goodbye",
            "translated": "Tạm biệt",
            "quality_score": 0.88,
            "warnings": []
        }

        result = deserialize_translation_result(data)

        assert isinstance(result, TranslationResult)
        assert result.chunk_id == "chunk_456"
        assert result.source == "Goodbye"
        assert result.translated == "Tạm biệt"
        assert result.quality_score == 0.88
        assert result.warnings == []

    def test_roundtrip_serialization(self):
        """Test serialize -> deserialize roundtrip"""
        original = TranslationResult(
            chunk_id="chunk_789",
            source="Test text",
            translated="Văn bản kiểm tra",
            quality_score=0.95,
            warnings=["Test warning"]
        )

        serialized = serialize_translation_result(original)
        deserialized = deserialize_translation_result(serialized)

        assert deserialized.chunk_id == original.chunk_id
        assert deserialized.source == original.source
        assert deserialized.translated == original.translated
        assert deserialized.quality_score == original.quality_score
        assert deserialized.warnings == original.warnings


class TestCheckpointEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def temp_checkpoint_manager(self):
        """Create temporary checkpoint manager for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        manager = CheckpointManager(temp_file.name)
        yield manager
        os.unlink(temp_file.name)

    def test_load_nonexistent_checkpoint(self, temp_checkpoint_manager):
        """Test loading checkpoint that doesn't exist"""
        checkpoint = temp_checkpoint_manager.load_checkpoint("nonexistent_job")
        assert checkpoint is None

    def test_get_resume_info_nonexistent(self, temp_checkpoint_manager):
        """Test getting resume info for nonexistent checkpoint"""
        info = temp_checkpoint_manager.get_resume_info("nonexistent_job")
        assert info is None

    def test_empty_metadata(self, temp_checkpoint_manager):
        """Test checkpoint with empty metadata"""
        job_id = "test_empty_metadata"

        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=5,
            completed_chunk_ids=[],
            results_data={},
            job_metadata=None  # Explicitly None
        )

        checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)
        assert checkpoint.job_metadata == {}

    def test_large_results_data(self, temp_checkpoint_manager):
        """Test checkpoint with large results dataset"""
        job_id = "test_large_data"

        # Create 1000 fake results
        large_results = {
            f"chunk_{i}": {
                "translated": f"Translation {i}" * 100,  # Long text
                "quality_score": 0.9
            }
            for i in range(1000)
        }

        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=1000,
            completed_chunk_ids=[f"chunk_{i}" for i in range(1000)],
            results_data=large_results
        )

        checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)
        assert len(checkpoint.results_data) == 1000
        assert checkpoint.completion_percentage() == 1.0

    def test_unicode_in_results(self, temp_checkpoint_manager):
        """Test handling of Unicode characters in results"""
        job_id = "test_unicode"

        results_data = {
            "chunk_1": {
                "translated": "Tiếng Việt có dấu: àáảãạ ơớợờỡ",
                "quality_score": 0.95
            },
            "chunk_2": {
                "translated": "中文字符测试",
                "quality_score": 0.90
            },
            "chunk_3": {
                "translated": "العربية اختبار",
                "quality_score": 0.88
            }
        }

        temp_checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/input.pdf",
            output_file="/output.docx",
            total_chunks=3,
            completed_chunk_ids=["chunk_1", "chunk_2", "chunk_3"],
            results_data=results_data
        )

        checkpoint = temp_checkpoint_manager.load_checkpoint(job_id)
        assert checkpoint.results_data["chunk_1"]["translated"] == "Tiếng Việt có dấu: àáảãạ ơớợờỡ"
        assert checkpoint.results_data["chunk_2"]["translated"] == "中文字符测试"
        assert checkpoint.results_data["chunk_3"]["translated"] == "العربية اختبار"
