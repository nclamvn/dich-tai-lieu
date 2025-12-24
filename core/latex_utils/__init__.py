"""
LaTeX utilities for equation extraction and processing.

Phase 2.1.2: LaTeX Math Extractor
"""

from .latex_math_extractor import (
    MathSegment,
    extract_math_segments,
    select_primary_equation,
    is_valid_single_equation,
    enrich_node_with_equations,
)

__all__ = [
    'MathSegment',
    'extract_math_segments',
    'select_primary_equation',
    'is_valid_single_equation',
    'enrich_node_with_equations',
]
