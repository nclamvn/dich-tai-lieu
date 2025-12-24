#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit Tests for Phase 5.1 Chunk Cache

Tests cover:
- Hash key generation (stability, uniqueness)
- Cache operations (set, get, clear)
- Statistics tracking
- Database persistence
- Thread safety
"""

import pytest
import os
import tempfile
from pathlib import Path

from core.cache.chunk_cache import ChunkCache, compute_chunk_key


class TestComputeChunkKey:
    """Test hash key generation function"""

    def test_same_input_same_key(self):
        """Same inputs should generate identical keys"""
        key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        key2 = compute_chunk_key("Hello world", "en", "vi", "simple")
        assert key1 == key2, "Same inputs must produce same key"

    def test_different_text_different_key(self):
        """Different text should generate different keys"""
        key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        key2 = compute_chunk_key("Goodbye world", "en", "vi", "simple")
        assert key1 != key2, "Different text must produce different keys"

    def test_different_mode_different_key(self):
        """Different pipeline modes should generate different keys"""
        key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        key2 = compute_chunk_key("Hello world", "en", "vi", "academic")
        assert key1 != key2, "Different modes must produce different keys"

    def test_different_lang_pair_different_key(self):
        """Different language pairs should generate different keys"""
        key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        key2 = compute_chunk_key("Hello world", "en", "zh", "simple")
        key3 = compute_chunk_key("Hello world", "vi", "en", "simple")
        assert key1 != key2, "Different target language must produce different key"
        assert key1 != key3, "Different source language must produce different key"

    def test_whitespace_normalization(self):
        """Leading/trailing whitespace should not affect key"""
        key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        key2 = compute_chunk_key("  Hello world  ", "en", "vi", "simple")
        key3 = compute_chunk_key("\nHello world\n", "en", "vi", "simple")
        assert key1 == key2 == key3, "Whitespace normalization should work"

    def test_with_domain_parameter(self):
        """Domain parameter should affect cache key"""
        key1 = compute_chunk_key("E = mc²", "en", "vi", "simple", domain="stem")
        key2 = compute_chunk_key("E = mc²", "en", "vi", "simple", domain="general")
        key3 = compute_chunk_key("E = mc²", "en", "vi", "simple")  # No domain
        assert key1 != key2, "Different domains must produce different keys"
        assert key1 != key3, "Domain vs no-domain must produce different keys"

    def test_key_format(self):
        """Generated key should be valid SHA256 hex string"""
        key = compute_chunk_key("Test text", "en", "vi", "simple")
        assert isinstance(key, str), "Key must be string"
        assert len(key) == 64, "SHA256 hex digest should be 64 characters"
        assert all(c in '0123456789abcdef' for c in key), "Key must be hex string"


class TestChunkCache:
    """Test ChunkCache class operations"""

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        cache = ChunkCache(temp_file.name)
        yield cache
        cache.close()
        os.unlink(temp_file.name)

    def test_cache_set_get_roundtrip(self, temp_cache):
        """Test basic set and get operations"""
        key = "test_key_123"
        value = "Xin chào thế giới"

        temp_cache.set(key, value, "en", "vi", "simple")
        result = temp_cache.get(key)

        assert result == value, "Retrieved value must match stored value"

    def test_cache_miss_returns_none(self, temp_cache):
        """Test that missing keys return None"""
        result = temp_cache.get("nonexistent_key")
        assert result is None, "Missing key must return None"

    def test_cache_overwrite(self, temp_cache):
        """Test that setting same key overwrites previous value"""
        key = "overwrite_test"

        temp_cache.set(key, "First value", "en", "vi", "simple")
        temp_cache.set(key, "Second value", "en", "vi", "simple")

        result = temp_cache.get(key)
        assert result == "Second value", "New value must overwrite old value"

    def test_cache_multiple_entries(self, temp_cache):
        """Test storing and retrieving multiple entries"""
        entries = {
            "key1": "Value 1",
            "key2": "Value 2",
            "key3": "Value 3"
        }

        for key, value in entries.items():
            temp_cache.set(key, value)

        for key, expected_value in entries.items():
            result = temp_cache.get(key)
            assert result == expected_value, f"Key {key} must return correct value"

    def test_cache_unicode_support(self, temp_cache):
        """Test that cache handles Unicode text correctly"""
        key = "unicode_test"
        value = "Tiếng Việt có dấu: àáảãạ, 中文字符, 日本語, العربية"

        temp_cache.set(key, value, "en", "vi", "simple")
        result = temp_cache.get(key)

        assert result == value, "Unicode text must be preserved"

    def test_cache_long_text(self, temp_cache):
        """Test that cache handles long text correctly"""
        key = "long_text_test"
        value = "Lorem ipsum " * 1000  # Long text

        temp_cache.set(key, value)
        result = temp_cache.get(key)

        assert result == value, "Long text must be preserved"

    def test_cache_clear(self, temp_cache):
        """Test clearing all cache entries"""
        temp_cache.set("key1", "value1")
        temp_cache.set("key2", "value2")

        temp_cache.clear()

        assert temp_cache.get("key1") is None, "Cache must be empty after clear"
        assert temp_cache.get("key2") is None, "Cache must be empty after clear"

        stats = temp_cache.stats()
        assert stats['total_entries'] == 0, "Entry count must be 0 after clear"

    def test_cache_persistence(self):
        """Test that cache survives restart"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_path = temp_file.name
        temp_file.close()

        try:
            # First session: write data
            cache1 = ChunkCache(temp_path)
            cache1.set("persistent_key", "persistent_value")
            cache1.close()

            # Second session: read data
            cache2 = ChunkCache(temp_path)
            result = cache2.get("persistent_key")
            cache2.close()

            assert result == "persistent_value", "Data must persist across restarts"
        finally:
            os.unlink(temp_path)


class TestCacheStatistics:
    """Test cache statistics tracking"""

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        cache = ChunkCache(temp_file.name)
        yield cache
        cache.close()
        os.unlink(temp_file.name)

    def test_stats_initial_state(self, temp_cache):
        """Test initial statistics"""
        stats = temp_cache.stats()

        assert stats['total_entries'] == 0, "Initial entry count must be 0"
        assert stats['hits'] == 0, "Initial hits must be 0"
        assert stats['misses'] == 0, "Initial misses must be 0"
        assert stats['hit_rate'] == 0.0, "Initial hit rate must be 0"

    def test_stats_hit_tracking(self, temp_cache):
        """Test that cache hits are tracked correctly"""
        temp_cache.set("key1", "value1")

        # First get - should be a hit
        temp_cache.get("key1")

        stats = temp_cache.stats()
        assert stats['hits'] == 1, "Hit count must be 1"
        assert stats['misses'] == 0, "Miss count must be 0"
        assert stats['hit_rate'] == 1.0, "Hit rate must be 100%"

    def test_stats_miss_tracking(self, temp_cache):
        """Test that cache misses are tracked correctly"""
        # Get nonexistent key - should be a miss
        temp_cache.get("nonexistent")

        stats = temp_cache.stats()
        assert stats['hits'] == 0, "Hit count must be 0"
        assert stats['misses'] == 1, "Miss count must be 1"
        assert stats['hit_rate'] == 0.0, "Hit rate must be 0%"

    def test_stats_hit_rate_calculation(self, temp_cache):
        """Test hit rate calculation with mixed hits and misses"""
        temp_cache.set("key1", "value1")
        temp_cache.set("key2", "value2")

        # 2 hits
        temp_cache.get("key1")
        temp_cache.get("key2")

        # 2 misses
        temp_cache.get("nonexistent1")
        temp_cache.get("nonexistent2")

        stats = temp_cache.stats()
        assert stats['hits'] == 2, "Hit count must be 2"
        assert stats['misses'] == 2, "Miss count must be 2"
        assert stats['hit_rate'] == 0.5, "Hit rate must be 50%"

    def test_stats_entry_count(self, temp_cache):
        """Test that entry count is tracked correctly"""
        temp_cache.set("key1", "value1")
        temp_cache.set("key2", "value2")
        temp_cache.set("key3", "value3")

        stats = temp_cache.stats()
        assert stats['total_entries'] == 3, "Entry count must be 3"

    def test_stats_after_clear(self, temp_cache):
        """Test that stats are reset after clear"""
        temp_cache.set("key1", "value1")
        temp_cache.get("key1")
        temp_cache.get("nonexistent")

        temp_cache.clear()

        stats = temp_cache.stats()
        assert stats['total_entries'] == 0, "Entry count must be 0 after clear"
        assert stats['hits'] == 0, "Hits must be reset after clear"
        assert stats['misses'] == 0, "Misses must be reset after clear"


class TestCacheEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_text(self):
        """Test handling of empty text"""
        key1 = compute_chunk_key("", "en", "vi", "simple")
        key2 = compute_chunk_key("", "en", "vi", "simple")
        assert key1 == key2, "Empty text should produce stable key"

    def test_very_long_key(self):
        """Test that very long text doesn't break key generation"""
        long_text = "A" * 100000  # 100K characters
        key = compute_chunk_key(long_text, "en", "vi", "simple")
        assert len(key) == 64, "Key length must still be 64 regardless of text length"

    def test_special_characters_in_text(self):
        """Test handling of special characters"""
        special_text = "Test with\n\r\t special chars: @#$%^&*()[]{}|\\/<>?"
        key = compute_chunk_key(special_text, "en", "vi", "simple")
        assert isinstance(key, str) and len(key) == 64, "Special chars should be handled"

    def test_case_sensitivity(self):
        """Test that text is case-sensitive"""
        key1 = compute_chunk_key("Hello World", "en", "vi", "simple")
        key2 = compute_chunk_key("hello world", "en", "vi", "simple")
        assert key1 != key2, "Text should be case-sensitive"

    def test_language_code_case_insensitive(self):
        """Test that language codes are case-insensitive"""
        key1 = compute_chunk_key("Hello", "en", "vi", "simple")
        key2 = compute_chunk_key("Hello", "EN", "VI", "simple")
        assert key1 == key2, "Language codes should be case-insensitive"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
