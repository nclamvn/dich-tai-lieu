#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Intent Package Contract

Defines the output contract from Agent #2 (Editorial Core).
This is what Agent #2 produces and Agent #3 consumes.

Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json

from .base import BaseContract, ContractMetadata


class BlockType(Enum):
    """Types of content blocks"""
    TITLE = "title"
    SUBTITLE = "subtitle"
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    QUOTE = "quote"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    FORMULA = "formula"
    IMAGE = "image"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    PAGE_NUMBER = "page_number"
    HEADER = "header"
    FOOTER = "footer"
    TOC_ENTRY = "toc_entry"
    INDEX_ENTRY = "index_entry"
    SEPARATOR = "separator"
    SCENE_BREAK = "scene_break"
    EPIGRAPH = "epigraph"


class SectionType(Enum):
    """Types of book sections"""
    COVER = "cover"
    TITLE_PAGE = "title_page"
    COPYRIGHT = "copyright"
    DEDICATION = "dedication"
    FOREWORD = "foreword"
    PREFACE = "preface"
    ACKNOWLEDGMENTS = "acknowledgments"
    TABLE_OF_CONTENTS = "table_of_contents"
    LIST_OF_FIGURES = "list_of_figures"
    LIST_OF_TABLES = "list_of_tables"
    INTRODUCTION = "introduction"
    MAIN_BODY = "main_body"
    CHAPTER = "chapter"
    EPILOGUE = "epilogue"
    AFTERWORD = "afterword"
    APPENDIX = "appendix"
    GLOSSARY = "glossary"
    BIBLIOGRAPHY = "bibliography"
    INDEX = "index"
    COLOPHON = "colophon"


class TransitionType(Enum):
    """Types of section transitions"""
    NONE = "none"
    PAGE_BREAK = "page_break"
    SECTION_BREAK = "section_break"
    CHAPTER_BREAK = "chapter_break"  # Start on odd page
    CONTINUOUS = "continuous"


@dataclass
class SpacingRule:
    """Spacing rules for blocks"""
    before: float = 0  # Points or mm
    after: float = 0
    line_spacing: float = 1.0  # Multiplier
    unit: str = "pt"  # pt, mm, cm

    def to_dict(self) -> Dict:
        return {
            "before": self.before,
            "after": self.after,
            "line_spacing": self.line_spacing,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SpacingRule':
        return cls(
            before=data.get("before", 0),
            after=data.get("after", 0),
            line_spacing=data.get("line_spacing", 1.0),
            unit=data.get("unit", "pt"),
        )


@dataclass
class Block:
    """A content block with layout intent"""
    id: str
    type: BlockType
    content: str
    section: SectionType = SectionType.MAIN_BODY
    level: int = 0  # Hierarchy level

    # Spacing
    spacing: SpacingRule = field(default_factory=SpacingRule)

    # Transitions
    break_before: TransitionType = TransitionType.NONE
    break_after: TransitionType = TransitionType.NONE

    # Style hints (not enforcement)
    style_hints: Dict[str, Any] = field(default_factory=dict)

    # Numbering
    number: Optional[str] = None  # Chapter/section number
    include_in_toc: bool = False
    toc_level: int = 0

    # References
    references: List[str] = field(default_factory=list)  # IDs of related blocks

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "section": self.section.value,
            "level": self.level,
            "spacing": self.spacing.to_dict(),
            "break_before": self.break_before.value,
            "break_after": self.break_after.value,
            "style_hints": self.style_hints,
            "number": self.number,
            "include_in_toc": self.include_in_toc,
            "toc_level": self.toc_level,
            "references": self.references,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Block':
        return cls(
            id=data["id"],
            type=BlockType(data["type"]),
            content=data.get("content", ""),
            section=SectionType(data.get("section", "main_body")),
            level=data.get("level", 0),
            spacing=SpacingRule.from_dict(data.get("spacing", {})),
            break_before=TransitionType(data.get("break_before", "none")),
            break_after=TransitionType(data.get("break_after", "none")),
            style_hints=data.get("style_hints", {}),
            number=data.get("number"),
            include_in_toc=data.get("include_in_toc", False),
            toc_level=data.get("toc_level", 0),
            references=data.get("references", []),
        )


@dataclass
class SectionDefinition:
    """Definition of a document section"""
    type: SectionType
    start_block_id: str
    end_block_id: str

    # Section properties
    numbering_style: str = "arabic"  # arabic, roman, alpha, none
    numbering_start: int = 1
    header_text: str = ""
    footer_text: str = ""

    # Page properties
    start_on_odd_page: bool = False
    different_first_page: bool = False

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "start_block_id": self.start_block_id,
            "end_block_id": self.end_block_id,
            "numbering_style": self.numbering_style,
            "numbering_start": self.numbering_start,
            "header_text": self.header_text,
            "footer_text": self.footer_text,
            "start_on_odd_page": self.start_on_odd_page,
            "different_first_page": self.different_first_page,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SectionDefinition':
        return cls(
            type=SectionType(data["type"]),
            start_block_id=data["start_block_id"],
            end_block_id=data["end_block_id"],
            numbering_style=data.get("numbering_style", "arabic"),
            numbering_start=data.get("numbering_start", 1),
            header_text=data.get("header_text", ""),
            footer_text=data.get("footer_text", ""),
            start_on_odd_page=data.get("start_on_odd_page", False),
            different_first_page=data.get("different_first_page", False),
        )


@dataclass
class ConsistencyReport:
    """Report on content consistency"""
    term_inconsistencies: List[Dict] = field(default_factory=list)
    style_inconsistencies: List[Dict] = field(default_factory=list)
    numbering_issues: List[Dict] = field(default_factory=list)
    reference_issues: List[Dict] = field(default_factory=list)
    resolved_count: int = 0
    unresolved_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "term_inconsistencies": self.term_inconsistencies,
            "style_inconsistencies": self.style_inconsistencies,
            "numbering_issues": self.numbering_issues,
            "reference_issues": self.reference_issues,
            "resolved_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConsistencyReport':
        return cls(
            term_inconsistencies=data.get("term_inconsistencies", []),
            style_inconsistencies=data.get("style_inconsistencies", []),
            numbering_issues=data.get("numbering_issues", []),
            reference_issues=data.get("reference_issues", []),
            resolved_count=data.get("resolved_count", 0),
            unresolved_count=data.get("unresolved_count", 0),
        )


@dataclass
class LayoutIntentPackage(BaseContract):
    """
    Complete output from Agent #2 (Editorial Core).

    This contract defines the Layout Intent Package (LIP):
    - Ordered blocks with layout intent
    - Section definitions
    - Consistency report
    - Template reference
    """

    # Metadata
    _metadata: ContractMetadata = field(default_factory=lambda: ContractMetadata(
        source_agent="editorial_core",
        target_agent="layout_core",
    ))

    # Document info
    title: str = ""
    subtitle: str = ""
    author: str = ""
    template: str = "default"  # Template name to use

    # Ordered blocks
    blocks: List[Block] = field(default_factory=list)

    # Section definitions
    sections: List[SectionDefinition] = field(default_factory=list)

    # Front matter components (optional, auto-generated)
    toc_blocks: List[Block] = field(default_factory=list)

    # Consistency report
    consistency: ConsistencyReport = field(default_factory=ConsistencyReport)

    # Processing notes for Agent #3
    notes: List[str] = field(default_factory=list)

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
            "document": {
                "title": self.title,
                "subtitle": self.subtitle,
                "author": self.author,
                "template": self.template,
            },
            "blocks": [b.to_dict() for b in self.blocks],
            "sections": [s.to_dict() for s in self.sections],
            "toc_blocks": [b.to_dict() for b in self.toc_blocks],
            "consistency": self.consistency.to_dict(),
            "notes": self.notes,
        }

        # Calculate checksum
        self._metadata.checksum = self._metadata.calculate_checksum(data)
        data["metadata"]["checksum"] = self._metadata.checksum

        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutIntentPackage':
        lip = cls()

        # Metadata
        meta = data.get("metadata", {})
        lip._metadata = ContractMetadata(
            version=meta.get("version", "1.0"),
            created_at=meta.get("created_at", ""),
            source_agent=meta.get("source_agent", "editorial_core"),
            target_agent=meta.get("target_agent", "layout_core"),
            checksum=meta.get("checksum", ""),
        )

        # Document info
        doc = data.get("document", {})
        lip.title = doc.get("title", "")
        lip.subtitle = doc.get("subtitle", "")
        lip.author = doc.get("author", "")
        lip.template = doc.get("template", "default")

        # Blocks
        lip.blocks = [Block.from_dict(b) for b in data.get("blocks", [])]

        # Sections
        lip.sections = [SectionDefinition.from_dict(s) for s in data.get("sections", [])]

        # TOC
        lip.toc_blocks = [Block.from_dict(b) for b in data.get("toc_blocks", [])]

        # Consistency
        lip.consistency = ConsistencyReport.from_dict(data.get("consistency", {}))

        # Notes
        lip.notes = data.get("notes", [])

        return lip

    def validate(self) -> List[str]:
        """Validate the contract"""
        errors = []

        # Blocks required
        if not self.blocks:
            errors.append("blocks cannot be empty")

        # Block ID uniqueness
        seen_ids = set()
        for i, block in enumerate(self.blocks):
            if not block.id:
                errors.append(f"block[{i}].id is required")
            elif block.id in seen_ids:
                errors.append(f"block[{i}].id '{block.id}' is duplicate")
            else:
                seen_ids.add(block.id)

        # Section validation
        for i, section in enumerate(self.sections):
            if section.start_block_id not in seen_ids:
                errors.append(f"section[{i}].start_block_id '{section.start_block_id}' not found")
            if section.end_block_id not in seen_ids:
                errors.append(f"section[{i}].end_block_id '{section.end_block_id}' not found")

        return errors

    # Convenience methods
    def get_blocks_by_section(self, section_type: SectionType) -> List[Block]:
        """Get blocks in a specific section"""
        return [b for b in self.blocks if b.section == section_type]

    def get_blocks_by_type(self, block_type: BlockType) -> List[Block]:
        """Get blocks of a specific type"""
        return [b for b in self.blocks if b.type == block_type]

    def get_toc_entries(self) -> List[Block]:
        """Get blocks that should appear in TOC"""
        return [b for b in self.blocks if b.include_in_toc]

    def get_chapters(self) -> List[Block]:
        """Get chapter blocks"""
        return [b for b in self.blocks if b.type == BlockType.CHAPTER]

    def get_block_by_id(self, block_id: str) -> Optional[Block]:
        """Get block by ID"""
        for b in self.blocks:
            if b.id == block_id:
                return b
        return None

    def add_block(self, block: Block) -> None:
        """Add a block to the package"""
        self.blocks.append(block)

    def add_section(self, section: SectionDefinition) -> None:
        """Add a section definition"""
        self.sections.append(section)

    def get_full_text(self) -> str:
        """Get full document text from blocks"""
        return "\n\n".join(b.content for b in self.blocks if b.content)

    def count_by_type(self) -> Dict[str, int]:
        """Count blocks by type"""
        counts = {}
        for block in self.blocks:
            type_name = block.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
