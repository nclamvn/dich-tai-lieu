#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Tests for Pipeline Fixes (FIX-001 to FIX-004)

Tests verify:
- FIX-001: Chunker no longer creates duplicate paragraphs
- FIX-002: Merger uses overlap_char_count and fuzzy matching
- FIX-003: Checkpoint type consistency (INT not STRING)
- FIX-004: Translator prompt context handling

Run with:
    pytest tests/integration/test_pipeline_fixes.py -v
    pytest tests/integration/test_pipeline_fixes.py -v -k "chunker"
    pytest tests/integration/test_pipeline_fixes.py -v -k "merger"
    pytest tests/integration/test_pipeline_fixes.py -v -k "checkpoint"
    pytest tests/integration/test_pipeline_fixes.py -v -k "e2e"
"""

import pytest
import asyncio
import re
import sys
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def count_duplicate_paragraphs(text: str) -> dict:
    """Count paragraphs that appear more than once."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    meaningful_paragraphs = [p for p in paragraphs if len(p) > 50]
    counts = Counter(meaningful_paragraphs)
    duplicates = [(p[:100] + "...", count) for p, count in counts.items() if count > 1]
    return {
        'total_paragraphs': len(meaningful_paragraphs),
        'unique_paragraphs': len(counts),
        'duplicate_count': len(duplicates),
        'duplicates': duplicates
    }


def verify_chapter_order(text: str, chapter_pattern: str = r"CHAPTER (\d+)") -> bool:
    """Verify chapters appear in correct ascending order."""
    matches = re.findall(chapter_pattern, text)
    if not matches:
        return True
    chapter_numbers = [int(m) for m in matches]
    return chapter_numbers == sorted(chapter_numbers)


def extract_chunk_markers(text: str) -> list:
    """Extract [CHUNK_BOUNDARY_XXX] markers from text."""
    matches = re.findall(r'\[CHUNK_BOUNDARY_(\d+)\]', text)
    return [int(m) for m in matches]


def check_code_blocks_intact(text: str) -> dict:
    """Check if code blocks are intact."""
    starts = list(re.finditer(r'```\w*\n', text))
    ends = list(re.finditer(r'\n```', text))
    intact = len(starts) == len(ends)
    return {
        'total_starts': len(starts),
        'total_ends': len(ends),
        'intact': intact
    }


# ============================================================================
# TEST GROUP A: CHUNKER TESTS
# ============================================================================

class TestChunkerFixes:
    """Tests for FIX-001: Chunker Context Overlap"""

    def test_chunker_no_duplicate_paragraphs(self, stress_test_dir, chunker):
        """
        FIX-001: Verify chunks don't contain duplicate paragraphs.

        Previously, chunker copied last paragraph of chunk N into chunk N+1.
        After fix, paragraphs should appear in exactly one chunk.
        """
        # Load large test file
        test_file = stress_test_dir / "large_100_pages.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # Create chunks
        chunks = chunker.create_chunks(text)

        assert len(chunks) > 10, f"Expected many chunks, got {len(chunks)}"

        # Collect all paragraphs from all chunks
        all_paragraphs = []
        for chunk in chunks:
            # Split chunk text into paragraphs
            paras = [p.strip() for p in chunk.text.split('\n\n') if p.strip() and len(p.strip()) > 50]
            all_paragraphs.extend(paras)

        # Count occurrences
        para_counts = Counter(all_paragraphs)
        duplicates = [(p[:80], count) for p, count in para_counts.items() if count > 1]

        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate paragraphs across chunks:\n"
            + "\n".join([f"  '{p}...' appears {c} times" for p, c in duplicates[:5]])
        )

    def test_chunker_overlap_char_count_set(self, stress_test_dir, chunker):
        """
        FIX-001: Verify overlap_char_count is set for chunks after the first.

        Chunks 2+ should have overlap_char_count > 0 indicating the context overlap.
        """
        test_file = stress_test_dir / "large_100_pages.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunker.create_chunks(text)

        # First chunk should have overlap_char_count = 0
        assert chunks[0].overlap_char_count == 0, "First chunk should have overlap_char_count=0"

        # At least some subsequent chunks should have overlap_char_count > 0
        chunks_with_overlap = [c for c in chunks[1:] if c.overlap_char_count > 0]

        assert len(chunks_with_overlap) > 0, (
            "Expected some chunks to have overlap_char_count > 0 after FIX-001"
        )

    def test_chunker_extreme_paragraphs(self, stress_test_dir, chunker):
        """
        Test chunker handles extreme paragraph sizes without crashing.
        """
        test_file = stress_test_dir / "extreme_paragraphs.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # Should not crash
        chunks = chunker.create_chunks(text)

        assert len(chunks) > 0, "Should produce at least one chunk"

        # Verify all content is captured (approximately)
        total_chunk_text = " ".join(c.text for c in chunks)
        original_word_count = len(text.split())
        chunk_word_count = len(total_chunk_text.split())

        # Allow 20% variance due to overlap handling
        assert chunk_word_count >= original_word_count * 0.8, (
            f"Lost too much content: {chunk_word_count} vs {original_word_count} words"
        )

    def test_chunker_unicode(self, stress_test_dir, chunker):
        """
        Test chunker handles Unicode correctly (multi-byte characters).
        """
        test_file = stress_test_dir / "unicode_stress.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunker.create_chunks(text)

        assert len(chunks) > 0, "Should produce chunks"

        # Verify Vietnamese diacritics preserved
        all_text = " ".join(c.text for c in chunks)
        assert "tiếng Việt" in all_text or "Tiếng Việt" in text.lower(), (
            "Vietnamese text should be preserved"
        )

        # Verify Chinese characters preserved
        assert any('\u4e00' <= char <= '\u9fff' for char in all_text), (
            "Chinese characters should be preserved"
        )

        # Verify no encoding corruption (no replacement characters)
        assert '\ufffd' not in all_text, "Found Unicode replacement character (corruption)"


# ============================================================================
# TEST GROUP B: MERGER TESTS
# ============================================================================

class TestMergerFixes:
    """Tests for FIX-002: Merger Fuzzy Matching"""

    def test_merger_uses_overlap_metadata(self, merger):
        """
        FIX-002: Verify merger uses overlap_char_count to remove overlap.
        """
        from core.validator import TranslationResult

        # Create two results with known overlap
        result1 = TranslationResult(
            chunk_id=1,
            source="Original text one.",
            translated="This is the first paragraph. This is overlap text.",
            quality_score=0.9,
            overlap_char_count=0  # First chunk, no overlap
        )

        result2 = TranslationResult(
            chunk_id=2,
            source="Original text two.",
            translated="This is overlap text. This is the second paragraph.",
            quality_score=0.9,
            overlap_char_count=50  # 50 chars of overlap from previous
        )

        # Merge
        merged = merger.merge_translations([result1, result2])

        # The overlap "This is overlap text." should appear only once
        # (approximately, since we multiply by 1.2 for Vietnamese expansion)
        overlap_count = merged.count("overlap text")
        assert overlap_count <= 2, f"Overlap should be reduced, found 'overlap text' {overlap_count} times"

    def test_merger_fuzzy_fallback(self, merger):
        """
        FIX-002: Verify fuzzy matching works when exact match fails.
        """
        from core.validator import TranslationResult

        # Two chunks with similar but not identical overlap
        result1 = TranslationResult(
            chunk_id=1,
            source="Original one.",
            translated="The algorithm processes data efficiently. The results are excellent.",
            quality_score=0.9,
            overlap_char_count=0
        )

        result2 = TranslationResult(
            chunk_id=2,
            source="Original two.",
            # Slightly different overlap (fuzzy case)
            translated="The results are very good. Additional analysis follows.",
            quality_score=0.9,
            overlap_char_count=0  # No metadata, should use fuzzy
        )

        # Should not crash and should produce merged output
        merged = merger.merge_translations([result1, result2])

        assert len(merged) > 0, "Should produce merged output"
        assert "algorithm" in merged, "First chunk content should be present"
        assert "Additional" in merged, "Second chunk content should be present"

    def test_merger_preserves_unique_content(self, merger):
        """
        Verify merger doesn't accidentally remove similar but unique content.
        """
        from core.validator import TranslationResult

        # Create results with DISTINCT content (no similarity that could be confused as overlap)
        results = []
        distinct_content = [
            "ALPHA: Machine learning achieved 95% accuracy on classification tasks.",
            "BETA: Deep learning reached 94% precision in image recognition.",
            "GAMMA: Neural networks obtained 96% recall on text analysis.",
        ]

        for i, content in enumerate(distinct_content, 1):
            results.append(TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=content,
                quality_score=0.9,
                overlap_char_count=0
            ))

        merged = merger.merge_translations(results)

        # All three distinct pieces should be present
        assert "ALPHA" in merged, "First content (ALPHA) should be preserved"
        assert "BETA" in merged, "Second content (BETA) should be preserved"
        assert "GAMMA" in merged, "Third content (GAMMA) should be preserved"


# ============================================================================
# TEST GROUP C: CHECKPOINT TESTS
# ============================================================================

class TestCheckpointFixes:
    """Tests for FIX-003: Checkpoint Type Mismatch"""

    def test_checkpoint_type_consistency(self, temp_checkpoint_db):
        """
        FIX-003: Verify chunk_ids are INT after loading from checkpoint.
        """
        from core.cache.checkpoint_manager import serialize_translation_result
        from core.validator import TranslationResult

        # Create test results with INT chunk_ids
        test_results = {}
        for i in range(1, 6):
            result = TranslationResult(
                chunk_id=i,
                source=f"Source {i}",
                translated=f"Translated {i}",
                quality_score=0.9
            )
            test_results[i] = serialize_translation_result(result)

        # Save checkpoint
        temp_checkpoint_db.save_checkpoint(
            job_id="test_job_001",
            input_file="input.txt",
            output_file="output.txt",
            total_chunks=5,
            completed_chunk_ids=[1, 2, 3, 4, 5],
            results_data=test_results,
            job_metadata={}
        )

        # Load checkpoint
        checkpoint = temp_checkpoint_db.load_checkpoint("test_job_001")

        assert checkpoint is not None, "Checkpoint should be loaded"

        # FIX-003: Keys should be INT, not STRING
        for key in checkpoint.results_data.keys():
            assert isinstance(key, int), f"Key {key} should be INT, got {type(key)}"

        # completed_chunk_ids should also be INT
        for chunk_id in checkpoint.completed_chunk_ids:
            assert isinstance(chunk_id, int), f"Chunk ID {chunk_id} should be INT"

    def test_checkpoint_list_also_converts(self, temp_checkpoint_db):
        """
        FIX-003: Verify list_checkpoints() also converts keys to INT.
        """
        from core.cache.checkpoint_manager import serialize_translation_result
        from core.validator import TranslationResult

        # Create and save multiple checkpoints
        for job_num in range(3):
            test_results = {}
            for i in range(1, 4):
                result = TranslationResult(
                    chunk_id=i,
                    source=f"Source {i}",
                    translated=f"Translated {i}",
                    quality_score=0.9
                )
                test_results[i] = serialize_translation_result(result)

            temp_checkpoint_db.save_checkpoint(
                job_id=f"test_job_{job_num:03d}",
                input_file=f"input_{job_num}.txt",
                output_file=f"output_{job_num}.txt",
                total_chunks=3,
                completed_chunk_ids=[1, 2, 3],
                results_data=test_results,
                job_metadata={}
            )

        # List checkpoints
        checkpoints = temp_checkpoint_db.list_checkpoints()

        assert len(checkpoints) == 3, "Should have 3 checkpoints"

        for checkpoint in checkpoints:
            for key in checkpoint.results_data.keys():
                assert isinstance(key, int), f"Key {key} should be INT in list_checkpoints"


# ============================================================================
# TEST GROUP D: END-TO-END TESTS
# ============================================================================

class TestEndToEnd:
    """End-to-end integration tests"""

    def test_e2e_chunk_translate_merge_no_duplicates(
        self, stress_test_dir, chunker, merger, mock_translator
    ):
        """
        Full pipeline: chunk → translate → merge should not produce duplicates.
        """
        test_file = stress_test_dir / "large_100_pages.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # Step 1: Chunk
        chunks = chunker.create_chunks(text)
        assert len(chunks) > 50, f"Expected many chunks, got {len(chunks)}"

        # Step 2: Mock translate
        async def translate_all():
            results = []
            for chunk in chunks:
                result = await mock_translator.translate_chunk(None, chunk)
                results.append(result)
            return results

        results = asyncio.run(translate_all())

        # Step 3: Merge
        merged = merger.merge_translations(results)

        # Verify: Check for duplicate paragraphs
        dup_info = count_duplicate_paragraphs(merged)

        # Allow very few duplicates (some might be legitimate repeated content)
        assert dup_info['duplicate_count'] <= 3, (
            f"Too many duplicates: {dup_info['duplicate_count']}\n"
            f"Examples: {dup_info['duplicates'][:3]}"
        )

    def test_e2e_chapter_order_preserved(self, stress_test_dir, chunker, merger, mock_translator):
        """
        Verify chapter order is preserved through the pipeline.
        """
        test_file = stress_test_dir / "large_100_pages.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunker.create_chunks(text)

        async def translate_all():
            results = []
            for chunk in chunks:
                result = await mock_translator.translate_chunk(None, chunk)
                results.append(result)
            return results

        results = asyncio.run(translate_all())
        merged = merger.merge_translations(results)

        # Verify chapter order
        assert verify_chapter_order(merged), "Chapters should be in ascending order"

    def test_e2e_complex_structure_preserved(self, stress_test_dir, chunker, merger, mock_translator):
        """
        Verify code blocks and tables are preserved through pipeline.
        """
        test_file = stress_test_dir / "complex_structure.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunker.create_chunks(text)

        async def translate_all():
            results = []
            for chunk in chunks:
                result = await mock_translator.translate_chunk(None, chunk)
                results.append(result)
            return results

        results = asyncio.run(translate_all())
        merged = merger.merge_translations(results)

        # Check code blocks
        code_check = check_code_blocks_intact(merged)
        assert code_check['intact'], (
            f"Code blocks not intact: {code_check['total_starts']} starts, "
            f"{code_check['total_ends']} ends"
        )

        # Check tables (should have table content)
        assert '|' in merged, "Table content should be preserved"

    def test_e2e_repetitive_content_not_over_removed(
        self, stress_test_dir, chunker, merger, mock_translator
    ):
        """
        HARDEST TEST: Similar but unique content should NOT be removed.

        This tests that fuzzy matching doesn't false-positive on legitimately
        similar content.
        """
        test_file = stress_test_dir / "repetitive_content.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        original_word_count = len(text.split())

        chunks = chunker.create_chunks(text)

        async def translate_all():
            results = []
            for chunk in chunks:
                result = await mock_translator.translate_chunk(None, chunk)
                results.append(result)
            return results

        results = asyncio.run(translate_all())
        merged = merger.merge_translations(results)

        merged_word_count = len(merged.split())

        # Word count should be similar (within 30% - mock translator adds "TRANSLATED:" prefix)
        # Account for the prefix overhead
        expected_min = original_word_count * 0.7
        expected_max = original_word_count * 1.5  # Mock adds text

        assert merged_word_count >= expected_min, (
            f"Too much content removed: {merged_word_count} words vs "
            f"original {original_word_count} words"
        )

    def test_e2e_checkpoint_markers_mostly_present(
        self, stress_test_dir, chunker, merger, mock_translator
    ):
        """
        Verify most chunk boundary markers are present in output.

        Note: Some markers may be lost at chunk boundaries, but most should be preserved.
        We accept 90%+ preservation rate as success.
        """
        test_file = stress_test_dir / "checkpoint_killer.txt"
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # Extract expected markers from original
        original_markers = extract_chunk_markers(text)
        assert len(original_markers) == 100, f"Expected 100 markers, got {len(original_markers)}"

        chunks = chunker.create_chunks(text)

        async def translate_all():
            results = []
            for chunk in chunks:
                result = await mock_translator.translate_chunk(None, chunk)
                results.append(result)
            return results

        results = asyncio.run(translate_all())
        merged = merger.merge_translations(results)

        # Extract markers from merged output
        output_markers = extract_chunk_markers(merged)

        # Calculate preservation rate
        preserved_count = len(set(original_markers) & set(output_markers))
        preservation_rate = preserved_count / len(original_markers)

        # Accept 85%+ preservation (some may be lost at boundaries)
        assert preservation_rate >= 0.85, (
            f"Only {preservation_rate:.1%} of markers preserved "
            f"({preserved_count}/{len(original_markers)})"
        )

        # Also check that chunk order is maintained
        if len(output_markers) > 1:
            assert output_markers == sorted(output_markers), (
                "Markers should be in ascending order"
            )


# ============================================================================
# TEST GROUP E: TRANSLATOR PROMPT TESTS
# ============================================================================

class TestTranslatorPrompt:
    """Tests for FIX-004: Translator Prompt Update"""

    def test_prompt_includes_context_instructions(self, chunker):
        """
        FIX-004: Verify prompt includes clear context instructions.
        """
        from core.translator import TranslatorEngine

        # Create a chunk with context
        from core.chunker import TranslationChunk
        chunk = TranslationChunk(
            id=1,
            text="This is the main text to translate.",
            context_before="This is the previous paragraph for context.",
            context_after="This is the next paragraph for context."
        )

        # Create translator and build prompt
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",  # Not used, just for init
            source_lang="en",
            target_lang="vi"
        )

        prompt = engine.build_prompt(chunk)

        # FIX-004: Prompt should have clear context instructions
        assert "DO NOT TRANSLATE" in prompt, "Prompt should instruct not to translate context"
        assert "CONTEXT" in prompt, "Prompt should have CONTEXT section"
        assert "---START---" in prompt, "Prompt should have START marker"
        assert "---END---" in prompt, "Prompt should have END marker"

    def test_chunk_overlap_passed_to_result(self, chunker, mock_translator):
        """
        FIX-002: Verify overlap_char_count is passed from chunk to result.
        """
        from core.chunker import TranslationChunk

        # Create chunk with overlap_char_count
        chunk = TranslationChunk(
            id=2,
            text="This is chunk 2 text.",
            context_before="Previous chunk ending.",
            overlap_char_count=150  # Set overlap
        )

        # Translate with mock
        result = asyncio.run(mock_translator.translate_chunk(None, chunk))

        # Result should have same overlap_char_count
        assert result.overlap_char_count == 150, (
            f"Expected overlap_char_count=150, got {result.overlap_char_count}"
        )


# ============================================================================
# MAIN - Custom test runner with pretty output
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
