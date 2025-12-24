"""
APS Cache Manager

High-level cache manager for APS pipeline with specialized methods.
"""

import hashlib
import logging
from typing import Any, Optional, Dict
from pathlib import Path

from .memory_cache import MemoryCache
from .file_cache import FileCache
from .base import CacheStats

logger = logging.getLogger(__name__)


class APSCacheManager:
    """
    Unified cache manager for APS pipeline.

    Cache hierarchy:
    - L1: Memory cache (translation chunks, hot ADN)
    - L2: File cache (ADN, output files)

    Usage:
        cache = APSCacheManager()

        # Translation caching
        cache.get_translation(source_text, source_lang, target_lang)
        cache.set_translation(source_text, translated, source_lang, target_lang)

        # ADN caching
        cache.get_adn(document_hash)
        cache.set_adn(document_hash, adn_data)

        # Output caching
        cache.get_output(job_id, format)
        cache.set_output(job_id, format, file_path)
    """

    def __init__(
        self,
        cache_dir: str = "data/cache/aps",
        memory_max_size: int = 1000,
        file_max_size_mb: int = 500,
        translation_ttl: int = 86400 * 7,  # 7 days
        adn_ttl: int = 86400 * 30,  # 30 days
        output_ttl: int = 86400,  # 1 day
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # L1: Memory caches
        self._translation_cache = MemoryCache(
            max_size=memory_max_size,
            default_ttl=3600,  # 1 hour in memory
        )

        self._adn_memory_cache = MemoryCache(
            max_size=100,
            default_ttl=1800,  # 30 min in memory
        )

        # L2: File caches
        self._translation_file_cache = FileCache(
            cache_dir=str(self.cache_dir / "translations"),
            max_size_mb=file_max_size_mb // 2,
            default_ttl=translation_ttl,
        )

        self._adn_file_cache = FileCache(
            cache_dir=str(self.cache_dir / "adn"),
            max_size_mb=file_max_size_mb // 4,
            default_ttl=adn_ttl,
        )

        self._output_file_cache = FileCache(
            cache_dir=str(self.cache_dir / "outputs"),
            max_size_mb=file_max_size_mb // 4,
            default_ttl=output_ttl,
        )

        logger.info(f"APSCacheManager initialized: {self.cache_dir}")

    # ==================== Translation Cache ====================

    def _translation_key(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Generate cache key for translation"""
        content = f"{source_lang}:{target_lang}:{source_text}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:32]
        return f"trans:{hash_val}"

    def get_translation(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[str]:
        """
        Get cached translation.

        Checks L1 (memory) first, then L2 (file).
        """
        key = self._translation_key(source_text, source_lang, target_lang)

        # L1: Memory
        result = self._translation_cache.get(key)
        if result is not None:
            return result

        # L2: File
        result = self._translation_file_cache.get(key)
        if result is not None:
            # Promote to L1
            self._translation_cache.set(key, result)
            return result

        return None

    def set_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
    ) -> bool:
        """
        Cache translation result.

        Stores in both L1 (memory) and L2 (file).
        """
        key = self._translation_key(source_text, source_lang, target_lang)

        # L1: Memory
        self._translation_cache.set(key, translated_text)

        # L2: File (for persistence)
        self._translation_file_cache.set(key, translated_text, content_type="json")

        return True

    # ==================== ADN Cache ====================

    def _adn_key(self, document_hash: str) -> str:
        """Generate cache key for ADN"""
        return f"adn:{document_hash}"

    def get_adn(self, document_hash: str) -> Optional[Dict]:
        """
        Get cached ADN data.
        """
        key = self._adn_key(document_hash)

        # L1: Memory
        result = self._adn_memory_cache.get(key)
        if result is not None:
            return result

        # L2: File
        result = self._adn_file_cache.get(key)
        if result is not None:
            # Promote to L1
            self._adn_memory_cache.set(key, result)
            return result

        return None

    def set_adn(self, document_hash: str, adn_data: Dict) -> bool:
        """
        Cache ADN data.
        """
        key = self._adn_key(document_hash)

        # L1: Memory
        self._adn_memory_cache.set(key, adn_data)

        # L2: File
        self._adn_file_cache.set(key, adn_data, content_type="json")

        return True

    # ==================== Output Cache ====================

    def _output_key(self, job_id: str, format_type: str) -> str:
        """Generate cache key for output"""
        return f"output:{job_id}:{format_type}"

    def get_output_path(self, job_id: str, format_type: str) -> Optional[Path]:
        """
        Get cached output file path.

        Returns None if not cached or expired.
        """
        key = self._output_key(job_id, format_type)

        if not self._output_file_cache.exists(key):
            return None

        # Get the stored path
        stored_path = self._output_file_cache.get(key)
        if stored_path and Path(stored_path).exists():
            return Path(stored_path)

        return None

    def set_output_path(
        self,
        job_id: str,
        format_type: str,
        file_path: Path,
    ) -> bool:
        """
        Cache output file path.
        """
        key = self._output_key(job_id, format_type)
        return self._output_file_cache.set(
            key,
            str(file_path),
            content_type="json",
        )

    # ==================== Document Hash ====================

    @staticmethod
    def hash_document(content: str) -> str:
        """
        Generate hash for document content.

        Used as cache key for ADN.
        """
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    @staticmethod
    def hash_file(file_path: Path) -> str:
        """
        Generate hash for file.
        """
        hasher = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)

        return hasher.hexdigest()[:32]

    # ==================== Statistics ====================

    def stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "translation_memory": self._translation_cache.stats().to_dict(),
            "translation_file": self._translation_file_cache.stats().to_dict(),
            "adn_memory": self._adn_memory_cache.stats().to_dict(),
            "adn_file": self._adn_file_cache.stats().to_dict(),
            "output_file": self._output_file_cache.stats().to_dict(),
        }

    def clear_all(self) -> Dict:
        """Clear all caches"""
        return {
            "translation_memory": self._translation_cache.clear(),
            "translation_file": self._translation_file_cache.clear(),
            "adn_memory": self._adn_memory_cache.clear(),
            "adn_file": self._adn_file_cache.clear(),
            "output_file": self._output_file_cache.clear(),
        }

    def cleanup_expired(self) -> Dict:
        """Cleanup expired entries from all caches"""
        return {
            "translation_memory": self._translation_cache.cleanup_expired(),
            "translation_file": self._translation_file_cache.cleanup_expired(),
            "adn_memory": self._adn_memory_cache.cleanup_expired(),
            "adn_file": self._adn_file_cache.cleanup_expired(),
            "output_file": self._output_file_cache.cleanup_expired(),
        }


# Global instance
_cache_manager: Optional[APSCacheManager] = None


def get_cache_manager(**kwargs) -> APSCacheManager:
    """Get or create global cache manager"""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = APSCacheManager(**kwargs)

    return _cache_manager
