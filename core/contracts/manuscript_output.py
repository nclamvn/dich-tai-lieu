#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manuscript Core Output Contract

Defines the output contract from Agent #1 (Manuscript Core).
This is what Agent #1 produces and Agent #2 consumes.

Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json

from .base import BaseContract, ContractMetadata


class SegmentType(Enum):
    """Types of document segments"""
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    QUOTE = "quote"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    FORMULA = "formula"
    IMAGE = "image"
    FOOTNOTE = "footnote"
    FRONT_MATTER = "front_matter"
    BACK_MATTER = "back_matter"


@dataclass
class Segment:
    """A translated document segment"""
    id: str
    type: SegmentType
    level: int = 0  # Hierarchy level (0 = root)
    original_text: str = ""
    translated_text: str = ""
    position: Dict[str, int] = field(default_factory=lambda: {"start": 0, "end": 0})
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "level": self.level,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "position": self.position,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Segment':
        return cls(
            id=data["id"],
            type=SegmentType(data["type"]),
            level=data.get("level", 0),
            original_text=data.get("original_text", ""),
            translated_text=data.get("translated_text", ""),
            position=data.get("position", {"start": 0, "end": 0}),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DocumentStructure:
    """Document structure information"""
    total_chapters: int = 0
    total_sections: int = 0
    total_paragraphs: int = 0
    heading_hierarchy: List[Dict] = field(default_factory=list)
    has_front_matter: bool = False
    has_back_matter: bool = False
    has_footnotes: bool = False
    has_images: bool = False
    has_tables: bool = False

    def to_dict(self) -> Dict:
        return {
            "total_chapters": self.total_chapters,
            "total_sections": self.total_sections,
            "total_paragraphs": self.total_paragraphs,
            "heading_hierarchy": self.heading_hierarchy,
            "has_front_matter": self.has_front_matter,
            "has_back_matter": self.has_back_matter,
            "has_footnotes": self.has_footnotes,
            "has_images": self.has_images,
            "has_tables": self.has_tables,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentStructure':
        return cls(
            total_chapters=data.get("total_chapters", 0),
            total_sections=data.get("total_sections", 0),
            total_paragraphs=data.get("total_paragraphs", 0),
            heading_hierarchy=data.get("heading_hierarchy", []),
            has_front_matter=data.get("has_front_matter", False),
            has_back_matter=data.get("has_back_matter", False),
            has_footnotes=data.get("has_footnotes", False),
            has_images=data.get("has_images", False),
            has_tables=data.get("has_tables", False),
        )


@dataclass
class QualityMetrics:
    """Translation quality metrics"""
    overall_score: float = 0.0
    confidence_mean: float = 0.0
    confidence_min: float = 0.0
    segments_high_confidence: int = 0  # > 0.8
    segments_medium_confidence: int = 0  # 0.5 - 0.8
    segments_low_confidence: int = 0  # < 0.5
    issues: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "confidence_mean": self.confidence_mean,
            "confidence_min": self.confidence_min,
            "segments_high_confidence": self.segments_high_confidence,
            "segments_medium_confidence": self.segments_medium_confidence,
            "segments_low_confidence": self.segments_low_confidence,
            "issues": self.issues,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'QualityMetrics':
        return cls(
            overall_score=data.get("overall_score", 0.0),
            confidence_mean=data.get("confidence_mean", 0.0),
            confidence_min=data.get("confidence_min", 0.0),
            segments_high_confidence=data.get("segments_high_confidence", 0),
            segments_medium_confidence=data.get("segments_medium_confidence", 0),
            segments_low_confidence=data.get("segments_low_confidence", 0),
            issues=data.get("issues", []),
        )


@dataclass
class ManuscriptCoreOutput(BaseContract):
    """
    Complete output from Agent #1 (Manuscript Core).

    This contract defines everything Agent #1 produces:
    - Translated segments
    - Document structure
    - Content ADN
    - STEM elements
    - Quality metrics
    """

    # Metadata
    _metadata: ContractMetadata = field(default_factory=lambda: ContractMetadata(
        source_agent="manuscript_core",
        target_agent="editorial_core",
    ))

    # Source information
    source_file: str = ""
    source_format: str = ""  # pdf, docx, txt, md
    source_language: str = ""
    target_language: str = ""
    is_scanned: bool = False
    total_pages: int = 0

    # Translated content
    segments: List[Segment] = field(default_factory=list)

    # Document structure
    structure: DocumentStructure = field(default_factory=DocumentStructure)

    # Content ADN (from core.adn module)
    adn: Dict[str, Any] = field(default_factory=dict)

    # STEM elements
    stem: Dict[str, Any] = field(default_factory=lambda: {
        "formulas": [],
        "code_blocks": [],
        "tables": [],
    })

    # Quality metrics
    quality: QualityMetrics = field(default_factory=QualityMetrics)

    @property
    def metadata(self) -> ContractMetadata:
        return self._metadata

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "metadata": {
                "version": self._metadata.version,
                "created_at": self._metadata.created_at,
                "source_agent": self._metadata.source_agent,
                "target_agent": self._metadata.target_agent,
            },
            "source": {
                "file": self.source_file,
                "format": self.source_format,
                "source_language": self.source_language,
                "target_language": self.target_language,
                "is_scanned": self.is_scanned,
                "total_pages": self.total_pages,
            },
            "segments": [s.to_dict() for s in self.segments],
            "structure": self.structure.to_dict(),
            "adn": self.adn,
            "stem": self.stem,
            "quality": self.quality.to_dict(),
        }

        # Calculate and add checksum
        self._metadata.checksum = self._metadata.calculate_checksum(data)
        data["metadata"]["checksum"] = self._metadata.checksum

        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ManuscriptCoreOutput':
        output = cls()

        # Metadata
        meta = data.get("metadata", {})
        output._metadata = ContractMetadata(
            version=meta.get("version", "1.0"),
            created_at=meta.get("created_at", ""),
            source_agent=meta.get("source_agent", "manuscript_core"),
            target_agent=meta.get("target_agent", "editorial_core"),
            checksum=meta.get("checksum", ""),
        )

        # Source info
        source = data.get("source", {})
        output.source_file = source.get("file", "")
        output.source_format = source.get("format", "")
        output.source_language = source.get("source_language", "")
        output.target_language = source.get("target_language", "")
        output.is_scanned = source.get("is_scanned", False)
        output.total_pages = source.get("total_pages", 0)

        # Segments
        output.segments = [Segment.from_dict(s) for s in data.get("segments", [])]

        # Structure
        output.structure = DocumentStructure.from_dict(data.get("structure", {}))

        # ADN
        output.adn = data.get("adn", {})

        # STEM
        output.stem = data.get("stem", {"formulas": [], "code_blocks": [], "tables": []})

        # Quality
        output.quality = QualityMetrics.from_dict(data.get("quality", {}))

        return output

    def validate(self) -> List[str]:
        """Validate the contract"""
        errors = []

        # Required fields
        if not self.source_language:
            errors.append("source_language is required")
        if not self.target_language:
            errors.append("target_language is required")
        if not self.segments:
            errors.append("segments cannot be empty")

        # Segment validation
        seen_ids = set()
        for i, seg in enumerate(self.segments):
            if not seg.id:
                errors.append(f"segment[{i}].id is required")
            elif seg.id in seen_ids:
                errors.append(f"segment[{i}].id '{seg.id}' is duplicate")
            else:
                seen_ids.add(seg.id)

            if not seg.translated_text and not seg.original_text:
                errors.append(f"segment[{i}] has no text")

        # Quality score range
        if not (0 <= self.quality.overall_score <= 1):
            errors.append("quality.overall_score must be between 0 and 1")

        return errors

    # Convenience methods
    def get_full_text(self, translated: bool = True) -> str:
        """Get full document text"""
        if translated:
            return "\n\n".join(s.translated_text for s in self.segments if s.translated_text)
        return "\n\n".join(s.original_text for s in self.segments if s.original_text)

    def get_segments_by_type(self, segment_type: SegmentType) -> List[Segment]:
        """Get segments of a specific type"""
        return [s for s in self.segments if s.type == segment_type]

    def get_low_confidence_segments(self, threshold: float = 0.5) -> List[Segment]:
        """Get segments with confidence below threshold"""
        return [s for s in self.segments if s.confidence < threshold]

    def get_segment_by_id(self, segment_id: str) -> Optional[Segment]:
        """Get segment by ID"""
        for s in self.segments:
            if s.id == segment_id:
                return s
        return None

    def add_segment(self, segment: Segment) -> None:
        """Add a segment to the output"""
        self.segments.append(segment)

    def update_quality_metrics(self) -> None:
        """Update quality metrics based on current segments"""
        if not self.segments:
            return

        confidences = [s.confidence for s in self.segments]
        self.quality.confidence_mean = sum(confidences) / len(confidences)
        self.quality.confidence_min = min(confidences)

        self.quality.segments_high_confidence = sum(1 for c in confidences if c > 0.8)
        self.quality.segments_medium_confidence = sum(1 for c in confidences if 0.5 <= c <= 0.8)
        self.quality.segments_low_confidence = sum(1 for c in confidences if c < 0.5)

        # Overall score based on confidence distribution
        self.quality.overall_score = self.quality.confidence_mean
