"""
User Glossary Manager — Standalone term glossary with JSON persistence.

CRUD operations for user-defined glossaries:
- Create/list/get/delete glossaries
- Add/remove/update terms within a glossary
- Export glossary as Dict[str, str] for ConsistencyChecker integration
- JSON file persistence in data/glossaries/

Standalone module — no core/ imports.

Usage::

    manager = GlossaryManager(storage_dir="data/glossaries")

    # Create glossary
    gid = manager.create_glossary("Medical Terms", source_lang="en", target_lang="vi")

    # Add terms
    manager.add_term(gid, "heart", "tim")
    manager.add_term(gid, "lung", "phổi")

    # Get as dict for ConsistencyChecker
    terms = manager.get_term_dict(gid)
    # → {"heart": "tim", "lung": "phổi"}
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GlossaryTerm:
    """A single source → target term mapping."""

    source: str
    target: str
    notes: str = ""
    domain: str = "general"
    added_at: float = 0.0

    def __post_init__(self):
        if self.added_at == 0.0:
            self.added_at = time.time()


@dataclass
class Glossary:
    """A named collection of terms."""

    id: str
    name: str
    source_language: str = "en"
    target_language: str = "vi"
    description: str = ""
    terms: List[GlossaryTerm] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.updated_at == 0.0:
            self.updated_at = now

    @property
    def term_count(self) -> int:
        return len(self.terms)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "description": self.description,
            "terms": [asdict(t) for t in self.terms],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Glossary:
        terms = [
            GlossaryTerm(**t) for t in data.get("terms", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            source_language=data.get("source_language", "en"),
            target_language=data.get("target_language", "vi"),
            description=data.get("description", ""),
            terms=terms,
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )

    def get_term_dict(self) -> Dict[str, str]:
        """Export terms as {source: target} dict."""
        return {t.source: t.target for t in self.terms}


# ---------------------------------------------------------------------------
# GlossaryManager
# ---------------------------------------------------------------------------

class GlossaryManager:
    """Manage user glossaries with JSON persistence.

    Each glossary is stored as a separate JSON file in storage_dir.
    """

    def __init__(self, storage_dir: str = "data/glossaries") -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Glossary] = {}
        self._load_all()

    # --- CRUD: Glossaries ---

    def create_glossary(
        self,
        name: str,
        source_language: str = "en",
        target_language: str = "vi",
        description: str = "",
    ) -> str:
        """Create a new glossary. Returns glossary ID."""
        gid = uuid.uuid4().hex[:12]
        glossary = Glossary(
            id=gid,
            name=name,
            source_language=source_language,
            target_language=target_language,
            description=description,
        )
        self._cache[gid] = glossary
        self._save(gid)
        logger.info("Created glossary %s: %s", gid, name)
        return gid

    def get_glossary(self, glossary_id: str) -> Optional[Glossary]:
        """Get a glossary by ID."""
        return self._cache.get(glossary_id)

    def list_glossaries(self) -> List[Glossary]:
        """List all glossaries."""
        return list(self._cache.values())

    def delete_glossary(self, glossary_id: str) -> bool:
        """Delete a glossary. Returns True if deleted."""
        if glossary_id not in self._cache:
            return False
        del self._cache[glossary_id]
        path = self._glossary_path(glossary_id)
        if path.exists():
            path.unlink()
        logger.info("Deleted glossary %s", glossary_id)
        return True

    def update_glossary(
        self,
        glossary_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Glossary]:
        """Update glossary metadata."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return None
        if name is not None:
            glossary.name = name
        if description is not None:
            glossary.description = description
        glossary.updated_at = time.time()
        self._save(glossary_id)
        return glossary

    # --- CRUD: Terms ---

    def add_term(
        self,
        glossary_id: str,
        source: str,
        target: str,
        notes: str = "",
        domain: str = "general",
    ) -> bool:
        """Add a term to a glossary. Returns True on success."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return False

        # Check for duplicate source term
        for existing in glossary.terms:
            if existing.source.lower() == source.lower():
                existing.target = target
                existing.notes = notes
                existing.domain = domain
                glossary.updated_at = time.time()
                self._save(glossary_id)
                return True

        term = GlossaryTerm(
            source=source, target=target,
            notes=notes, domain=domain,
        )
        glossary.terms.append(term)
        glossary.updated_at = time.time()
        self._save(glossary_id)
        return True

    def remove_term(self, glossary_id: str, source: str) -> bool:
        """Remove a term by source text. Returns True if removed."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return False

        original_count = len(glossary.terms)
        glossary.terms = [
            t for t in glossary.terms
            if t.source.lower() != source.lower()
        ]

        if len(glossary.terms) < original_count:
            glossary.updated_at = time.time()
            self._save(glossary_id)
            return True
        return False

    def get_terms(self, glossary_id: str) -> List[GlossaryTerm]:
        """Get all terms in a glossary."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return []
        return glossary.terms

    # --- Integration ---

    def get_term_dict(self, glossary_id: str) -> Dict[str, str]:
        """Get terms as {source: target} dict for ConsistencyChecker."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return {}
        return glossary.get_term_dict()

    def merge_glossaries(self, glossary_ids: List[str]) -> Dict[str, str]:
        """Merge multiple glossaries into one dict. Later IDs override."""
        merged: Dict[str, str] = {}
        for gid in glossary_ids:
            merged.update(self.get_term_dict(gid))
        return merged

    def find_matches(self, text: str, glossary_id: str) -> List[GlossaryTerm]:
        """Find glossary terms that appear in text."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return []
        text_lower = text.lower()
        return [t for t in glossary.terms if t.source.lower() in text_lower]

    # --- Persistence ---

    def _glossary_path(self, glossary_id: str) -> Path:
        return self._storage_dir / f"{glossary_id}.json"

    def _save(self, glossary_id: str) -> None:
        """Save a single glossary to disk."""
        glossary = self._cache.get(glossary_id)
        if not glossary:
            return
        try:
            path = self._glossary_path(glossary_id)
            path.write_text(
                json.dumps(glossary.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save glossary %s: %s", glossary_id, exc)

    def _load_all(self) -> None:
        """Load all glossaries from disk."""
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                glossary = Glossary.from_dict(data)
                self._cache[glossary.id] = glossary
            except Exception as exc:
                logger.warning("Failed to load glossary %s: %s", path, exc)

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    @property
    def count(self) -> int:
        return len(self._cache)
