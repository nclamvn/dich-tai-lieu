"""
Cache Module - Combined Legacy, Phase 5.1 Chunk Cache, Phase 5.2 Checkpoints, and APS Cache

Exports:
- TranslationCache (legacy cache from core/cache/legacy_cache.py)
- ChunkCache (Phase 5.1, new hash-based SQLite cache)
- compute_chunk_key (Phase 5.1, hash key generator)
- CheckpointManager (Phase 5.2, fault-tolerant job state persistence)
- CheckpointState (Phase 5.2, checkpoint data structure)
- serialize_translation_result, deserialize_translation_result (Phase 5.2, serialization helpers)
- CacheInterface, CacheStats (base cache interface)
- MemoryCache, LRUCache (in-memory LRU cache)
- FileCache (file-based persistent cache)
- APSCacheManager, get_cache_manager (APS-specific cache manager)
"""

# Import legacy cache (backward compatibility)
from .legacy_cache import TranslationCache

# Import Phase 5.1 chunk cache
from .chunk_cache import ChunkCache, compute_chunk_key

# Import Phase 5.2 checkpoint manager
from .checkpoint_manager import (
    CheckpointManager,
    CheckpointState,
    serialize_translation_result,
    deserialize_translation_result
)

# Import PERF-004 APS cache
from .base import CacheInterface, CacheStats
from .memory_cache import MemoryCache, LRUCache
from .file_cache import FileCache
from .aps_cache import APSCacheManager, get_cache_manager

__all__ = [
    # Legacy
    'TranslationCache',
    # Phase 5.1
    'ChunkCache',
    'compute_chunk_key',
    # Phase 5.2
    'CheckpointManager',
    'CheckpointState',
    'serialize_translation_result',
    'deserialize_translation_result',
    # PERF-004 APS Cache
    'CacheInterface',
    'CacheStats',
    'MemoryCache',
    'LRUCache',
    'FileCache',
    'APSCacheManager',
    'get_cache_manager',
]
