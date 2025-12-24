#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Detection Result

Provides a standardized result format for element detection
used by both STEM module and Formatting Engine.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .element_types import ElementType


@dataclass
class DetectionResult:
    """
    Unified detection result for both STEM and Formatting modules.

    This class provides a common interface for detection results,
    allowing code reuse between STEM and Formatting modules.

    Attributes:
        element_type: Type of detected element
        content: The detected content
        start_pos: Start position in original text
        end_pos: End position in original text
        line_number: Line number (0-indexed)
        level: For headings - level 1-4
        language: For code blocks - programming language
        is_fenced: For code blocks - True if fenced (```)
        formula_type: For formulas - type (latex, unicode, chemical)
        placeholder: For STEM - placeholder string (⟪STEM_*⟫)
        style_hints: Additional styling information
        children: Nested elements (for lists, tables)
        confidence: Detection confidence score (0.0-1.0)
        metadata: Additional metadata
    """

    element_type: ElementType
    content: str

    # Position info
    start_pos: int = 0
    end_pos: int = 0
    line_number: int = 0

    # Element-specific metadata
    level: Optional[int] = None          # For headings: 1-4
    language: Optional[str] = None       # For code blocks
    is_fenced: Optional[bool] = None     # For code blocks
    indent_level: Optional[int] = None   # For indented code

    # STEM-specific
    formula_type: Optional[str] = None   # LATEX_DISPLAY, LATEX_INLINE, CHEMICAL, etc.
    placeholder: Optional[str] = None    # ⟪STEM_*⟫
    environment_name: Optional[str] = None  # For LaTeX environments

    # Formatting-specific
    style_hints: Dict[str, Any] = field(default_factory=dict)

    # Children (for nested elements like lists, tables)
    children: List['DetectionResult'] = field(default_factory=list)

    # Quality
    confidence: float = 1.0

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize data."""
        # Ensure end_pos >= start_pos
        if self.end_pos < self.start_pos:
            self.end_pos = self.start_pos + len(self.content)

    @property
    def length(self) -> int:
        """Length of the detected content."""
        return self.end_pos - self.start_pos

    @property
    def is_stem_element(self) -> bool:
        """Check if this is a STEM-specific element."""
        return ElementType.is_code(self.element_type) or ElementType.is_formula(self.element_type)

    @property
    def is_block_element(self) -> bool:
        """Check if this is a block-level element."""
        block_types = [
            ElementType.CODE_BLOCK,
            ElementType.FORMULA_BLOCK,
            ElementType.BLOCKQUOTE,
            ElementType.TABLE,
            ElementType.FIGURE,
            ElementType.HORIZONTAL_RULE,
        ]
        return self.element_type in block_types or ElementType.is_heading(self.element_type)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "type": self.element_type.name,
            "content": self.content,
            "start": self.start_pos,
            "end": self.end_pos,
            "line": self.line_number,
        }

        # Add optional fields if set
        if self.level is not None:
            result["level"] = self.level
        if self.language:
            result["language"] = self.language
        if self.is_fenced is not None:
            result["is_fenced"] = self.is_fenced
        if self.formula_type:
            result["formula_type"] = self.formula_type
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.style_hints:
            result["style_hints"] = self.style_hints
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        if self.confidence != 1.0:
            result["confidence"] = self.confidence
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DetectionResult':
        """
        Create from dictionary.

        Args:
            data: Dictionary with detection result data

        Returns:
            DetectionResult instance
        """
        # Get element type from string
        element_type = ElementType[data.get("type", "UNKNOWN")]

        # Parse children recursively
        children = []
        if "children" in data:
            children = [cls.from_dict(c) for c in data["children"]]

        return cls(
            element_type=element_type,
            content=data.get("content", ""),
            start_pos=data.get("start", 0),
            end_pos=data.get("end", 0),
            line_number=data.get("line", 0),
            level=data.get("level"),
            language=data.get("language"),
            is_fenced=data.get("is_fenced"),
            formula_type=data.get("formula_type"),
            placeholder=data.get("placeholder"),
            style_hints=data.get("style_hints", {}),
            children=children,
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation."""
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"DetectionResult({self.element_type.name}, '{preview}')"
