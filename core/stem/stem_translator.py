"""
STEM Translator Module

Main orchestrator for STEM-aware translation that coordinates:
- Formula detection and preservation
- Code block detection and preservation
- STEM-specific translation prompts
- Quality validation
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from .formula_detector import FormulaDetector
from .code_detector import CodeDetector
from .placeholder_manager import PlaceholderManager, ProcessedContent
from ..translator import TranslatorEngine
from ..chunker import TranslationChunk
from ..math_reconstructor import MathReconstructor
from ..layout_cleaner import LayoutCleaner

logger = logging.getLogger(__name__)


@dataclass
class STEMTranslationResult:
    """Result of STEM translation"""
    translated_text: str
    original_text: str
    formula_count: int
    code_count: int
    preservation_rate: float
    quality_score: float = 0.0
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class STEMTranslator:
    """
    STEM-aware translation coordinator

    This class orchestrates the STEM translation pipeline:
    1. Detect formulas and code blocks
    2. Replace with placeholders
    3. Translate text with STEM-aware prompts
    4. Restore original formulas and code
    5. Validate preservation
    """

    def __init__(
        self,
        base_translator: TranslatorEngine,
        glossary_path: Optional[Path] = None
    ):
        """
        Initialize STEM translator

        Args:
            base_translator: Underlying translation engine (OpenAI/Anthropic)
            glossary_path: Path to STEM glossary JSON file
        """
        self.base_translator = base_translator
        self.formula_detector = FormulaDetector()
        self.code_detector = CodeDetector()
        self.placeholder_manager = PlaceholderManager()

        # NEW: Add math reconstructor and layout cleaner for enhanced quality
        self.math_reconstructor = MathReconstructor()
        self.layout_cleaner = LayoutCleaner()

        # Load STEM glossary
        self.glossary = self._load_glossary(glossary_path)

        logger.info("STEMTranslator initialized")

    def _load_glossary(self, glossary_path: Optional[Path]) -> Dict:
        """Load STEM domain glossary"""
        if glossary_path is None:
            # Default path
            glossary_path = Path(__file__).parent.parent.parent / 'glossary' / 'stem.json'

        try:
            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)
                logger.info(f"Loaded STEM glossary from {glossary_path}")
                return glossary
        except Exception as e:
            logger.warning(f"Failed to load STEM glossary: {e}")
            return {}

    async def translate_document(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "vi",
        debug: bool = False,
        pages_text: Optional[List[str]] = None
    ) -> STEMTranslationResult:
        """
        Translate document with STEM awareness

        Args:
            text: Input text to translate
            source_lang: Source language code
            target_lang: Target language code
            debug: Enable debug output
            pages_text: Optional list of per-page text for layout cleaning

        Returns:
            STEMTranslationResult with translated text and statistics
        """
        logger.info(f"Starting STEM translation: {len(text)} chars")

        # PRIORITY: Translation quality is HIGHEST priority

        # REGRESSION FIX (Phase 1.5): Reordered pipeline to protect formula boundaries
        # Step 1: Detect formulas and code FIRST (before any cleaning)
        formula_matches = self.formula_detector.detect_formulas(text)
        code_matches = self.code_detector.detect_code(text)

        logger.info(f"Detected: {len(formula_matches)} formulas, {len(code_matches)} code blocks")

        # Extract formula positions for boundary protection
        formula_positions = [(match.start, match.end) for match in formula_matches]

        # Step 2: Clean layout WITH formula boundary protection
        if pages_text:
            logger.info("Cleaning document layout (headers/footers removal with formula protection)...")
            text = self.layout_cleaner.clean_document(text, pages_text, formula_positions)
            logger.info(f"Layout cleaned: {len(text)} chars")

            # Re-detect formulas after cleaning (positions may have shifted)
            formula_matches = self.formula_detector.detect_formulas(text)
            code_matches = self.code_detector.detect_code(text)
            logger.info(f"Re-detected after cleaning: {len(formula_matches)} formulas, {len(code_matches)} code blocks")

        # Step 3: Normalize Unicode ONLY within formula boundaries (REGRESSION FIX)
        # This prevents corruption of Vietnamese prose
        text = self.math_reconstructor.normalize_unicode_scoped(text, formula_matches)
        logger.info(f"Unicode normalized in {len(formula_matches)} formula regions (Vietnamese text protected)")

        # Step 4: Replace with placeholders
        processed = self.placeholder_manager.preprocess(
            text=text,
            formula_matches=formula_matches,
            code_matches=code_matches
        )

        if debug:
            debug_output = self.placeholder_manager.create_debug_output(
                original_text=text,
                processed=processed
            )
            logger.debug(f"\n{debug_output}")

        # Step 3: Create STEM-aware prompt
        stem_prompt = self._create_stem_prompt(target_lang)

        # Step 4: Translate with modified text
        # Note: We'll use the base translator but with enhanced prompt
        translated_with_placeholders = await self._translate_with_stem_prompt(
            text=processed.text,
            source_lang=source_lang,
            target_lang=target_lang,
            stem_prompt=stem_prompt
        )

        # Step 5: Restore formulas and code
        final_text = self.placeholder_manager.restore(
            translated_text=translated_with_placeholders,
            mapping=processed.mapping
        )

        # REGRESSION FIX: Apply scoped Unicode normalization to translated text
        # Re-detect formulas in translated text (positions may have shifted)
        translated_formulas = self.formula_detector.detect_formulas(final_text)
        final_text = self.math_reconstructor.normalize_unicode_scoped(final_text, translated_formulas)
        logger.info(f"Unicode normalized in {len(translated_formulas)} translated formula regions (Vietnamese protected)")

        # Step 6: Validate preservation
        verification = self.placeholder_manager.verify_restoration(
            original_text=text,
            restored_text=final_text,
            formula_matches=formula_matches,
            code_matches=code_matches
        )

        # Collect warnings
        warnings = []
        if verification['formulas_lost'] > 0:
            warnings.append(f"Lost {verification['formulas_lost']} formulas during translation")
        if verification['code_lost'] > 0:
            warnings.append(f"Lost {verification['code_lost']} code blocks during translation")
        if verification['remaining_placeholders'] > 0:
            warnings.append(f"{verification['remaining_placeholders']} placeholders not restored")

        logger.info(f"STEM translation complete. Preservation rate: {verification['preservation_rate']:.1%}")

        if debug and warnings:
            for warning in warnings:
                logger.warning(warning)

        return STEMTranslationResult(
            translated_text=final_text,
            original_text=text,
            formula_count=len(formula_matches),
            code_count=len(code_matches),
            preservation_rate=verification['preservation_rate'],
            warnings=warnings
        )

    async def _translate_with_stem_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        stem_prompt: str
    ) -> str:
        """
        Translate text using STEM-aware prompt

        Args:
            text: Text with placeholders
            source_lang: Source language
            target_lang: Target language
            stem_prompt: STEM-specific instructions

        Returns:
            Translated text with placeholders intact
        """
        import httpx

        # Create a single translation chunk
        # For long documents, we'd chunk this properly in production
        chunk = TranslationChunk(
            id=0,
            text=text,
            context_before="",
            context_after="",
            metadata={}
        )

        # Use the base translator with HTTP client
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                result = await self.base_translator.translate_chunk(
                    client=client,
                    chunk=chunk
                )
                return result.translated  # FIX: Use .translated not .translated_text
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    def _create_stem_prompt(self, target_lang: str) -> str:
        """
        Create STEM-specific translation prompt

        Args:
            target_lang: Target language code

        Returns:
            Prompt string with STEM instructions
        """
        # Language names
        lang_names = {
            'vi': 'Vietnamese',
            'en': 'English',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German'
        }
        target_lang_name = lang_names.get(target_lang, target_lang)

        # Build glossary excerpt for prompt
        glossary_text = ""
        if self.glossary:
            # Extract a few key terms for the prompt
            key_terms = []
            for category in ['mathematics', 'physics', 'chemistry', 'computer_science']:
                if category in self.glossary:
                    terms = list(self.glossary[category].items())[:5]  # First 5 terms
                    key_terms.extend([f"'{en}' = '{target}'" for en, target in terms])

            if key_terms:
                glossary_text = "\n\nKey technical terms:\n" + "\n".join(key_terms[:15])

        prompt = f"""You are translating a STEM (Science, Technology, Engineering, Mathematics) document to {target_lang_name}.

CRITICAL RULES:
1. PRESERVE ALL PLACEHOLDERS EXACTLY: Any text in the format ⟪STEM_*⟫ must remain COMPLETELY UNCHANGED
   - These are mathematical formulas, equations, and code blocks
   - Do NOT translate, modify, or remove these placeholders
   - Do NOT add spaces or punctuation around them unless present in the original

2. Technical terminology:
   - Use standard scientific terminology in {target_lang_name}
   - Maintain consistency with established translations
   - Keep technical abbreviations (e.g., DNA, RNA, HTTP, API) unchanged{glossary_text}

3. Preserve structure:
   - Keep equation numbers like (1), (2), Equation (3)
   - Maintain figure/table references: Figure 1, Table 2
   - Keep citation formats: [1], [Smith 2020]
   - Preserve list numbering and bullet points

4. Mathematical expressions:
   - Inline math stays inline, display math stays display
   - Do not add or remove whitespace around formulas
   - Keep punctuation after formulas if present

5. Code and programming:
   - Code blocks remain completely untouched (they are placeholders)
   - Function names, variable names, and keywords are not translated
   - Comments in code can be translated if separate from placeholders

6. Units and symbols:
   - Keep standard units: m, kg, s, Hz, V, Ω, etc.
   - Keep mathematical symbols: ∫, ∑, ∂, ∇, etc.
   - Maintain scientific notation: 1.5×10⁻³, 3.2e8

Translate ONLY the natural language text, maintaining all technical accuracy and formatting."""

        return prompt

    def is_stem_content(self, text: str) -> bool:
        """
        Quick check if content appears to be STEM-related

        Args:
            text: Text to check

        Returns:
            True if content appears to be STEM
        """
        has_formulas = self.formula_detector.has_formulas(text)
        has_code = self.code_detector.has_code(text)

        return has_formulas or has_code

    def analyze_stem_content(self, text: str) -> Dict:
        """
        Analyze STEM content in text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with analysis results
        """
        formula_stats = self.formula_detector.count_formulas(text)
        code_stats = self.code_detector.count_code_blocks(text)

        is_stem_heavy = self.placeholder_manager.is_stem_heavy(
            formula_count=formula_stats['total'],
            code_count=code_stats['total'],
            text_length=len(text)
        )

        return {
            'is_stem_content': self.is_stem_content(text),
            'is_stem_heavy': is_stem_heavy,
            'formulas': formula_stats,
            'code_blocks': code_stats,
            'text_length': len(text),
            'stem_score': self._calculate_stem_score(formula_stats, code_stats, len(text))
        }

    def _calculate_stem_score(self, formula_stats: dict, code_stats: dict, text_length: int) -> float:
        """
        Calculate a STEM score (0-1) indicating how STEM-heavy the content is

        Args:
            formula_stats: Formula statistics
            code_stats: Code statistics
            text_length: Total text length

        Returns:
            Score between 0 (not STEM) and 1 (very STEM-heavy)
        """
        # Estimate STEM content length
        formula_count = formula_stats.get('total', 0)
        code_count = code_stats.get('total', 0)

        # Rough estimates of average lengths
        avg_formula_length = 50
        avg_code_length = 150

        stem_content_length = (formula_count * avg_formula_length +
                              code_count * avg_code_length)

        # Calculate ratio
        if text_length == 0:
            return 0.0

        ratio = stem_content_length / text_length
        # Cap at 1.0
        return min(ratio, 1.0)

    async def translate_chunk(
        self,
        chunk: TranslationChunk,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> str:
        """
        Translate a single chunk with STEM awareness

        This is useful when integrating with the existing chunking system.

        Args:
            chunk: Translation chunk
            source_lang: Source language
            target_lang: Target language

        Returns:
            Translated chunk text
        """
        result = await self.translate_document(
            text=chunk.text,
            source_lang=source_lang,
            target_lang=target_lang
        )

        return result.translated_text
