#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TranslationCache - Cache để tránh dịch lại content giống nhau
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from config.logging_config import get_logger
logger = get_logger(__name__)



class TranslationCache:
    """Cache để tránh dịch lại content giống nhau"""

    def __init__(self, cache_dir: Path, enabled: bool = True):
        self.enabled = enabled
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.cache_file = self.cache_dir / "translation_cache.json"
        self.cache = self._load_cache()
        self.hits = 0
        self.misses = 0

    def _load_cache(self) -> Dict:
        """Load cache từ disk"""
        if not self.enabled:
            return {}

        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                logger.info(f" Loaded {len(data)} cached translations")
                return data
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk"""
        if not self.enabled:
            return

        try:
            self.cache_file.write_text(
                json.dumps(self.cache, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f" Cannot save cache: {e}")

    def get_hash(self, text: str, model: str) -> str:
        """Generate unique hash cho text + model"""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str) -> Optional[str]:
        """Get cached translation"""
        if not self.enabled:
            return None

        hash_key = self.get_hash(text, model)
        if hash_key in self.cache:
            self.hits += 1
            return self.cache[hash_key]["translation"]

        self.misses += 1
        return None

    def set(self, text: str, translation: str, model: str, quality_score: float = 0.0):
        """Cache translation"""
        if not self.enabled:
            return

        hash_key = self.get_hash(text, model)
        self.cache[hash_key] = {
            "translation": translation,
            "model": model,
            "quality_score": quality_score,
            "timestamp": datetime.now().isoformat()
        }

        # Periodic save
        if len(self.cache) % 10 == 0:
            self._save_cache()

    def get_stats(self) -> str:
        """Get cache statistics"""
        total = self.hits + self.misses
        if total == 0:
            return "Cache: No requests yet"

        hit_rate = (self.hits / total) * 100
        return f"Cache: {self.hits} hits, {self.misses} misses ({hit_rate:.1f}% hit rate)"

    def save(self):
        """Force save cache to disk"""
        self._save_cache()
