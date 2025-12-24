#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEM Integration Bridge

Allows Formatting Engine to reuse STEM module's detection capabilities
without duplicating code. Provides fallback detection when STEM module
is not available.

Usage:
    from core.formatting.utils.stem_integration import get_stem_integration

    stem = get_stem_integration()

    # Check availability
    if stem.is_available():
        code_results = stem.detect_code(text)
        formula_results = stem.detect_formulas(text)
    else:
        # Fallback detection will be used automatically
        code_results = stem.detect_code(text)
"""

import re
from typing import List, Optional
from pathlib import Path
import sys

# Ensure core modules are importable
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import shared types
from core.shared.element_types import ElementType
from core.shared.detection_result import DetectionResult

# Try to import STEM module
try:
    from core.stem.code_detector import CodeDetector, CodeMatch, CodeType
    from core.stem.formula_detector import FormulaDetector, FormulaMatch, FormulaType
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False
    CodeDetector = None
    FormulaDetector = None
    CodeMatch = None
    FormulaMatch = None
    CodeType = None
    FormulaType = None


class STEMIntegration:
    """
    Bridge class to use STEM detection in Formatting Engine.

    Provides a unified interface for code and formula detection that:
    - Uses STEM module when available (full-featured detection)
    - Falls back to basic patterns when STEM is not available

    Usage:
        stem = STEMIntegration()

        # Detect code blocks
        code_results = stem.detect_code(text)

        # Detect formulas
        formula_results = stem.detect_formulas(text)

        # Detect all STEM elements
        all_results = stem.detect_all_stem_elements(text)
    """

    def __init__(self):
        """Initialize STEM integration with detectors if available."""
        self._code_detector = CodeDetector() if STEM_AVAILABLE and CodeDetector else None
        self._formula_detector = FormulaDetector() if STEM_AVAILABLE and FormulaDetector else None

    def is_available(self) -> bool:
        """
        Check if STEM module is available.

        Returns:
            True if STEM module can be imported
        """
        return STEM_AVAILABLE

    def detect_code(self, text: str) -> List[DetectionResult]:
        """
        Detect code blocks using STEM's CodeDetector.

        Uses full-featured STEM detection if available,
        otherwise falls back to basic pattern matching.

        Args:
            text: Input text to scan

        Returns:
            List of DetectionResult with CODE_BLOCK or CODE_INLINE type
        """
        if self._code_detector:
            return self._detect_code_via_stem(text)
        else:
            return self._fallback_code_detection(text)

    def detect_formulas(self, text: str, include_chemical: bool = True) -> List[DetectionResult]:
        """
        Detect mathematical formulas using STEM's FormulaDetector.

        Uses full-featured STEM detection if available,
        otherwise falls back to basic LaTeX pattern matching.

        Args:
            text: Input text to scan
            include_chemical: Include chemical formula detection

        Returns:
            List of DetectionResult with FORMULA_BLOCK, FORMULA_INLINE, or CHEMICAL_FORMULA type
        """
        if self._formula_detector:
            return self._detect_formulas_via_stem(text, include_chemical)
        else:
            return self._fallback_formula_detection(text)

    def detect_all_stem_elements(self, text: str) -> List[DetectionResult]:
        """
        Detect all STEM elements (code + formulas).

        Args:
            text: Input text to scan

        Returns:
            Combined list sorted by position
        """
        code_results = self.detect_code(text)
        formula_results = self.detect_formulas(text)

        # Combine and sort by position
        all_results = code_results + formula_results
        all_results.sort(key=lambda x: x.start_pos)

        # Remove overlapping results (keep first/larger)
        return self._remove_overlaps(all_results)

    def has_stem_content(self, text: str) -> bool:
        """
        Quick check if text contains any STEM content.

        Args:
            text: Text to check

        Returns:
            True if code or formulas detected
        """
        if self._code_detector and self._code_detector.has_code(text):
            return True
        if self._formula_detector and self._formula_detector.has_formulas(text):
            return True

        # Fallback quick checks
        if '```' in text or '`' in text:
            return True
        if '$' in text or '\\[' in text or '\\(' in text:
            return True

        return False

    # =========================================================================
    # STEM-based detection (when STEM module is available)
    # =========================================================================

    def _detect_code_via_stem(self, text: str) -> List[DetectionResult]:
        """Detect code using STEM's CodeDetector."""
        results = []
        code_matches = self._code_detector.detect_code(text)

        for match in code_matches:
            # Determine element type based on code type
            if match.code_type == CodeType.FENCED:
                element_type = ElementType.CODE_BLOCK
                is_fenced = True
            elif match.code_type == CodeType.INDENTED:
                element_type = ElementType.CODE_BLOCK
                is_fenced = False
            else:  # INLINE
                element_type = ElementType.CODE_INLINE
                is_fenced = False

            results.append(DetectionResult(
                element_type=element_type,
                content=match.content,
                start_pos=match.start,
                end_pos=match.end,
                language=match.language or "",
                is_fenced=is_fenced,
                indent_level=match.indent_level if hasattr(match, 'indent_level') else None,
                metadata={"source": "stem"},
            ))

        return results

    def _detect_formulas_via_stem(self, text: str, include_chemical: bool = True) -> List[DetectionResult]:
        """Detect formulas using STEM's FormulaDetector."""
        results = []
        formula_matches = self._formula_detector.detect_formulas(text, include_chemical=include_chemical)

        for match in formula_matches:
            # Determine element type based on formula type
            if match.formula_type == FormulaType.CHEMICAL:
                element_type = ElementType.CHEMICAL_FORMULA
            elif match.formula_type in [FormulaType.DISPLAY_DOLLAR, FormulaType.DISPLAY_BRACKET, FormulaType.LATEX_ENV]:
                element_type = ElementType.FORMULA_BLOCK
            else:
                element_type = ElementType.FORMULA_INLINE

            results.append(DetectionResult(
                element_type=element_type,
                content=match.content,
                start_pos=match.start,
                end_pos=match.end,
                formula_type=match.formula_type.value if match.formula_type else None,
                environment_name=match.environment_name if hasattr(match, 'environment_name') else None,
                metadata={"source": "stem"},
            ))

        return results

    # =========================================================================
    # Fallback detection (when STEM module is not available)
    # =========================================================================

    def _fallback_code_detection(self, text: str) -> List[DetectionResult]:
        """
        Fallback code detection using basic patterns.

        Detects:
        - Fenced code blocks: ```lang ... ```
        - Inline code: `code`
        """
        results = []

        # Fenced code blocks
        fenced_pattern = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)
        for match in fenced_pattern.finditer(text):
            language = match.group(1) or ""
            code_content = match.group(2)

            results.append(DetectionResult(
                element_type=ElementType.CODE_BLOCK,
                content=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                language=language,
                is_fenced=True,
                metadata={"source": "fallback", "code": code_content},
            ))

        # Inline code
        inline_pattern = re.compile(r'`([^`\n]+?)`')
        for match in inline_pattern.finditer(text):
            # Skip if inside a fenced block
            in_fenced = False
            for fenced in results:
                if fenced.start_pos <= match.start() <= fenced.end_pos:
                    in_fenced = True
                    break

            if not in_fenced:
                results.append(DetectionResult(
                    element_type=ElementType.CODE_INLINE,
                    content=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    is_fenced=False,
                    metadata={"source": "fallback"},
                ))

        return results

    def _fallback_formula_detection(self, text: str) -> List[DetectionResult]:
        """
        Fallback formula detection using basic LaTeX patterns.

        Detects:
        - Display math: $$...$$ or \\[...\\]
        - Inline math: $...$ or \\(...\\)
        """
        results = []

        # Display math: $$...$$
        display_dollar = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
        for match in display_dollar.finditer(text):
            results.append(DetectionResult(
                element_type=ElementType.FORMULA_BLOCK,
                content=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                formula_type="display_dollar",
                metadata={"source": "fallback"},
            ))

        # Display math: \[...\]
        display_bracket = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)
        for match in display_bracket.finditer(text):
            results.append(DetectionResult(
                element_type=ElementType.FORMULA_BLOCK,
                content=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                formula_type="display_bracket",
                metadata={"source": "fallback"},
            ))

        # Inline math: $...$ (not $$)
        inline_dollar = re.compile(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)')
        for match in inline_dollar.finditer(text):
            # Skip if inside a display block
            in_display = False
            for display in results:
                if display.start_pos <= match.start() <= display.end_pos:
                    in_display = True
                    break

            if not in_display:
                results.append(DetectionResult(
                    element_type=ElementType.FORMULA_INLINE,
                    content=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    formula_type="inline_dollar",
                    metadata={"source": "fallback"},
                ))

        # Inline math: \(...\)
        inline_paren = re.compile(r'\\\((.+?)\\\)', re.DOTALL)
        for match in inline_paren.finditer(text):
            results.append(DetectionResult(
                element_type=ElementType.FORMULA_INLINE,
                content=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                formula_type="inline_paren",
                metadata={"source": "fallback"},
            ))

        return results

    def _remove_overlaps(self, results: List[DetectionResult]) -> List[DetectionResult]:
        """Remove overlapping results, keeping first/larger."""
        if not results:
            return []

        # Sort by start position, then by length (descending)
        results.sort(key=lambda x: (x.start_pos, -(x.end_pos - x.start_pos)))

        non_overlapping = []
        for result in results:
            overlaps = False
            for accepted in non_overlapping:
                if (result.start_pos < accepted.end_pos and result.end_pos > accepted.start_pos):
                    overlaps = True
                    break

            if not overlaps:
                non_overlapping.append(result)

        return non_overlapping


# Singleton instance
_stem_integration: Optional[STEMIntegration] = None


def get_stem_integration() -> STEMIntegration:
    """
    Get singleton STEMIntegration instance.

    Returns:
        STEMIntegration instance
    """
    global _stem_integration
    if _stem_integration is None:
        _stem_integration = STEMIntegration()
    return _stem_integration


def reset_stem_integration():
    """Reset singleton instance (for testing)."""
    global _stem_integration
    _stem_integration = None
