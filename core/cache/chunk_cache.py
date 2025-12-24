#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chunk Cache - Phase 5.1

Provides persistent caching for translation chunks using SQLite backend.

Key Features:
- Stable hash-based key generation
- Persistent storage across restarts
- Hit/miss statistics tracking
- Thread-safe operations
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import threading


def compute_chunk_key(
    source_text: str,
    source_lang: str,
    target_lang: str,
    mode: str = "simple",
    **kwargs
) -> str:
    """
    Generate stable cache key for a translation chunk.

    Args:
        source_text: The text to translate
        source_lang: Source language code (e.g., 'en')
        target_lang: Target language code (e.g., 'vi')
        mode: Pipeline mode (simple/academic/book/stem)
        **kwargs: Additional flags that affect translation
                 (e.g., quality_mode, enable_chemical_formulas)

    Returns:
        Hex string (SHA256 hash) representing the unique cache key

    Examples:
        >>> key1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        >>> key2 = compute_chunk_key("Hello world", "en", "vi", "simple")
        >>> key1 == key2
        True
        >>> key3 = compute_chunk_key("Hello world", "en", "vi", "academic")
        >>> key1 != key3
        True
    """
    # Normalize text (strip leading/trailing whitespace, but preserve internal structure)
    normalized_text = source_text.strip()

    # Build deterministic key components
    key_components = {
        'text': normalized_text,
        'source_lang': source_lang.lower(),
        'target_lang': target_lang.lower(),
        'mode': mode.lower(),
    }

    # Add relevant kwargs that affect translation output
    # Filter out None values and sort for determinism
    relevant_flags = {
        k: v for k, v in sorted(kwargs.items())
        if v is not None and k in [
            'quality_mode',
            'enable_chemical_formulas',
            'glossary_name',
            'domain',
        ]
    }

    if relevant_flags:
        key_components['flags'] = relevant_flags

    # Convert to stable JSON string (sorted keys)
    key_string = json.dumps(key_components, sort_keys=True, ensure_ascii=False)

    # Generate SHA256 hash
    hash_obj = hashlib.sha256(key_string.encode('utf-8'))
    return hash_obj.hexdigest()


class ChunkCache:
    """
    SQLite-backed cache for translation chunks.

    Thread-safe implementation with automatic schema creation.

    Database Schema:
        - key: TEXT PRIMARY KEY (SHA256 hash)
        - value: TEXT (translated text)
        - source_lang: TEXT
        - target_lang: TEXT
        - mode: TEXT
        - created_at: TEXT (ISO timestamp)
        - last_accessed: TEXT (ISO timestamp)
        - access_count: INTEGER

    Usage:
        >>> cache = ChunkCache('./data/cache/chunks.db')
        >>> cache.set('abc123', 'Hello world')
        >>> cache.get('abc123')
        'Hello world'
        >>> cache.stats()
        {'total_entries': 1, 'hits': 1, 'misses': 0, 'hit_rate': 1.0}
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize cache with SQLite database.

        Args:
            db_path: Path to SQLite database file (will be created if doesn't exist)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()

        # Stats tracking (in-memory, reset on restart)
        self._stats_lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        # Initialize database schema
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunk_cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                source_lang TEXT,
                target_lang TEXT,
                mode TEXT,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 1
            )
        ''')

        # Create indexes for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON chunk_cache(created_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_accessed ON chunk_cache(last_accessed)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lang_pair ON chunk_cache(source_lang, target_lang)
        ''')

        conn.commit()

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve cached value by key.

        Updates last_accessed timestamp and access_count on hit.

        Args:
            key: Cache key (SHA256 hash from compute_chunk_key)

        Returns:
            Cached translated text if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT value FROM chunk_cache WHERE key = ?', (key,))
        row = cursor.fetchone()

        if row:
            # Update access stats
            now = datetime.utcnow().isoformat()
            cursor.execute('''
                UPDATE chunk_cache
                SET last_accessed = ?, access_count = access_count + 1
                WHERE key = ?
            ''', (now, key))
            conn.commit()

            # Track hit
            with self._stats_lock:
                self._hits += 1

            return row['value']
        else:
            # Track miss
            with self._stats_lock:
                self._misses += 1

            return None

    def set(
        self,
        key: str,
        value: str,
        source_lang: str = '',
        target_lang: str = '',
        mode: str = ''
    ) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key (SHA256 hash from compute_chunk_key)
            value: Translated text to cache
            source_lang: Optional source language (for metadata)
            target_lang: Optional target language (for metadata)
            mode: Optional pipeline mode (for metadata)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute('''
            INSERT OR REPLACE INTO chunk_cache
            (key, value, source_lang, target_lang, mode, created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (key, value, source_lang, target_lang, mode, now, now))

        conn.commit()

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with:
            - total_entries: Number of cached chunks
            - hits: Number of cache hits (since init)
            - misses: Number of cache misses (since init)
            - hit_rate: Cache hit rate (0.0 - 1.0)
            - db_size_mb: Database file size in MB
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get total entries
        cursor.execute('SELECT COUNT(*) as count FROM chunk_cache')
        total_entries = cursor.fetchone()['count']

        # Get DB file size
        db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        db_size_mb = db_size_bytes / (1024 * 1024)

        # Calculate hit rate
        with self._stats_lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                'total_entries': total_entries,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'db_size_mb': round(db_size_mb, 2)
            }

    def clear(self) -> None:
        """Clear all cache entries (for testing/maintenance)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chunk_cache')
        conn.commit()

        # Reset stats
        with self._stats_lock:
            self._hits = 0
            self._misses = 0

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
