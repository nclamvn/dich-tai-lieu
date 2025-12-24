"""
Academic Vietnamese Polisher

Post-processing module to enhance Vietnamese translation quality for academic/STEM documents.
Improves terminology, phrase structure, and readability while preserving mathematical content.

Phase 1.6 - Academic Presentation Layer
"""

import re
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class PolishingStats:
    """Statistics from polishing operation"""
    terms_normalized: int = 0
    phrases_improved: int = 0
    punctuation_fixes: int = 0
    total_changes: int = 0


class AcademicVietnamesePolisher:
    """
    Enhances Vietnamese academic prose quality.

    Key features:
    - Normalizes technical terminology to Vietnamese academic standards
    - Improves sentence structure and flow
    - Fixes punctuation for Vietnamese academic style
    - Preserves all STEM content (formulas, code) unchanged
    """

    def __init__(self, glossary_mgr=None):
        """
        Initialize academic polisher

        Args:
            glossary_mgr: Optional GlossaryManager for term consistency
        """
        self.glossary_mgr = glossary_mgr
        self.academic_terms = self._load_academic_terms()
        self.phrase_patterns = self._load_phrase_patterns()

    def _load_academic_terms(self) -> Dict[str, str]:
        """
        Load academic Vietnamese terminology mappings.

        These are common STEM terms that need consistent Vietnamese translation.
        Expands on glossary with academic-specific phrase corrections.
        """
        return {
            # Physics - Quantum Mechanics
            "wave-particle duality": "tính lưỡng tính sóng–hạt",
            "Wave-Particle Duality": "Tính lưỡng tính sóng–hạt",
            "wave particle duality": "tính lưỡng tính sóng–hạt",
            "Wave-Particle Tính Đối Xứng": "Tính lưỡng tính sóng–hạt",  # Fix common error
            # HOTFIX 1.6.1: Handle mix English-Vietnamese
            "Wave-Particle Tính chất lưỡng tính": "Tính lưỡng tính sóng–hạt",
            "Wave-Particle tính chất lưỡng tính": "tính lưỡng tính sóng–hạt",
            "Wave-Particle": "Tính lưỡng tính sóng–hạt",
            "Heisenberg uncertainty principle": "nguyên lý bất định Heisenberg",
            "Schrödinger equation": "phương trình Schrödinger",
            "wave function": "hàm sóng",
            "quantum state": "trạng thái lượng tử",
            "quantum mechanics": "cơ học lượng tử",
            "quantum system": "hệ lượng tử",
            "energy eigenvalue": "trị riêng năng lượng",
            "ground state": "trạng thái cơ bản",
            "excited state": "trạng thái kích thích",

            # Mathematics
            "Hilbert space": "không gian Hilbert",
            "vector space": "không gian vector",
            "inner product": "tích vô hướng",
            "linear operator": "toán tử tuyến tính",
            "eigenvalue": "trị riêng",
            "eigenvector": "vector riêng",
            "discrete sequence": "dãy rời rạc",
            "continuous function": "hàm liên tục",
            "differential equation": "phương trình vi phân",
            "partial derivative": "đạo hàm riêng",
            "boundary condition": "điều kiện biên",
            "initial condition": "điều kiện đầu",

            # General Academic
            "in particular": "cụ thể",
            "for example": "ví dụ",
            "such that": "sao cho",
            "it follows that": "từ đó suy ra",
            "we can see that": "ta thấy rằng",
            "note that": "lưu ý rằng",
            "recall that": "nhớ lại rằng",
            "assume that": "giả sử",
            "suppose that": "giả sử",
            "let us": "ta hãy",
            "we have": "ta có",
            "we obtain": "ta thu được",
        }

    def _load_phrase_patterns(self) -> List[tuple]:
        """
        Load phrase improvement patterns.

        Returns list of (pattern, replacement) tuples for regex substitution.
        These fix common awkward literal translations.
        """
        return [
            # Fix spacing around punctuation
            (r'\s+,', ','),
            (r'\s+\.', '.'),
            (r'\s+:', ':'),
            (r'\s+;', ';'),

            # Fix double spaces
            (r'  +', ' '),

            # Fix spacing around quotes
            (r'\"\s+', '"'),
            (r'\s+\"', '"'),

            # Vietnamese-specific punctuation improvements
            (r'([,;:])([^\s])', r'\1 \2'),  # Add space after punctuation if missing

            # Fix "được + verb" patterns that sound robotic
            (r'được thể hiện bởi', 'được biểu diễn bằng'),
            (r'được cho bởi', 'được xác định bởi'),
            (r'được tạo ra bởi', 'được sinh ra bởi'),

            # Academic connector improvements
            (r'Nó có nghĩa là', 'Điều này có nghĩa'),
            (r'Điều đó có nghĩa là', 'Điều này có nghĩa'),
            (r'Chúng ta có thể thấy rằng', 'Ta thấy rằng'),
            (r'Chúng ta có', 'Ta có'),
            (r'Chúng ta thu được', 'Ta thu được'),

            # Remove redundant "một cách"
            (r'một cách chính xác', 'chính xác'),
            (r'một cách rõ ràng', 'rõ ràng'),
        ]

    def polish(self, text: str) -> str:
        """
        Apply academic Vietnamese improvements to text.

        Args:
            text: Input Vietnamese text (may contain STEM placeholders)

        Returns:
            Improved text with better academic Vietnamese

        Process:
        1. Extract and protect STEM content (formulas, code)
        2. Normalize terminology
        3. Improve phrases
        4. Fix punctuation
        5. Restore STEM content
        """
        # Step 1: Extract STEM content for protection
        protected_regions = self._extract_stem_regions(text)
        text_with_placeholders = self._replace_with_placeholders(text, protected_regions)

        # Step 2: Apply improvements
        text_with_placeholders = self._normalize_terminology(text_with_placeholders)
        text_with_placeholders = self._improve_phrases(text_with_placeholders)
        text_with_placeholders = self._fix_punctuation(text_with_placeholders)

        # Step 3: Restore STEM content
        final_text = self._restore_stem_content(text_with_placeholders, protected_regions)

        # PHASE 1.6.3: Normalize inline math delimiters
        # Fix translation errors like $$h$ → $h$ (inline vars incorrectly using display delimiters)
        final_text = self._normalize_inline_delimiters(final_text)

        return final_text

    def _extract_stem_regions(self, text: str) -> List[tuple]:
        """
        Extract positions of STEM content that must not be modified.

        Returns list of (start, end, content) tuples.

        PHASE 1.6.2 FIX: Match longer delimiters FIRST to prevent overlapping regions.
        Order matters: display math ($$) before inline math ($).
        """
        regions = []

        # CRITICAL: Match display math FIRST (longer delimiter takes priority)
        # Display math: $$...$$
        for match in re.finditer(r'\$\$.*?\$\$', text, re.DOTALL):
            regions.append((match.start(), match.end(), match.group()))

        # LaTeX brackets: \[...\] (also display math)
        for match in re.finditer(r'\\\[.*?\\\]', text, re.DOTALL):
            regions.append((match.start(), match.end(), match.group()))

        # LaTeX environments: \begin{...}...\end{...}
        for match in re.finditer(r'\\begin\{[^}]+\}.*?\\end\{[^}]+\}', text, re.DOTALL):
            regions.append((match.start(), match.end(), match.group()))

        # Code blocks (if any)
        for match in re.finditer(r'```.*?```', text, re.DOTALL):
            regions.append((match.start(), match.end(), match.group()))

        # LaTeX parentheses: \(...\)
        for match in re.finditer(r'\\\(.*?\\\)', text):
            start, end = match.start(), match.end()
            if not self._overlaps_existing(start, end, regions):
                regions.append((start, end, match.group()))

        # Inline math: $...$ (match LAST, with overlap detection)
        # Use negative lookahead/lookbehind to avoid matching inside $$
        for match in re.finditer(r'(?<!\$)\$(?!\$)[^\$]+?\$(?!\$)', text):
            start, end = match.start(), match.end()
            # Only add if not overlapping with existing regions
            if not self._overlaps_existing(start, end, regions):
                regions.append((start, end, match.group()))

        # Sort by start position
        regions.sort(key=lambda x: x[0])

        return regions

    def _overlaps_existing(self, start: int, end: int, regions: List[tuple]) -> bool:
        """
        Check if a region [start, end) overlaps with any existing region.

        Two regions overlap if: start1 < end2 AND start2 < end1
        """
        for r_start, r_end, _ in regions:
            if start < r_end and r_start < end:
                return True
        return False

    def _replace_with_placeholders(self, text: str, regions: List[tuple]) -> str:
        """
        Replace STEM regions with placeholders for safe processing.
        """
        if not regions:
            return text

        result = []
        last_pos = 0

        for i, (start, end, content) in enumerate(regions):
            # Add text before this region
            result.append(text[last_pos:start])
            # Add placeholder
            result.append(f"⟪POLISH_PROTECT_{i}⟫")
            last_pos = end

        # Add remaining text
        result.append(text[last_pos:])

        return ''.join(result)

    def _restore_stem_content(self, text: str, regions: List[tuple]) -> str:
        """
        Restore original STEM content from placeholders.
        """
        result = text

        for i, (start, end, content) in enumerate(regions):
            placeholder = f"⟪POLISH_PROTECT_{i}⟫"
            result = result.replace(placeholder, content, 1)

        return result

    def _normalize_terminology(self, text: str) -> str:
        """
        Normalize academic terminology using dictionary.
        """
        result = text

        # Apply term replacements (longer terms first to avoid partial matches)
        sorted_terms = sorted(self.academic_terms.items(), key=lambda x: len(x[0]), reverse=True)

        for english, vietnamese in sorted_terms:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(english) + r'\b'
            result = re.sub(pattern, vietnamese, result, flags=re.IGNORECASE)

        return result

    def _improve_phrases(self, text: str) -> str:
        """
        Improve phrase structure using patterns.
        """
        result = text

        for pattern, replacement in self.phrase_patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def _fix_punctuation(self, text: str) -> str:
        """
        Fix Vietnamese academic punctuation conventions.
        """
        result = text

        # Vietnamese uses spaces after punctuation marks
        result = re.sub(r'([,;:.!?])([^\s\n])', r'\1 \2', result)

        # Remove spaces before punctuation
        result = re.sub(r'\s+([,;:.!?])', r'\1', result)

        # Fix multiple punctuation marks
        result = re.sub(r'([,;:.!?])\1+', r'\1', result)

        # Clean up multiple spaces
        result = re.sub(r'  +', ' ', result)

        # Clean up space at start of lines
        result = re.sub(r'^ +', '', result, flags=re.MULTILINE)

        return result

    def _normalize_inline_delimiters(self, text: str) -> str:
        """
        PHASE 1.6.3: Fix inline math using display delimiters.

        Translation sometimes produces mixed/malformed delimiters:
        1. $$VAR$ → $VAR$ (short inline vars with display open)
        2. $$FORMULA$ → $$FORMULA$$ (display formulas missing closing $$)

        Examples:
          "Trong đó $$h$ là..." → "Trong đó $h$ là..."
          "$$n=1$) là..."       → "$(n=1$) là..."
          "$$\\hat{H} = ...$ ." → "$$\\hat{H} = ...$$ ."

        Does NOT touch:
          - Display equations: $$\\lambda = \\frac{h}{p}$$ (already correct)
          - Properly delimited inline: $h$ (already correct)
        """
        result = text

        # Fix 1: $$LONG_FORMULA$ → $$LONG_FORMULA$$ (add missing closing $$)
        # Match $$CONTENT$ where CONTENT is >15 chars (likely a display formula)
        # This catches: $$\hat{H} = -\frac{\hbar^2}{2m}\nabla^2 + V(\mathbf{r})$
        def fix_malformed_display(match):
            content = match.group(1)
            # If content is long, it's a display formula missing closing $$
            if len(content) > 15:
                return f'$${content}$$'
            # If short, will be handled by next pattern
            return match.group(0)

        # Apply display fix first (greedy match for long formulas)
        result = re.sub(r'\$\$([^\$]+?)\$(?!\$)', fix_malformed_display, result)

        # Fix 2: $$SHORT_VAR$ → $SHORT_VAR$ (short inline vars)
        # Match $$CONTENT$ where CONTENT is ≤15 chars
        def normalize_short_inline(match):
            content = match.group(1)
            if len(content) <= 15:
                return f'${content}$'
            return match.group(0)

        result = re.sub(r'\$\$([^\$]{1,15}?)\$(?!\$)', normalize_short_inline, result)

        # Fix 3: $VAR$$ (inline open, display close) - also incorrect
        result = re.sub(r'(?<!\$)\$([^\$]{1,15}?)\$\$', r'$\1$', result)

        return result

    def polish_with_stats(self, text: str) -> tuple[str, PolishingStats]:
        """
        Polish text and return statistics.

        Returns:
            (polished_text, stats)
        """
        # Track changes (simplified - could be more sophisticated)
        original_text = text
        polished_text = self.polish(text)

        stats = PolishingStats()

        # Count differences as rough metric
        if original_text != polished_text:
            # Estimate changes
            stats.total_changes = 1
            stats.terms_normalized = len([t for t in self.academic_terms.keys() if t in original_text])
            stats.phrases_improved = len([p for p, r in self.phrase_patterns if re.search(p, original_text)])

        return polished_text, stats
