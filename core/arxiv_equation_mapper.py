"""
Phase 2.1.0 - arXiv Equation Mapper

Maps extracted LaTeX equations to document positions for OMML replacement.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from core.arxiv_latex_extractor import ArxivLatexExtractor, LatexEquation

logger = logging.getLogger(__name__)


@dataclass
class EquationMapping:
    """Maps a document position to LaTeX source."""
    page_num: int  # Page number in PDF
    char_offset: int  # Character offset in page text
    pdf_text: str  # Text extracted from PDF (usually broken Unicode)
    latex_source: LatexEquation  # Proper LaTeX from source
    confidence: float  # Match confidence (0.0 to 1.0)


class ArxivEquationMapper:
    """
    Maps PDF equation positions to LaTeX source equations.

    This enables replacing broken PDF-extracted equation text with proper
    LaTeX for perfect OMML rendering.
    """

    def __init__(self, tar_gz_path: str):
        """
        Initialize mapper with arXiv source archive.

        Args:
            tar_gz_path: Path to arXiv .tar.gz file
        """
        self.tar_gz_path = Path(tar_gz_path)
        self.extractor = ArxivLatexExtractor(str(tar_gz_path))
        self.equations: List[LatexEquation] = []
        self.mappings: List[EquationMapping] = []

    def extract_equations(self) -> List[LatexEquation]:
        """
        Extract equations from source archive.

        Returns:
            List of extracted LaTeX equations
        """
        self.equations = self.extractor.extract()
        logger.info(f"Extracted {len(self.equations)} equations from LaTeX source")
        return self.equations

    def map_pdf_text_to_latex(
        self,
        pdf_text: str,
        page_num: int,
        char_offset: int,
        min_confidence: float = 0.6
    ) -> Optional[EquationMapping]:
        """
        Map PDF-extracted text to proper LaTeX source.

        Args:
            pdf_text: Text extracted from PDF (may be broken Unicode)
            page_num: Page number in PDF
            char_offset: Character offset in page
            min_confidence: Minimum confidence for match (0.0 to 1.0)

        Returns:
            EquationMapping if match found, None otherwise
        """
        if not self.equations:
            logger.warning("No equations extracted yet. Call extract_equations() first.")
            return None

        best_match = None
        best_confidence = 0.0

        # Clean PDF text for matching
        pdf_clean = self._clean_text_for_matching(pdf_text)

        for eq in self.equations:
            # Try multiple matching strategies
            confidence = self._calculate_match_confidence(pdf_clean, eq)

            if confidence > best_confidence and confidence >= min_confidence:
                best_confidence = confidence
                best_match = EquationMapping(
                    page_num=page_num,
                    char_offset=char_offset,
                    pdf_text=pdf_text,
                    latex_source=eq,
                    confidence=confidence
                )

        if best_match:
            logger.debug(
                f"Mapped PDF text to LaTeX with {best_confidence:.2%} confidence: "
                f"{pdf_text[:50]}... -> {best_match.latex_source.latex[:50]}..."
            )

        return best_match

    def _calculate_match_confidence(
        self,
        pdf_text: str,
        equation: LatexEquation
    ) -> float:
        """
        Calculate confidence score for matching PDF text to LaTeX equation.

        Uses multiple strategies:
        1. Direct symbol matching (e.g., ∑ in PDF matches \\sum in LaTeX)
        2. Context matching (surrounding text)
        3. Structural similarity

        Args:
            pdf_text: Cleaned PDF text
            equation: LaTeX equation candidate

        Returns:
            Confidence score (0.0 to 1.0)
        """
        scores = []

        # Strategy 1: Symbol matching
        symbol_score = self._match_symbols(pdf_text, equation.latex)
        if symbol_score > 0:
            scores.append(symbol_score)

        # Strategy 2: Context matching
        context_score = self._match_context(pdf_text, equation)
        if context_score > 0:
            scores.append(context_score)

        # Strategy 3: Structural similarity
        struct_score = self._match_structure(pdf_text, equation.latex)
        if struct_score > 0:
            scores.append(struct_score)

        # Return weighted average
        if not scores:
            return 0.0

        # Give more weight to symbol and structure matching
        weights = [0.4, 0.3, 0.3][:len(scores)]
        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def _match_symbols(self, pdf_text: str, latex: str) -> float:
        """
        Match mathematical symbols between PDF text and LaTeX.

        Maps Unicode symbols to LaTeX commands:
        - ∑ -> \\sum
        - ∫ -> \\int
        - ∏ -> \\prod
        - √ -> \\sqrt
        - ∞ -> \\infty
        - etc.
        """
        # Symbol mapping: Unicode -> LaTeX commands
        symbol_map = {
            '∑': r'\sum',
            '∫': r'\int',
            '∏': r'\prod',
            '√': r'\sqrt',
            '∞': r'\infty',
            '∂': r'\partial',
            '∇': r'\nabla',
            'α': r'\alpha',
            'β': r'\beta',
            'γ': r'\gamma',
            'δ': r'\delta',
            'ε': r'\epsilon',
            'θ': r'\theta',
            'λ': r'\lambda',
            'μ': r'\mu',
            'π': r'\pi',
            'σ': r'\sigma',
            'τ': r'\tau',
            'φ': r'\phi',
            'ω': r'\omega',
            '≤': r'\leq',
            '≥': r'\geq',
            '≠': r'\neq',
            '≈': r'\approx',
            '∈': r'\in',
            '∉': r'\notin',
            '⊂': r'\subset',
            '⊆': r'\subseteq',
            '∪': r'\cup',
            '∩': r'\cap',
            '∀': r'\forall',
            '∃': r'\exists',
        }

        # Count matching symbols
        matches = 0
        total_symbols = 0

        for unicode_sym, latex_cmd in symbol_map.items():
            if unicode_sym in pdf_text:
                total_symbols += pdf_text.count(unicode_sym)
                if latex_cmd in latex:
                    matches += min(
                        pdf_text.count(unicode_sym),
                        latex.count(latex_cmd)
                    )

        if total_symbols == 0:
            return 0.0

        return matches / total_symbols

    def _match_context(self, pdf_text: str, equation: LatexEquation) -> float:
        """
        Match based on surrounding context.

        Uses context_before and context_after from equation to find matches.
        """
        # This is a simplified version - in production you'd compare with
        # actual surrounding text from PDF

        # For now, just check if any context keywords appear
        context = (equation.context_before + " " + equation.context_after).lower()
        pdf_lower = pdf_text.lower()

        # Look for common mathematical terms
        keywords = ['theorem', 'lemma', 'proof', 'equation', 'formula', 'where']
        matches = sum(1 for kw in keywords if kw in context and kw in pdf_lower)

        return min(matches / len(keywords), 1.0)

    def _match_structure(self, pdf_text: str, latex: str) -> float:
        """
        Match structural similarity (e.g., presence of sub/superscripts).

        Detects patterns like:
        - Subscripts: x_i in LaTeX vs x i (with newlines) in PDF
        - Superscripts: x^2 in LaTeX vs x 2 (with newlines) in PDF
        - Fractions: \frac{a}{b} in LaTeX vs a/b or stacked in PDF
        """
        # Count structural elements in LaTeX
        latex_has_subscript = '_' in latex or '_{' in latex
        latex_has_superscript = '^' in latex or '^{' in latex
        latex_has_fraction = r'\frac' in latex
        latex_has_sum = r'\sum' in latex
        latex_has_int = r'\int' in latex

        # Check PDF text for corresponding structures
        # (This is heuristic - PDF text may have broken formatting)
        pdf_has_numbers = bool(re.search(r'\d', pdf_text))
        pdf_has_letters = bool(re.search(r'[a-zA-Z]', pdf_text))

        score = 0.0
        total = 0

        if latex_has_subscript or latex_has_superscript:
            total += 1
            if pdf_has_numbers and pdf_has_letters:
                score += 0.5

        if latex_has_sum and '∑' in pdf_text:
            total += 1
            score += 1.0

        if latex_has_int and '∫' in pdf_text:
            total += 1
            score += 1.0

        if total == 0:
            return 0.0

        return score / total

    def _clean_text_for_matching(self, text: str) -> str:
        """
        Clean text for matching by removing whitespace and normalizing.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove newlines
        text = text.replace('\n', ' ')
        # Strip
        text = text.strip()
        return text

    def get_equation_by_latex(self, latex_fragment: str) -> Optional[LatexEquation]:
        """
        Find equation by LaTeX fragment.

        Args:
            latex_fragment: Fragment of LaTeX to search for

        Returns:
            Matching LatexEquation or None
        """
        for eq in self.equations:
            if latex_fragment in eq.latex or eq.latex in latex_fragment:
                return eq
        return None

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about extracted equations.

        Returns:
            Dictionary with statistics
        """
        if not self.equations:
            return {
                'total_equations': 0,
                'inline': 0,
                'display': 0,
                'environment': 0
            }

        stats = {
            'total_equations': len(self.equations),
            'inline': sum(1 for eq in self.equations if eq.equation_type == 'inline'),
            'display': sum(1 for eq in self.equations if eq.equation_type == 'display'),
            'environment': sum(1 for eq in self.equations if eq.equation_type == 'environment'),
        }

        return stats
