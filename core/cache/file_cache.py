"""
File Cache

Persistent file-based cache for larger data (ADN, outputs).
"""

import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass
import logging
import pickle

from .base import CacheInterface, CacheStats

logger = logging.getLogger(__name__)


@dataclass
class FileCacheEntry:
    """Metadata for cached file"""
    key: str
    filename: str
    created_at: float
    expires_at: Optional[float]
    size_bytes: int
    content_type: str  # "json", "pickle", "binary"


class FileCache(CacheInterface):
    """
    File-based persistent cache.

    Features:
    - Persistent across restarts
    - Large data support
    - Automatic cleanup of expired entries
    - Multiple content types (JSON, pickle, binary)
    """

    def __init__(
        self,
        cache_dir: str = "data/cache/files",
        max_size_mb: int = 500,
        default_ttl: Optional[int] = 86400,  # 24 hours
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl

        self._index_file = self.cache_dir / "_index.json"
        self._index: Dict[str, FileCacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size_mb)

        # Load existing index
        self._load_index()

    def _load_index(self):
        """Load index from disk"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    data = json.load(f)

                for key, entry_dict in data.items():
                    self._index[key] = FileCacheEntry(**entry_dict)

                logger.debug(f"Loaded {len(self._index)} cache entries")
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self._index = {}

    def _save_index(self):
        """Save index to disk"""
        try:
            data = {
                k: {
                    "key": v.key,
                    "filename": v.filename,
                    "created_at": v.created_at,
                    "expires_at": v.expires_at,
                    "size_bytes": v.size_bytes,
                    "content_type": v.content_type,
                }
                for k, v in self._index.items()
            }

            with open(self._index_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _key_to_filename(self, key: str) -> str:
        """Convert key to safe filename"""
        hash_val = hashlib.md5(key.encode()).hexdigest()[:16]
        safe_key = "".join(c if c.isalnum() else "_" for c in key[:32])
        return f"{safe_key}_{hash_val}"

    def _get_file_path(self, filename: str) -> Path:
        """Get full path for cache file"""
        return self.cache_dir / filename

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._index:
                self._stats.misses += 1
                return None

            entry = self._index[key]

            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                self.delete(key)
                self._stats.misses += 1
                return None

            # Read file
            file_path = self._get_file_path(entry.filename)
            if not file_path.exists():
                del self._index[key]
                self._save_index()
                self._stats.misses += 1
                return None

            try:
                if entry.content_type == "json":
                    with open(file_path, 'r', encoding='utf-8') as f:
                        value = json.load(f)
                elif entry.content_type == "pickle":
                    with open(file_path, 'rb') as f:
                        value = pickle.load(f)
                else:  # binary
                    with open(file_path, 'rb') as f:
                        value = f.read()

                self._stats.hits += 1
                return value

            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
                self._stats.misses += 1
                return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        content_type: str = "auto",
    ) -> bool:
        with self._lock:
            # Determine content type
            if content_type == "auto":
                if isinstance(value, (dict, list, str)):
                    content_type = "json"
                elif isinstance(value, bytes):
                    content_type = "binary"
                else:
                    content_type = "pickle"

            # Generate filename
            filename = self._key_to_filename(key)
            if content_type == "json":
                filename += ".json"
            elif content_type == "pickle":
                filename += ".pkl"
            else:
                filename += ".bin"

            file_path = self._get_file_path(filename)

            # Write file
            try:
                if content_type == "json":
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(value, f, ensure_ascii=False)
                elif content_type == "pickle":
                    with open(file_path, 'wb') as f:
                        pickle.dump(value, f)
                else:  # binary
                    with open(file_path, 'wb') as f:
                        f.write(value)

                # Calculate TTL
                ttl = ttl or self.default_ttl
                expires_at = time.time() + ttl if ttl else None

                # Create entry
                entry = FileCacheEntry(
                    key=key,
                    filename=filename,
                    created_at=time.time(),
                    expires_at=expires_at,
                    size_bytes=file_path.stat().st_size,
                    content_type=content_type,
                )

                # Delete old entry if exists
                if key in self._index:
                    old_file = self._get_file_path(self._index[key].filename)
                    if old_file.exists() and old_file != file_path:
                        old_file.unlink()

                self._index[key] = entry
                self._save_index()

                # Update stats
                self._stats.size = len(self._index)

                # Check size limit
                self._enforce_size_limit()

                return True

            except Exception as e:
                logger.error(f"Failed to write cache file: {e}")
                return False

    def delete(self, key: str) -> bool:
        with self._lock:
            if key not in self._index:
                return False

            entry = self._index[key]
            file_path = self._get_file_path(entry.filename)

            # Delete file
            if file_path.exists():
                file_path.unlink()

            # Remove from index
            del self._index[key]
            self._save_index()

            self._stats.size = len(self._index)
            return True

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._index:
                return False

            entry = self._index[key]

            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                self.delete(key)
                return False

            # Check file exists
            file_path = self._get_file_path(entry.filename)
            return file_path.exists()

    def clear(self) -> int:
        with self._lock:
            count = len(self._index)

            # Delete all cache files
            for entry in self._index.values():
                file_path = self._get_file_path(entry.filename)
                if file_path.exists():
                    file_path.unlink()

            # Clear index
            self._index.clear()
            self._save_index()

            self._stats.size = 0
            return count

    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.size = len(self._index)
            return self._stats

    def _enforce_size_limit(self):
        """Remove oldest entries if over size limit"""
        total_size = sum(e.size_bytes for e in self._index.values())

        if total_size <= self.max_size_bytes:
            return

        # Sort by creation time (oldest first)
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1].created_at
        )

        # Remove oldest until under limit
        while total_size > self.max_size_bytes and sorted_entries:
            key, entry = sorted_entries.pop(0)
            total_size -= entry.size_bytes
            self.delete(key)
            logger.debug(f"Evicted cache entry: {key}")

    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._index.items()
                if v.expires_at and now > v.expires_at
            ]

            for key in expired_keys:
                self.delete(key)

            return len(expired_keys)

    def get_total_size_mb(self) -> float:
        """Get total cache size in MB"""
        with self._lock:
            total_bytes = sum(e.size_bytes for e in self._index.values())
            return total_bytes / (1024 * 1024)
