"""
Phase 1.9 Vietnamese Academic Polisher

Enhanced post-processing for STEM documents using corpus-derived glossary.
Focus: Vietnamese terminology consistency and academic phrasing improvements.

Key Features:
- Loads STEM-VN glossary from Phase 1.9 extraction
- Normalizes mathematical terminology to preferred forms
- Improves academic Vietnamese phrasing
- 100% formula preservation guarantee
- Detailed statistics tracking

DO NOT MODIFY:
- Mathematical formulas ($...$, $$...$$, \\[...\\], etc.)
- Proper nouns (mathematician names, universities)
- Theorem/Lemma/Proof numbering
- Citations and references
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path

from config.logging_config import get_logger
logger = get_logger(__name__)


@dataclass
class Phase19PolishingStats:
    """Detailed statistics from Phase 1.9 polishing"""
    # Terminology normalization
    terms_normalized: int = 0
    term_changes: Dict[str, int] = field(default_factory=dict)

    # Phrase improvements
    phrases_improved: int = 0
    phrase_changes: Dict[str, int] = field(default_factory=dict)

    # Structure preservation
    formulas_protected: int = 0
    formulas_corrupted: int = 0

    # Overall metrics
    total_changes: int = 0
    text_length_before: int = 0
    text_length_after: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'terms_normalized': self.terms_normalized,
            'phrases_improved': self.phrases_improved,
            'formulas_protected': self.formulas_protected,
            'formulas_corrupted': self.formulas_corrupted,
            'total_changes': self.total_changes,
            'text_length_before': self.text_length_before,
            'text_length_after': self.text_length_after,
            'top_term_changes': dict(sorted(
                self.term_changes.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            'top_phrase_changes': dict(sorted(
                self.phrase_changes.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }


class VietnameseAcademicPolisher:
    """
    Phase 1.9 Vietnamese Academic Polisher

    Applies corpus-based terminology normalization and academic phrasing
    improvements to Vietnamese STEM translations.

    Guarantees:
    - 100% formula preservation (never modifies math content)
    - Proper noun preservation (mathematician names, institutions)
    - Numbering preservation (Định lý 1.1, etc.)
    - Safe, conservative improvements only
    """

    def __init__(self, glossary_path: Optional[str] = None):
        """
        Initialize Phase 1.9 polisher

        Args:
            glossary_path: Path to STEM_VN_GLOSSARY_PHASE19.md
                          If None, uses default location
        """
        if glossary_path is None:
            # Default to docs/STEM_VN_GLOSSARY_PHASE19.md
            project_root = Path(__file__).parent.parent.parent
            glossary_path = project_root / "docs" / "STEM_VN_GLOSSARY_PHASE19.md"

        self.glossary_path = Path(glossary_path)
        self.term_mappings = self._load_glossary_terms()
        self.phrase_patterns = self._load_phrase_patterns()
        self.protected_patterns = self._load_protected_patterns()

    def _load_glossary_terms(self) -> Dict[str, str]:
        """
        Load term mappings from STEM-VN glossary.

        Extracts normalization rules like:
        - "ước tính" → "ước lượng"
        - "đánh giá" → "ước lượng" (in estimation context)
        - "tập" → "tập hợp" (in set theory context)

        Returns:
            Dict mapping Vietnamese variations to preferred form
        """
        mappings = {}

        if not self.glossary_path.exists():
            logger.warning(f"Glossary not found at {self.glossary_path}")
            return self._get_fallback_terms()

        # Parse glossary markdown table
        # Format: | EN term | VN term (preferred) | Alternatives (VN) | Frequency | Notes |
        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract table rows (skip headers)
            table_rows = re.findall(
                r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|',
                content
            )

            for row in table_rows:
                if len(row) < 3:
                    continue

                en_term = row[0].strip()
                vn_preferred = row[1].strip()
                vn_alternatives = row[2].strip()

                # Skip header rows and empty rows
                if en_term in ['EN Term', 'EN Phrase', '---', ''] or not vn_preferred:
                    continue

                # Map alternatives → preferred
                if vn_alternatives and vn_alternatives != '-':
                    for alt in vn_alternatives.split(','):
                        alt = alt.strip()
                        if alt:
                            mappings[alt] = vn_preferred

            logger.info(f"Loaded {len(mappings)} term normalizations from glossary")
            return mappings

        except Exception as e:
            logger.warning(f"Error loading glossary: {e}")
            return self._get_fallback_terms()

    def _get_fallback_terms(self) -> Dict[str, str]:
        """
        Fallback term mappings if glossary file not available.
        Based on Phase 1.9 corpus analysis.
        """
        return {
            # Estimation terminology (most common issue)
            "ước tính": "ước lượng",
            "đánh giá": "ước lượng",  # In mathematical estimation context

            # Set theory
            "tập": "tập hợp",  # When referring to sets, not groups

            # Proof terminology
            "bằng chứng": "chứng minh",  # "bằng chứng" is noun, "chứng minh" is verb

            # Academic connectors
            "cho thấy": "chỉ ra",  # More formal
            "chúng ta có": "ta có",  # Concise academic style
            "chúng ta thu được": "ta thu được",

            # Redundancy removal
            "một cách chính xác": "chính xác",
            "một cách rõ ràng": "rõ ràng",
        }

    def _load_phrase_patterns(self) -> List[Tuple[str, str, str]]:
        """
        Load phrase improvement patterns.

        Returns:
            List of (pattern, replacement, description) tuples
        """
        return [
            # Academic connectors
            (r'\bNó có nghĩa là\b', 'Điều này có nghĩa', 'academic_connector'),
            (r'\bĐiều đó có nghĩa là\b', 'Điều này có nghĩa', 'academic_connector'),
            (r'\bChúng ta có thể thấy rằng\b', 'Ta thấy rằng', 'academic_concision'),
            (r'\bChúng ta có\b', 'Ta có', 'academic_concision'),
            (r'\bChúng ta thu được\b', 'Ta thu được', 'academic_concision'),

            # Vietnamese academic style
            (r'\bđược cho bởi\b', 'được xác định bởi', 'academic_precision'),
            (r'\bđược tạo ra bởi\b', 'được sinh ra bởi', 'academic_style'),

            # Redundancy reduction
            (r'\bmột cách chính xác\b', 'chính xác', 'redundancy_removal'),
            (r'\bmột cách rõ ràng\b', 'rõ ràng', 'redundancy_removal'),
            (r'\bmột cách tự nhiên\b', 'tự nhiên', 'redundancy_removal'),

            # Spacing fixes (applied last)
            (r'\s+,', ',', 'punctuation'),
            (r'\s+\.', '.', 'punctuation'),
            (r'\s+;', ';', 'punctuation'),
            (r'\s+:', ':', 'punctuation'),
            (r'  +', ' ', 'whitespace'),
        ]

    def _load_protected_patterns(self) -> List[str]:
        """
        Load patterns for content that must NOT be modified.

        Returns:
            List of regex patterns to protect (proper nouns, etc.)
        """
        return [
            # Mathematician names (common in STEM docs)
            r'\b(Hilbert|Fourier|Cauchy|Schwarz|Hardy|Littlewood|'
            r'Vinogradov|Korobov|Borwein|Choi|Coons|Heisenberg|'
            r'Schrödinger|Euler|Gauss|Riemann|Poincaré)\b',

            # Institution names
            r'\b(Heidelberg|Cambridge|Oxford|MIT|Stanford)\b',

            # Grant/License IDs
            r'\b(DMS-\d+|CC-BY|arXiv:\d+\.\d+)\b',

            # Theorem numbering
            r'\b(Định lý|Bổ đề|Hệ quả|Mệnh đề|Định nghĩa)\s+\d+(\.\d+)*\b',

            # References
            r'\[\d+\]',
            r'\([A-Za-z]+\s+\d{4}\)',
        ]

    def polish(self, text: str, track_stats: bool = True) -> str:
        """
        Apply Vietnamese academic polishing to text.

        Args:
            text: Input Vietnamese text (translated STEM content)
            track_stats: If True, track detailed statistics

        Returns:
            Polished text with improved Vietnamese
        """
        if track_stats:
            polished, stats = self.polish_with_stats(text)
            return polished
        else:
            return self._apply_polishing(text)

    def _apply_polishing(self, text: str) -> str:
        """Core polishing logic without statistics"""
        # Step 1: Extract and protect formulas
        protected_regions = self._extract_protected_regions(text)
        text_safe, placeholders = self._protect_regions(text, protected_regions)

        # Step 2: Normalize terminology
        text_safe = self._normalize_terminology(text_safe)

        # Step 3: Improve phrases
        text_safe = self._improve_phrases(text_safe)

        # Step 4: Fix punctuation
        text_safe = self._fix_punctuation(text_safe)

        # Step 5: Restore protected content
        final_text = self._restore_protected(text_safe, placeholders)

        return final_text

    def polish_with_stats(self, text: str) -> Tuple[str, Phase19PolishingStats]:
        """
        Polish text and return detailed statistics.

        Args:
            text: Input Vietnamese text

        Returns:
            (polished_text, statistics)
        """
        stats = Phase19PolishingStats()
        stats.text_length_before = len(text)

        # Step 1: Extract and protect formulas
        protected_regions = self._extract_protected_regions(text)
        stats.formulas_protected = len([r for r in protected_regions if r[2] == 'formula'])

        text_safe, placeholders = self._protect_regions(text, protected_regions)

        # Step 2: Normalize terminology (with tracking)
        text_safe, term_stats = self._normalize_terminology_tracked(text_safe)
        stats.terms_normalized = sum(term_stats.values())
        stats.term_changes = term_stats

        # Step 3: Improve phrases (with tracking)
        text_safe, phrase_stats = self._improve_phrases_tracked(text_safe)
        stats.phrases_improved = sum(phrase_stats.values())
        stats.phrase_changes = phrase_stats

        # Step 4: Fix punctuation
        text_safe = self._fix_punctuation(text_safe)

        # Step 5: Restore protected content
        final_text = self._restore_protected(text_safe, placeholders)

        # Verify no formulas corrupted
        final_formula_count = len(self._extract_protected_regions(final_text))
        if final_formula_count < stats.formulas_protected:
            stats.formulas_corrupted = stats.formulas_protected - final_formula_count

        stats.text_length_after = len(final_text)
        stats.total_changes = stats.terms_normalized + stats.phrases_improved

        return final_text, stats

    def _extract_protected_regions(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Extract all regions that must not be modified.

        Returns:
            List of (start, end, type) tuples
            Types: 'formula', 'code', 'proper_noun'
        """
        regions = []

        # Math delimiters (order matters: longest first)
        math_patterns = [
            (r'\$\$.*?\$\$', 'formula'),  # Display math
            (r'\\\[.*?\\\]', 'formula'),  # LaTeX display brackets
            (r'\\begin\{[^}]+\}.*?\\end\{[^}]+\}', 'formula'),  # LaTeX environments
            (r'\\\(.*?\\\)', 'formula'),  # LaTeX inline parens
            (r'(?<!\$)\$(?!\$)[^\$]+?\$(?!\$)', 'formula'),  # Inline math (last)
        ]

        for pattern, region_type in math_patterns:
            for match in re.finditer(pattern, text, re.DOTALL):
                start, end = match.start(), match.end()
                if not self._overlaps_any(start, end, regions):
                    regions.append((start, end, region_type))

        # Code blocks
        for match in re.finditer(r'```.*?```', text, re.DOTALL):
            start, end = match.start(), match.end()
            if not self._overlaps_any(start, end, regions):
                regions.append((start, end, 'code'))

        # Protected patterns (proper nouns, etc.)
        for pattern in self.protected_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                if not self._overlaps_any(start, end, regions):
                    regions.append((start, end, 'proper_noun'))

        # Sort by position
        regions.sort(key=lambda x: x[0])
        return regions

    def _overlaps_any(self, start: int, end: int, regions: List[Tuple[int, int, str]]) -> bool:
        """Check if [start, end) overlaps with any existing region"""
        for r_start, r_end, _ in regions:
            if start < r_end and r_start < end:
                return True
        return False

    def _protect_regions(self, text: str, regions: List[Tuple[int, int, str]]) -> Tuple[str, Dict[str, str]]:
        """
        Replace protected regions with safe placeholders.

        Returns:
            (text_with_placeholders, placeholder_map)
        """
        if not regions:
            return text, {}

        placeholders = {}
        result = []
        last_pos = 0

        for i, (start, end, region_type) in enumerate(regions):
            # Add text before this region
            result.append(text[last_pos:start])

            # Create placeholder
            placeholder = f"⟪VN_POLISH_PROTECT_{i}⟫"
            result.append(placeholder)
            placeholders[placeholder] = text[start:end]

            last_pos = end

        # Add remaining text
        result.append(text[last_pos:])

        return ''.join(result), placeholders

    def _restore_protected(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restore protected content from placeholders"""
        result = text
        for placeholder, original in placeholders.items():
            result = result.replace(placeholder, original, 1)
        return result

    def _normalize_terminology(self, text: str) -> str:
        """Apply terminology normalizations"""
        result = text

        # Apply term mappings (longer terms first)
        sorted_terms = sorted(self.term_mappings.items(), key=lambda x: len(x[0]), reverse=True)

        for variant, preferred in sorted_terms:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variant) + r'\b'
            result = re.sub(pattern, preferred, result)

        return result

    def _normalize_terminology_tracked(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Apply terminology normalizations with change tracking"""
        result = text
        changes = {}

        sorted_terms = sorted(self.term_mappings.items(), key=lambda x: len(x[0]), reverse=True)

        for variant, preferred in sorted_terms:
            pattern = r'\b' + re.escape(variant) + r'\b'
            matches = re.findall(pattern, result)
            if matches:
                change_key = f"{variant} → {preferred}"
                changes[change_key] = len(matches)
                result = re.sub(pattern, preferred, result)

        return result, changes

    def _improve_phrases(self, text: str) -> str:
        """Apply phrase improvements"""
        result = text

        for pattern, replacement, _ in self.phrase_patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def _improve_phrases_tracked(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Apply phrase improvements with change tracking"""
        result = text
        changes = {}

        for pattern, replacement, category in self.phrase_patterns:
            matches = re.findall(pattern, result)
            if matches:
                change_key = f"{category}: {pattern[:30]}..."
                changes[change_key] = len(matches)
                result = re.sub(pattern, replacement, result)

        return result, changes

    def _fix_punctuation(self, text: str) -> str:
        """Fix Vietnamese punctuation conventions"""
        result = text

        # Add space after punctuation if missing
        result = re.sub(r'([,;:.!?])([^\s\n])', r'\1 \2', result)

        # Remove space before punctuation
        result = re.sub(r'\s+([,;:.!?])', r'\1', result)

        # Fix duplicate punctuation
        result = re.sub(r'([,;:.!?])\1+', r'\1', result)

        # Clean up multiple spaces
        result = re.sub(r'  +', ' ', result)

        # Clean up line-start spaces
        result = re.sub(r'^ +', '', result, flags=re.MULTILINE)

        return result


def main():
    """Test the polisher on sample text"""
    polisher = VietnameseAcademicPolisher()

    sample = """
    Chúng ta có thể thấy rằng ước tính này được cho bởi công thức $E = mc^2$.
    Định lý 1.1 chứng tỏ rằng tập này là liên tục.
    Theo Cauchy-Schwarz, chúng ta thu được bất đẳng thức  $$\\sum_{i=1}^n a_i^2 \\leq n$$ .
    """

    logger.info("Original:")
    logger.info(sample)
    logger.info("=" * 50)

    polished, stats = polisher.polish_with_stats(sample)

    logger.info("Polished:")
    logger.info(polished)
    logger.info("=" * 50)

    logger.info("Statistics:")
    logger.info(f"Terms normalized: {stats.terms_normalized}")
    logger.info(f"Phrases improved: {stats.phrases_improved}")
    logger.info(f"Formulas protected: {stats.formulas_protected}")
    logger.info(f"Formulas corrupted: {stats.formulas_corrupted}")
    logger.info(f"Total changes: {stats.total_changes}")

    if stats.term_changes:
        logger.info("Term changes:")
        for change, count in stats.term_changes.items():
            logger.info(f"  {change}: {count}x")

    if stats.phrase_changes:
        logger.info("Phrase changes:")
        for change, count in stats.phrase_changes.items():
            logger.info(f"  {change}: {count}x")


if __name__ == '__main__':
    main()
