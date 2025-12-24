"""
Quality Checker Module

Provides quality validation for translations, including:
- Length ratio checks
- Placeholder consistency validation
- STEM preservation verification

Lightweight, non-blocking quality checks for translation pipeline.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from core.stem.formula_detector import FormulaDetector
from core.stem.code_detector import CodeDetector


@dataclass
class QualityReport:
    """Quality check report for a translation"""
    length_ratio: float
    length_ratio_ok: bool
    missing_placeholders: List[str] = field(default_factory=list)
    extra_placeholders: List[str] = field(default_factory=list)
    placeholder_consistency_ok: bool = True
    stem_preservation_ok: bool = True
    warnings: List[str] = field(default_factory=list)
    overall_pass: bool = True

    def __repr__(self) -> str:
        status = "✓ PASS" if self.overall_pass else "✗ FAIL"
        return (
            f"QualityReport({status}, "
            f"ratio={self.length_ratio:.2f}, "
            f"warnings={len(self.warnings)})"
        )

    def summary(self) -> str:
        """Get human-readable summary"""
        lines = []
        lines.append(f"Quality Check: {'✓ PASS' if self.overall_pass else '✗ FAIL'}")
        lines.append(f"  Length ratio: {self.length_ratio:.2f} {'✓' if self.length_ratio_ok else '✗'}")
        lines.append(f"  Placeholders: {'✓' if self.placeholder_consistency_ok else '✗'}")

        if self.missing_placeholders:
            lines.append(f"    Missing: {self.missing_placeholders}")
        if self.extra_placeholders:
            lines.append(f"    Extra: {self.extra_placeholders}")

        lines.append(f"  STEM preservation: {'✓' if self.stem_preservation_ok else '✗'}")

        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"    - {warning}")

        return "\n".join(lines)


def check_length_ratio(
    source_text: str,
    translated_text: str,
    min_ratio: float = 0.5,
    max_ratio: float = 3.0
) -> dict:
    """
    Check if translation length is reasonable compared to source

    Args:
        source_text: Source text
        translated_text: Translated text
        min_ratio: Minimum allowed ratio (default: 0.5)
        max_ratio: Maximum allowed ratio (default: 3.0)

    Returns:
        Dictionary with 'ratio' and 'ok' keys

    Example:
        >>> check_length_ratio("Hello world", "Bonjour le monde")
        {'ratio': 1.45, 'ok': True}
    """
    source_len = len(source_text)
    translated_len = len(translated_text)

    if source_len == 0:
        ratio = 0.0 if translated_len == 0 else float('inf')
        ok = translated_len == 0
    else:
        ratio = translated_len / source_len
        ok = min_ratio <= ratio <= max_ratio

    return {
        'ratio': ratio,
        'ok': ok
    }


def check_placeholder_consistency(
    source_text: str,
    translated_text: str
) -> dict:
    """
    Check if all STEM placeholders are preserved in translation

    Args:
        source_text: Source text with placeholders
        translated_text: Translated text

    Returns:
        Dictionary with 'missing', 'extra', and 'ok' keys

    Example:
        >>> source = "The formula ⟪STEM_F0⟫ is important"
        >>> target = "La formule ⟪STEM_F0⟫ est importante"
        >>> check_placeholder_consistency(source, target)
        {'missing': [], 'extra': [], 'ok': True}
    """
    # Extract all STEM placeholders (formulas, code, chemicals)
    placeholder_pattern = re.compile(r'⟪STEM_[FCT]\d+⟫')

    source_placeholders = set(placeholder_pattern.findall(source_text))
    translated_placeholders = set(placeholder_pattern.findall(translated_text))

    missing = sorted(source_placeholders - translated_placeholders)
    extra = sorted(translated_placeholders - source_placeholders)

    ok = len(missing) == 0 and len(extra) == 0

    return {
        'missing': missing,
        'extra': extra,
        'ok': ok
    }


def check_stem_preservation(
    source_text: str,
    translated_text: str,
    formula_detector: Optional[FormulaDetector] = None,
    code_detector: Optional[CodeDetector] = None
) -> dict:
    """
    Check if STEM content (formulas, code) was properly detected and preserved

    Args:
        source_text: Original source text (before placeholder substitution)
        translated_text: Translated text (with placeholders restored)
        formula_detector: Optional FormulaDetector instance
        code_detector: Optional CodeDetector instance

    Returns:
        Dictionary with 'warnings' and 'ok' keys

    Note:
        This check looks for STEM content that might have been missed
        during the protection phase. It's a heuristic check, not definitive.
    """
    warnings = []

    # Initialize detectors if not provided
    if formula_detector is None:
        formula_detector = FormulaDetector()
    if code_detector is None:
        code_detector = CodeDetector()

    # Check if source has formulas that weren't protected
    formulas = formula_detector.detect_formulas(source_text, include_chemical=True)
    for formula in formulas:
        # Check if this formula appears unprotected in translated text
        # (If it was protected, it should be a placeholder, not raw formula)
        if formula.content in translated_text:
            warnings.append(
                f"Unprotected formula found in translation: {formula.content[:50]}"
            )

    # Check if source has code that wasn't protected
    code_blocks = code_detector.detect_code(source_text)
    for code in code_blocks:
        # Skip inline code (too many false positives)
        if code.code_type.value == 'inline':
            continue

        # Check if this code block appears unprotected
        if code.content in translated_text:
            warnings.append(
                f"Unprotected code found in translation: {code.content[:50]}"
            )

    ok = len(warnings) == 0

    return {
        'warnings': warnings,
        'ok': ok
    }


def build_quality_report(
    source_text: str,
    translated_text: str,
    original_source: Optional[str] = None,
    min_ratio: float = 0.5,
    max_ratio: float = 3.0
) -> QualityReport:
    """
    Build comprehensive quality report for a translation

    Args:
        source_text: Source text (with placeholders)
        translated_text: Translated text (with placeholders)
        original_source: Original source text before placeholder substitution
                        (for STEM preservation check)
        min_ratio: Minimum length ratio
        max_ratio: Maximum length ratio

    Returns:
        QualityReport with all checks aggregated

    Example:
        >>> source = "The equation ⟪STEM_F0⟫ is fundamental."
        >>> translated = "L'équation ⟪STEM_F0⟫ est fondamentale."
        >>> report = build_quality_report(source, translated)
        >>> print(report.summary())
    """
    # Check length ratio
    length_check = check_length_ratio(source_text, translated_text, min_ratio, max_ratio)

    # Check placeholder consistency
    placeholder_check = check_placeholder_consistency(source_text, translated_text)

    # Check STEM preservation (if original source provided)
    stem_check = {'warnings': [], 'ok': True}
    if original_source:
        stem_check = check_stem_preservation(original_source, translated_text)

    # Collect warnings
    warnings = []

    if not length_check['ok']:
        warnings.append(
            f"Length ratio out of bounds: {length_check['ratio']:.2f} "
            f"(expected {min_ratio}-{max_ratio})"
        )

    if placeholder_check['missing']:
        warnings.append(
            f"Missing placeholders: {', '.join(placeholder_check['missing'])}"
        )

    if placeholder_check['extra']:
        warnings.append(
            f"Extra placeholders: {', '.join(placeholder_check['extra'])}"
        )

    warnings.extend(stem_check['warnings'])

    # Determine overall pass/fail
    overall_pass = (
        length_check['ok'] and
        placeholder_check['ok'] and
        stem_check['ok']
    )

    return QualityReport(
        length_ratio=length_check['ratio'],
        length_ratio_ok=length_check['ok'],
        missing_placeholders=placeholder_check['missing'],
        extra_placeholders=placeholder_check['extra'],
        placeholder_consistency_ok=placeholder_check['ok'],
        stem_preservation_ok=stem_check['ok'],
        warnings=warnings,
        overall_pass=overall_pass
    )


# Example usage and testing
if __name__ == "__main__":
    print("Quality Checker - Demo")
    print("=" * 80)

    # Test 1: Good translation
    print("\n1. Good translation:")
    source1 = "The equation ⟪STEM_F0⟫ is fundamental in physics."
    translated1 = "L'équation ⟪STEM_F0⟫ est fondamentale en physique."
    report1 = build_quality_report(source1, translated1)
    print(report1.summary())

    # Test 2: Missing placeholder
    print("\n2. Missing placeholder:")
    source2 = "Both ⟪STEM_F0⟫ and ⟪STEM_F1⟫ are important."
    translated2 = "Both ⟪STEM_F0⟫ are important."
    report2 = build_quality_report(source2, translated2)
    print(report2.summary())

    # Test 3: Length ratio issue
    print("\n3. Length ratio issue:")
    source3 = "Hello world"
    translated3 = "This is a very long translation that doesn't match the source length"
    report3 = build_quality_report(source3, translated3)
    print(report3.summary())

    # Test 4: STEM preservation check
    print("\n4. STEM preservation check:")
    original = "The formula $E = mc^2$ is Einstein's equation."
    with_placeholder = "The formula ⟪STEM_F0⟫ is Einstein's equation."
    translated_good = "La formule ⟪STEM_F0⟫ est l'équation d'Einstein."
    translated_bad = "La formule $E = mc^2$ est l'équation d'Einstein."

    report4a = build_quality_report(with_placeholder, translated_good, original)
    print("\nGood STEM preservation:")
    print(report4a.summary())

    report4b = build_quality_report(with_placeholder, translated_bad, original)
    print("\nBad STEM preservation (unprotected formula in translation):")
    print(report4b.summary())

    print("\n" + "=" * 80)
    print("✓ Quality checker demo complete!")
