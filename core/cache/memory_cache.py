"""
Memory Cache

Fast in-memory LRU cache for frequently accessed data.
"""

import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict
from dataclasses import dataclass
import logging

from .base import CacheInterface, CacheStats

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class LRUCache(CacheInterface):
    """
    Thread-safe LRU (Least Recently Used) cache.

    Features:
    - O(1) get/set operations
    - Automatic eviction of least recently used items
    - Optional TTL per entry
    - Thread-safe
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.size = len(self._cache)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1

            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            # Calculate expiration
            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl if ttl else None

            # Create entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
            )

            # Update or insert
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = entry

            # Evict if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

            self._stats.size = len(self._cache)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return False

            return True

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.size = 0
            return count

    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.size = len(self._cache)
            return self._stats

    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]

            self._stats.size = len(self._cache)
            return len(expired_keys)


class MemoryCache(LRUCache):
    """
    Alias for LRUCache with sensible defaults for APS.
    """

    def __init__(
        self,
        max_size: int = 500,
        default_ttl: int = 3600,  # 1 hour
    ):
        super().__init__(max_size=max_size, default_ttl=default_ttl)
