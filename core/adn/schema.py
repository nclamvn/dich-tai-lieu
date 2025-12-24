#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADN (Content DNA) Schema Definitions

Defines the structure for content DNA extraction output.
This schema is the contract between Agent #1 and Agent #2.

Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json


class ProperNounType(Enum):
    """Types of proper nouns"""
    PERSON = "person"
    PLACE = "place"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    EVENT = "event"
    WORK_OF_ART = "work_of_art"
    OTHER = "other"


class PatternType(Enum):
    """Types of structural patterns"""
    CHAPTER_START = "chapter_start"
    SECTION_BREAK = "section_break"
    QUOTE_BLOCK = "quote_block"
    EMPHASIS = "emphasis"
    LIST_STRUCTURE = "list_structure"
    DIALOGUE = "dialogue"
    FOOTNOTE = "footnote"
    HEADER_FOOTER = "header_footer"
    OTHER = "other"


@dataclass
class ProperNoun:
    """A proper noun entity"""
    text: str
    type: ProperNounType
    translations: Dict[str, str] = field(default_factory=dict)  # lang -> translation
    occurrences: List[int] = field(default_factory=list)  # segment indices
    confidence: float = 1.0
    variants: List[str] = field(default_factory=list)  # alternative forms

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "type": self.type.value,
            "translations": self.translations,
            "occurrences": self.occurrences,
            "confidence": self.confidence,
            "variants": self.variants,
        }


@dataclass
class Character:
    """A character/entity in the content"""
    name: str
    variants: List[str] = field(default_factory=list)
    role: Optional[str] = None  # protagonist, antagonist, supporting, etc.
    first_appearance: int = 0  # segment index
    occurrences: List[int] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "variants": self.variants,
            "role": self.role,
            "first_appearance": self.first_appearance,
            "occurrences": self.occurrences,
            "attributes": self.attributes,
        }


@dataclass
class Term:
    """A terminology entry"""
    original: str
    translation: str
    domain: str = "general"
    frequency: int = 1
    context_examples: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "translation": self.translation,
            "domain": self.domain,
            "frequency": self.frequency,
            "context_examples": self.context_examples[:3],  # Limit examples
        }


@dataclass
class Pattern:
    """A structural pattern in the content"""
    type: PatternType
    markers: List[str] = field(default_factory=list)  # text markers that identify this pattern
    regex: Optional[str] = None  # regex pattern if applicable
    occurrences: int = 0
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "markers": self.markers,
            "regex": self.regex,
            "occurrences": self.occurrences,
            "examples": self.examples[:3],
        }


@dataclass
class ContentADN:
    """
    Complete Content ADN (DNA) for a document.

    This is the output contract from Agent #1 to Agent #2.
    """
    # Metadata
    version: str = "1.0"
    source_language: str = ""
    target_language: str = ""
    document_type: str = "unknown"  # book, article, report, etc.

    # Content DNA
    characters: List[Character] = field(default_factory=list)
    terms: List[Term] = field(default_factory=list)
    proper_nouns: List[ProperNoun] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)

    # Statistics
    total_segments: int = 0
    total_characters: int = 0
    unique_terms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "metadata": {
                "source_language": self.source_language,
                "target_language": self.target_language,
                "document_type": self.document_type,
            },
            "adn": {
                "characters": [c.to_dict() for c in self.characters],
                "terms": [t.to_dict() for t in self.terms],
                "proper_nouns": [p.to_dict() for p in self.proper_nouns],
                "patterns": [p.to_dict() for p in self.patterns],
            },
            "statistics": {
                "total_segments": self.total_segments,
                "total_characters": self.total_characters,
                "unique_terms": self.unique_terms,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'ContentADN':
        """Create from dictionary"""
        adn = cls(
            version=data.get("version", "1.0"),
            source_language=data.get("metadata", {}).get("source_language", ""),
            target_language=data.get("metadata", {}).get("target_language", ""),
            document_type=data.get("metadata", {}).get("document_type", "unknown"),
        )

        adn_data = data.get("adn", {})

        # Parse characters
        for c in adn_data.get("characters", []):
            adn.characters.append(Character(
                name=c["name"],
                variants=c.get("variants", []),
                role=c.get("role"),
                first_appearance=c.get("first_appearance", 0),
                occurrences=c.get("occurrences", []),
                attributes=c.get("attributes", {}),
            ))

        # Parse terms
        for t in adn_data.get("terms", []):
            adn.terms.append(Term(
                original=t["original"],
                translation=t["translation"],
                domain=t.get("domain", "general"),
                frequency=t.get("frequency", 1),
            ))

        # Parse proper nouns
        for p in adn_data.get("proper_nouns", []):
            adn.proper_nouns.append(ProperNoun(
                text=p["text"],
                type=ProperNounType(p["type"]),
                translations=p.get("translations", {}),
                occurrences=p.get("occurrences", []),
                confidence=p.get("confidence", 1.0),
                variants=p.get("variants", []),
            ))

        # Parse patterns
        for p in adn_data.get("patterns", []):
            adn.patterns.append(Pattern(
                type=PatternType(p["type"]),
                markers=p.get("markers", []),
                regex=p.get("regex"),
                occurrences=p.get("occurrences", 0),
            ))

        stats = data.get("statistics", {})
        adn.total_segments = stats.get("total_segments", 0)
        adn.total_characters = stats.get("total_characters", 0)
        adn.unique_terms = stats.get("unique_terms", 0)

        return adn

    @classmethod
    def from_json(cls, json_str: str) -> 'ContentADN':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
