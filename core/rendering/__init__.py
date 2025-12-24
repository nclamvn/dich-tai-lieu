"""
Phase 2.0.3b - Rendering Module

Handles conversion of LaTeX equations to various output formats (OMML, MathML, etc.)
"""

from .omml_converter import (
    latex_to_omml,
    inject_omml_into_paragraph,
    strip_latex_delimiters
)

__all__ = [
    'latex_to_omml',
    'inject_omml_into_paragraph',
    'strip_latex_delimiters',
]
