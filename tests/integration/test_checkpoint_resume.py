#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration Test for Phase 5.2 Checkpoint Resume Capability

Demonstrates:
1. Job starts and processes some chunks
2. Job is interrupted (simulated crash)
3. Job resumes from checkpoint
4. Completed chunks are skipped
5. Only remaining chunks are processed
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from core.cache.checkpoint_manager import CheckpointManager, serialize_translation_result
from core.chunker import SmartChunker, TranslationChunk
from core.validator import TranslationResult


class TestCheckpointResumeIntegration:
    """Integration tests for checkpoint resume functionality"""

    @pytest.fixture
    def temp_checkpoint_db(self):
        """Create temporary checkpoint database"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield Path(temp_file.name)
        Path(temp_file.name).unlink()

    @pytest.fixture
    def sample_text(self):
        """Sample text for chunking"""
        return """
        Chapter 1: Introduction
        This is the first paragraph of our test document.

        Chapter 2: Methods
        This is the second chapter with more content.

        Chapter 3: Results
        The third chapter contains our findings.

        Chapter 4: Discussion
        We discuss the implications here.

        Chapter 5: Conclusion
        Final thoughts and summary.
        """

    @pytest.mark.asyncio
    async def test_interrupt_and_resume_workflow(self, temp_checkpoint_db, sample_text):
        """
        Test complete interrupt and resume workflow:
        1. Process 3 out of 5 chunks
        2. Simulate interrupt
        3. Resume and process remaining 2 chunks
        4. Verify final results contain all chunks in order
        """

        # Initialize components
        checkpoint_manager = CheckpointManager(temp_checkpoint_db)
        chunker = SmartChunker(max_chars=200, context_window=50)

        # Create chunks from sample text
        all_chunks = chunker.create_chunks(sample_text)
        job_id = "test_resume_job_001"

        print(f"\n🔧 Test Setup: Created {len(all_chunks)} chunks")

        # ===== PHASE 1: Initial Processing (Interrupted) =====
        print(f"\n📍 PHASE 1: Processing first 3 chunks...")

        # Simulate processing first 3 chunks
        completed_results_phase1 = {}
        for i, chunk in enumerate(all_chunks[:3]):
            result = TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[Translated {i+1}] {chunk.text}",
                quality_score=0.85 + (i * 0.05)
            )
            completed_results_phase1[chunk.id] = result
            print(f"   ✓ Processed chunk {i+1}: {chunk.id}")

        # Save checkpoint before "crash"
        serialized_results = {
            cid: serialize_translation_result(res)
            for cid, res in completed_results_phase1.items()
        }

        checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/test/input.txt",
            output_file="/test/output.txt",
            total_chunks=len(all_chunks),
            completed_chunk_ids=list(completed_results_phase1.keys()),
            results_data=serialized_results,
            job_metadata={"domain": "general", "mode": "simple"}
        )

        print(f"   💾 Checkpoint saved: {len(completed_results_phase1)}/{len(all_chunks)} chunks")
        print(f"   💥 [SIMULATED CRASH]")

        # ===== PHASE 2: Resume from Checkpoint =====
        print(f"\n📍 PHASE 2: Resuming from checkpoint...")

        # Load checkpoint
        checkpoint = checkpoint_manager.load_checkpoint(job_id)
        assert checkpoint is not None, "Checkpoint should exist"

        print(f"   🔄 Loaded checkpoint: {len(checkpoint.completed_chunk_ids)}/{checkpoint.total_chunks} chunks completed")
        print(f"   → {checkpoint.remaining_chunks()} chunks remaining")

        # Restore completed results
        from core.cache.checkpoint_manager import deserialize_translation_result
        restored_results = {
            int(chunk_id): deserialize_translation_result(result_data)  # Convert string keys back to int
            for chunk_id, result_data in checkpoint.results_data.items()
        }

        # Filter to only process remaining chunks
        # Note: completed_chunk_ids are strings after JSON serialization
        completed_chunk_ids_int = [int(cid) for cid in checkpoint.completed_chunk_ids]
        chunks_to_process = [c for c in all_chunks if c.id not in completed_chunk_ids_int]

        print(f"   ✓ Restored {len(restored_results)} cached results")
        print(f"   → Processing {len(chunks_to_process)} remaining chunks")

        # Process remaining chunks
        all_completed_results = restored_results.copy()
        for i, chunk in enumerate(chunks_to_process):
            result = TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[Translated {len(restored_results) + i + 1}] {chunk.text}",
                quality_score=0.90 + (i * 0.03)
            )
            all_completed_results[chunk.id] = result
            print(f"   ✓ Processed chunk {len(restored_results) + i + 1}: {chunk.id}")

        # ===== PHASE 3: Verify Results =====
        print(f"\n📍 PHASE 3: Verifying results...")

        # Merge results in original chunk order
        final_results = []
        for chunk in all_chunks:
            assert chunk.id in all_completed_results, f"Missing result for chunk {chunk.id}"
            final_results.append(all_completed_results[chunk.id])

        # Verify all chunks were processed exactly once
        assert len(final_results) == len(all_chunks), "All chunks should have results"
        assert len(set(r.chunk_id for r in final_results)) == len(all_chunks), "No duplicate results"

        # Verify chunk IDs match original order
        for i, (chunk, result) in enumerate(zip(all_chunks, final_results)):
            assert chunk.id == result.chunk_id, f"Chunk order mismatch at index {i}"

        print(f"   ✅ All {len(final_results)} chunks processed correctly")
        print(f"   ✅ Results are in correct order")
        print(f"   ✅ No duplicates or missing chunks")

        # Cleanup checkpoint after successful completion
        checkpoint_manager.delete_checkpoint(job_id)
        assert not checkpoint_manager.has_checkpoint(job_id), "Checkpoint should be deleted"

        print(f"   🗑️  Checkpoint cleaned up")
        print(f"\n✅ Resume workflow completed successfully!")

    @pytest.mark.asyncio
    async def test_multiple_interruptions(self, temp_checkpoint_db, sample_text):
        """
        Test multiple interruptions and resumes:
        1. Process 2 chunks → interrupt
        2. Resume, process 2 more → interrupt again
        3. Resume, finish remaining chunks
        """

        checkpoint_manager = CheckpointManager(temp_checkpoint_db)
        chunker = SmartChunker(max_chars=150, context_window=40)
        all_chunks = chunker.create_chunks(sample_text)
        job_id = "test_multi_resume_001"

        print(f"\n🔧 Multi-Interrupt Test: {len(all_chunks)} total chunks")

        # Track all completed results across sessions
        all_results = {}

        # Session 1: Process first 2 chunks
        print(f"\n💼 Session 1: Processing 2 chunks...")
        for i in range(2):
            chunk = all_chunks[i]
            result = TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[S1] {chunk.text}",
                quality_score=0.85
            )
            all_results[chunk.id] = result

        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/test.txt",
            output_file="/out.txt",
            total_chunks=len(all_chunks),
            completed_chunk_ids=list(all_results.keys()),
            results_data={k: serialize_translation_result(v) for k, v in all_results.items()},
            job_metadata={}
        )
        print(f"   💾 Saved: {len(all_results)} chunks")
        print(f"   💥 [INTERRUPT 1]")

        # Session 2: Resume and process 2 more
        print(f"\n💼 Session 2: Resuming...")
        checkpoint = checkpoint_manager.load_checkpoint(job_id)
        from core.cache.checkpoint_manager import deserialize_translation_result
        all_results = {
            int(k): deserialize_translation_result(v)  # Convert string keys to int
            for k, v in checkpoint.results_data.items()
        }
        print(f"   🔄 Restored {len(all_results)} results")

        for i in range(2, 4):
            if i < len(all_chunks):
                chunk = all_chunks[i]
                result = TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=f"[S2] {chunk.text}",
                    quality_score=0.90
                )
                all_results[chunk.id] = result

        checkpoint_manager.save_checkpoint(
            job_id=job_id,
            input_file="/test.txt",
            output_file="/out.txt",
            total_chunks=len(all_chunks),
            completed_chunk_ids=list(all_results.keys()),
            results_data={k: serialize_translation_result(v) for k, v in all_results.items()},
            job_metadata={}
        )
        print(f"   💾 Saved: {len(all_results)} chunks")
        print(f"   💥 [INTERRUPT 2]")

        # Session 3: Final resume and completion
        print(f"\n💼 Session 3: Final resume...")
        checkpoint = checkpoint_manager.load_checkpoint(job_id)
        all_results = {
            int(k): deserialize_translation_result(v)  # Convert string keys to int
            for k, v in checkpoint.results_data.items()
        }
        print(f"   🔄 Restored {len(all_results)} results")

        for i in range(4, len(all_chunks)):
            chunk = all_chunks[i]
            result = TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"[S3] {chunk.text}",
                quality_score=0.95
            )
            all_results[chunk.id] = result

        print(f"   ✅ Completed: {len(all_results)}/{len(all_chunks)} chunks")

        # Verify
        assert len(all_results) == len(all_chunks), "All chunks should be processed"

        # Cleanup
        checkpoint_manager.delete_checkpoint(job_id)
        print(f"   🗑️  Checkpoint cleaned up")
        print(f"\n✅ Multi-interrupt test passed!")

    def test_checkpoint_persistence_across_instances(self, temp_checkpoint_db, sample_text):
        """
        Test that checkpoints persist across different CheckpointManager instances
        (simulating process restart)
        """

        chunker = SmartChunker(max_chars=200, context_window=50)
        all_chunks = chunker.create_chunks(sample_text)
        job_id = "test_persistence_001"

        print(f"\n🔧 Persistence Test: {len(all_chunks)} chunks")

        # Instance 1: Save checkpoint
        print(f"\n💼 Instance 1: Saving checkpoint...")
        manager1 = CheckpointManager(temp_checkpoint_db)

        results = {}
        for i in range(3):
            chunk = all_chunks[i]
            result = TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"Result {i}",
                quality_score=0.9
            )
            results[chunk.id] = result

        manager1.save_checkpoint(
            job_id=job_id,
            input_file="/input.txt",
            output_file="/output.txt",
            total_chunks=len(all_chunks),
            completed_chunk_ids=list(results.keys()),
            results_data={k: serialize_translation_result(v) for k, v in results.items()},
            job_metadata={"test": "data"}
        )

        print(f"   💾 Saved checkpoint with {len(results)} results")

        # Simulate process restart by creating new instance
        print(f"\n🔄 [SIMULATED PROCESS RESTART]")
        print(f"\n💼 Instance 2: Loading checkpoint...")
        manager2 = CheckpointManager(temp_checkpoint_db)

        # Load from new instance
        checkpoint = manager2.load_checkpoint(job_id)

        assert checkpoint is not None, "Checkpoint should persist"
        assert len(checkpoint.completed_chunk_ids) == 3, "Should have 3 completed chunks"
        assert checkpoint.job_metadata["test"] == "data", "Metadata should persist"

        print(f"   ✅ Checkpoint loaded successfully from new instance")
        print(f"   ✅ Data persisted across process restart")

        # Cleanup
        manager2.delete_checkpoint(job_id)
        print(f"   🗑️  Checkpoint cleaned up")
        print(f"\n✅ Persistence test passed!")


def test_checkpoint_manager_statistics(tmp_path):
    """Test checkpoint statistics tracking"""

    db_path = tmp_path / "checkpoints_stats.db"
    manager = CheckpointManager(db_path)

    # Create multiple checkpoints with different completion rates
    for i in range(5):
        manager.save_checkpoint(
            job_id=f"job_{i}",
            input_file=f"/input_{i}.txt",
            output_file=f"/output_{i}.txt",
            total_chunks=10,
            completed_chunk_ids=[f"chunk_{j}" for j in range(i * 2)],  # 0, 2, 4, 6, 8 completed
            results_data={}
        )

    stats = manager.get_statistics()

    print(f"\n📊 Checkpoint Statistics:")
    print(f"   Total checkpoints: {stats['total_checkpoints']}")
    print(f"   Total chunks tracked: {stats['total_chunks_tracked']}")
    print(f"   Average completion: {stats['avg_completion_rate']:.1%}")
    print(f"   DB size: {stats['db_size_bytes']} bytes")

    assert stats["total_checkpoints"] == 5
    assert stats["total_chunks_tracked"] == 50  # 5 jobs × 10 chunks

    print(f"\n✅ Statistics test passed!")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
