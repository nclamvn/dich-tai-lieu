"""
Layout DNA 2.0 — Structured Document Representation.

Represents a document as a sequence of typed regions:
  TEXT, TABLE, FORMULA, HEADING, LIST, IMAGE, CODE

Design goals:
  1. full_text property for backward compatibility (plain string)
  2. Typed regions for layout-aware processing
  3. Serializable (to_dict / from_dict / to_json)
  4. Standalone — no extraction or translation imports

Region order matches reading order in the original document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Region types
# ---------------------------------------------------------------------------

class RegionType(str, Enum):
    """Types of document regions."""

    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    HEADING = "heading"
    LIST = "list"
    IMAGE = "image"
    CODE = "code"


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------

@dataclass
class Region:
    """One contiguous region of a document.

    Attributes:
        type: The region type.
        content: Raw text content (plain text, markdown table, LaTeX, etc.)
        level: Heading level (1-6) or list nesting depth. 0 for non-hierarchical.
        metadata: Extra info (caption, language, formula_mode, etc.)
        page: Source page number (0-indexed, -1 if unknown).
        start_offset: Character offset in the original full text.
        end_offset: Character offset (exclusive) in the original full text.
    """

    type: RegionType
    content: str
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    page: int = -1
    start_offset: int = 0
    end_offset: int = 0

    # -- Convenience helpers -------------------------------------------------

    @property
    def is_structural(self) -> bool:
        """Region that defines document structure (heading, list)."""
        return self.type in (RegionType.HEADING, RegionType.LIST)

    @property
    def is_special(self) -> bool:
        """Region with specialised rendering (table, formula, code, image)."""
        return self.type in (
            RegionType.TABLE,
            RegionType.FORMULA,
            RegionType.CODE,
            RegionType.IMAGE,
        )

    @property
    def char_count(self) -> int:
        return len(self.content)

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "level": self.level,
            "metadata": self.metadata,
            "page": self.page,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Region":
        return cls(
            type=RegionType(data["type"]),
            content=data["content"],
            level=data.get("level", 0),
            metadata=data.get("metadata", {}),
            page=data.get("page", -1),
            start_offset=data.get("start_offset", 0),
            end_offset=data.get("end_offset", 0),
        )


# ---------------------------------------------------------------------------
# LayoutDNA
# ---------------------------------------------------------------------------

@dataclass
class LayoutDNA:
    """Full layout representation of a document.

    Backward compatible via ``full_text`` — any code doing
    ``str(dna)`` or using ``dna.full_text`` gets plain text.
    """

    regions: List[Region] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- Backward-compat property -------------------------------------------

    @property
    def full_text(self) -> str:
        """Concatenate all regions into one plain-text string.

        Joins with double newline between regions to preserve
        paragraph boundaries.
        """
        parts = [r.content for r in self.regions if r.content]
        return "\n\n".join(parts)

    def __str__(self) -> str:
        return self.full_text

    def __len__(self) -> int:
        return sum(len(r.content) for r in self.regions)

    # -- Query helpers -------------------------------------------------------

    def regions_of_type(self, rtype: RegionType) -> List[Region]:
        """Return all regions of a given type."""
        return [r for r in self.regions if r.type == rtype]

    @property
    def tables(self) -> List[Region]:
        return self.regions_of_type(RegionType.TABLE)

    @property
    def formulas(self) -> List[Region]:
        return self.regions_of_type(RegionType.FORMULA)

    @property
    def headings(self) -> List[Region]:
        return self.regions_of_type(RegionType.HEADING)

    @property
    def code_blocks(self) -> List[Region]:
        return self.regions_of_type(RegionType.CODE)

    @property
    def region_count(self) -> int:
        return len(self.regions)

    @property
    def has_tables(self) -> bool:
        return any(r.type == RegionType.TABLE for r in self.regions)

    @property
    def has_formulas(self) -> bool:
        return any(r.type == RegionType.FORMULA for r in self.regions)

    @property
    def has_code(self) -> bool:
        return any(r.type == RegionType.CODE for r in self.regions)

    def type_distribution(self) -> Dict[str, int]:
        """Count of regions per type."""
        dist: Dict[str, int] = {}
        for r in self.regions:
            key = r.type.value
            dist[key] = dist.get(key, 0) + 1
        return dist

    # -- Mutation helpers ----------------------------------------------------

    def add_region(
        self,
        rtype: RegionType,
        content: str,
        *,
        level: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        page: int = -1,
    ) -> Region:
        """Append a new region and return it."""
        offset = sum(len(r.content) for r in self.regions)
        # account for the "\n\n" joins in full_text
        if self.regions:
            offset += 2 * len(self.regions)
        region = Region(
            type=rtype,
            content=content,
            level=level,
            metadata=metadata or {},
            page=page,
            start_offset=offset,
            end_offset=offset + len(content),
        )
        self.regions.append(region)
        return region

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "regions": [r.to_dict() for r in self.regions],
            "metadata": self.metadata,
            "region_count": self.region_count,
            "type_distribution": self.type_distribution(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LayoutDNA":
        regions = [Region.from_dict(rd) for rd in data.get("regions", [])]
        return cls(
            regions=regions,
            metadata=data.get("metadata", {}),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "LayoutDNA":
        return cls.from_dict(json.loads(json_str))

    # -- Summary -------------------------------------------------------------

    def summary(self) -> str:
        """Human-readable one-line summary."""
        dist = self.type_distribution()
        parts = [f"{v} {k}" for k, v in sorted(dist.items())]
        return (
            f"LayoutDNA: {self.region_count} regions "
            f"({', '.join(parts)}), "
            f"{len(self)} chars"
        )
