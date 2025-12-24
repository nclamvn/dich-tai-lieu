#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Types and Constants

Provides unified type definitions used across both STEM and Formatting modules
to ensure consistency and enable code reuse.

Usage:
    from core.shared import ElementType, DetectionResult

    result = DetectionResult(
        element_type=ElementType.CODE_BLOCK,
        content="def hello(): pass",
        language="python"
    )
"""

from .element_types import ElementType, STEM_BLOCKTYPE_MAPPING, FORMATTING_TYPE_MAPPING
from .detection_result import DetectionResult

__all__ = [
    "ElementType",
    "DetectionResult",
    "STEM_BLOCKTYPE_MAPPING",
    "FORMATTING_TYPE_MAPPING",
]
