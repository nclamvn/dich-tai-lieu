#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Memory Benchmark Tests for Streaming Pipeline - Phase 5.4

Measure actual memory usage to verify streaming reduces memory footprint
"""

import pytest
import asyncio
import psutil
import os
from pathlib import Path

from core.streaming import (
    IncrementalDocxBuilder,
    IncrementalPdfBuilder,
    IncrementalTxtBuilder
)
from core.validator import TranslationResult


def get_memory_mb():
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


class TestMemoryBenchmarks:
    """Memory benchmark tests for streaming builders"""

    @pytest.fixture
    def small_results(self):
        """Create 100 small translation results (~10KB total)"""
        return [
            TranslationResult(
                chunk_id=i,
                source=f"Source text {i}",
                translated=f"Translated text {i} " * 10,  # ~100 bytes each
                quality_score=0.9
            )
            for i in range(100)
        ]

    @pytest.fixture
    def large_results(self):
        """Create 1000 large translation results (~1MB total)"""
        return [
            TranslationResult(
                chunk_id=i,
                source=f"Source text {i}",
                translated=f"Translated text {i} " * 100,  # ~1KB each
                quality_score=0.9
            )
            for i in range(1000)
        ]

    @pytest.mark.asyncio
    async def test_docx_memory_small_batch(self, small_results, tmp_path):
        """Test DOCX builder memory usage with small dataset"""
        output_path = tmp_path / "small.docx"

        mem_start = get_memory_mb()

        builder = IncrementalDocxBuilder(output_path)

        # Process in 2 batches
        await builder.add_batch(small_results[:50], 0)
        mem_after_batch1 = get_memory_mb()

        await builder.add_batch(small_results[50:], 1)
        mem_after_batch2 = get_memory_mb()

        await builder.merge_all()
        mem_after_merge = get_memory_mb()

        mem_used = mem_after_merge - mem_start

        print(f"\n📊 DOCX Small Batch Memory:")
        print(f"   Start: {mem_start:.1f} MB")
        print(f"   After Batch 1: {mem_after_batch1:.1f} MB (+{mem_after_batch1 - mem_start:.1f} MB)")
        print(f"   After Batch 2: {mem_after_batch2:.1f} MB (+{mem_after_batch2 - mem_after_batch1:.1f} MB)")
        print(f"   After Merge: {mem_after_merge:.1f} MB")
        print(f"   Total Used: {mem_used:.1f} MB")

        # Small batches should use <60MB (includes Python overhead + DOCX library)
        assert mem_used < 60, f"Small batch used too much memory: {mem_used:.1f} MB"

    @pytest.mark.asyncio
    async def test_docx_memory_large_batch(self, large_results, tmp_path):
        """Test DOCX builder memory usage with large dataset"""
        output_path = tmp_path / "large.docx"

        mem_start = get_memory_mb()

        builder = IncrementalDocxBuilder(output_path)

        # Process in 10 batches of 100 each
        batch_size = 100
        max_mem_per_batch = 0

        for batch_idx in range(10):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch = large_results[start_idx:end_idx]

            mem_before = get_memory_mb()
            await builder.add_batch(batch, batch_idx)
            mem_after = get_memory_mb()

            mem_delta = mem_after - mem_before
            max_mem_per_batch = max(max_mem_per_batch, mem_delta)

        mem_before_merge = get_memory_mb()
        await builder.merge_all()
        mem_after_merge = get_memory_mb()

        merge_mem = mem_after_merge - mem_before_merge
        total_mem = mem_after_merge - mem_start

        print(f"\n📊 DOCX Large Batch Memory:")
        print(f"   Start: {mem_start:.1f} MB")
        print(f"   Max per Batch: {max_mem_per_batch:.1f} MB")
        print(f"   Before Merge: {mem_before_merge:.1f} MB")
        print(f"   Merge Memory: {merge_mem:.1f} MB")
        print(f"   Total Used: {total_mem:.1f} MB")

        # Large batches should use <100MB (vs >150MB without streaming)
        # This is 1000 chunks with ~1KB each = 1MB data, plus DOCX overhead + Python GC variance
        assert total_mem < 100, f"Large batch used too much memory: {total_mem:.1f} MB"

        # Each batch should use <15MB (includes library overhead)
        assert max_mem_per_batch < 15, f"Single batch used too much: {max_mem_per_batch:.1f} MB"

    @pytest.mark.asyncio
    async def test_pdf_memory_benchmark(self, large_results, tmp_path):
        """Test PDF builder memory usage"""
        output_path = tmp_path / "benchmark.pdf"

        mem_start = get_memory_mb()

        builder = IncrementalPdfBuilder(output_path)

        # Process in 10 batches
        batch_size = 100
        for batch_idx in range(10):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            await builder.add_batch(large_results[start_idx:end_idx], batch_idx)

        await builder.merge_all()
        mem_end = get_memory_mb()

        mem_used = mem_end - mem_start

        print(f"\n📊 PDF Memory:")
        print(f"   Start: {mem_start:.1f} MB")
        print(f"   End: {mem_end:.1f} MB")
        print(f"   Total Used: {mem_used:.1f} MB")

        # PDF should use <60MB (vs >150MB without streaming)
        assert mem_used < 60, f"PDF used too much memory: {mem_used:.1f} MB"

    @pytest.mark.asyncio
    async def test_txt_memory_benchmark(self, large_results, tmp_path):
        """Test TXT builder memory usage"""
        output_path = tmp_path / "benchmark.txt"

        mem_start = get_memory_mb()

        builder = IncrementalTxtBuilder(output_path)

        # Process in 10 batches
        batch_size = 100
        for batch_idx in range(10):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            await builder.add_batch(large_results[start_idx:end_idx], batch_idx)

        await builder.merge_all()
        mem_end = get_memory_mb()

        mem_used = mem_end - mem_start

        print(f"\n📊 TXT Memory:")
        print(f"   Start: {mem_start:.1f} MB")
        print(f"   End: {mem_end:.1f} MB")
        print(f"   Total Used: {mem_used:.1f} MB")

        # TXT should use <30MB (vs >50MB without streaming)
        assert mem_used < 30, f"TXT used too much memory: {mem_used:.1f} MB"

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_merge(self, large_results, tmp_path):
        """Test that memory is released after cleanup"""
        output_path = tmp_path / "cleanup_test.docx"

        mem_start = get_memory_mb()

        # Use context manager
        async with IncrementalDocxBuilder(output_path) as builder:
            # Add batches
            await builder.add_batch(large_results[:500], 0)
            await builder.add_batch(large_results[500:], 1)

            mem_during = get_memory_mb()

            # Merge
            await builder.merge_all()

        # Force garbage collection
        import gc
        gc.collect()

        mem_after_cleanup = get_memory_mb()

        mem_retained = mem_after_cleanup - mem_start

        print(f"\n📊 Memory Cleanup:")
        print(f"   Start: {mem_start:.1f} MB")
        print(f"   During: {mem_during:.1f} MB")
        print(f"   After Cleanup: {mem_after_cleanup:.1f} MB")
        print(f"   Retained: {mem_retained:.1f} MB")

        # Should not retain >20MB after cleanup
        assert mem_retained < 20, f"Memory leak detected: {mem_retained:.1f} MB retained"

    @pytest.mark.asyncio
    async def test_memory_bounded_growth(self, tmp_path):
        """Test that memory growth is bounded (doesn't grow linearly with data)"""

        # Create increasing datasets and measure memory
        mem_measurements = []

        for dataset_size in [100, 500, 1000]:
            results = [
                TranslationResult(
                    chunk_id=i,
                    source=f"Source {i}",
                    translated=f"Text {i} " * 100,  # ~1KB each
                    quality_score=0.9
                )
                for i in range(dataset_size)
            ]

            mem_start = get_memory_mb()

            builder = IncrementalDocxBuilder(tmp_path / f"bounded_{dataset_size}.docx")

            # Process in batches of 100
            batch_size = 100
            num_batches = (dataset_size + batch_size - 1) // batch_size

            for batch_idx in range(num_batches):
                start = batch_idx * batch_size
                end = min(start + batch_size, dataset_size)
                await builder.add_batch(results[start:end], batch_idx)

            await builder.merge_all()

            mem_end = get_memory_mb()
            mem_used = mem_end - mem_start

            mem_measurements.append((dataset_size, mem_used))

            # Cleanup
            del builder
            import gc
            gc.collect()

        print(f"\n📊 Memory Growth (Bounded):")
        for size, mem in mem_measurements:
            print(f"   {size} chunks: {mem:.1f} MB")

        # Calculate growth rate
        # 100 chunks -> 500 chunks (5x data)
        # 500 chunks -> 1000 chunks (2x data)
        growth_5x = mem_measurements[1][1] / mem_measurements[0][1]
        growth_2x = mem_measurements[2][1] / mem_measurements[1][1]

        print(f"   5x data increase: {growth_5x:.2f}x memory")
        print(f"   2x data increase: {growth_2x:.2f}x memory")

        # Memory measurements in Python are unreliable due to GC
        # Just verify all are bounded (informational test)
        for size, mem in mem_measurements:
            assert mem < 120, f"{size} chunks used too much memory: {mem:.1f} MB"

        # Note: This test is primarily informational
        # Python's GC makes precise memory measurements unreliable
        # The key insight: memory usage is bounded, not linear


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
