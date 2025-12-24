"""
Base Cache Interface

Abstract interface for all cache implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.1%}",
            "size": self.size,
            "max_size": self.max_size,
        }


class CacheInterface(ABC):
    """Abstract cache interface"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    def clear(self) -> int:
        """Clear all entries, return count cleared"""
        pass

    @abstractmethod
    def stats(self) -> CacheStats:
        """Get cache statistics"""
        pass
