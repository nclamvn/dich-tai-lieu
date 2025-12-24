"""
Phase 3.5a - Translation Quality Engine (Rule-Based Polish)
VERSION: PHASE35A_STABLE (2025-11-18)

A defensive, rule-based quality polish layer that improves translated text
without changing meaning or touching semantic structures.

SCOPE (Phase 3.5a):
  - Rule-based only (NO LLM, NO API calls)
  - Normalize whitespace, punctuation
  - Fix common translation artifacts
  - Preserve ALL semantic structures (headings, theorems, formulas, etc.)
  - Default: OFF (must be explicitly enabled)

PHASE 3.5a.1 STABLE RELEASE (2025-11-18):
  - Added max_consecutive_newlines config control
  - Improved code block region detection (toggle-based state machine)
  - Fixed trailing whitespace handling (line-by-line .rstrip())
  - 43/43 tests passing (100% pass rate)

FUTURE (Phase 3.5b+):
  - LLM-based sentence rewriting (optional, with guardrails)
  - Glossary consistency enforcement
  - Cross-document consistency

Architecture:
  - Config-driven with clear on/off switches
  - Two-pass design (rule-based + LLM placeholder)
  - Non-destructive, idempotent operations
  - Domain-aware (book vs STEM)

Safety Philosophy:
  - Default mode: OFF
  - Only activate for specific pipelines (book/general, NOT STEM)
  - When in doubt, don't modify
  - All changes must be reversible/testable
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, List
import re


@dataclass
class TranslationQualityConfig:
    """
    Configuration for translation quality engine.

    Phase 3.5a: Rule-based polish only
    Phase 3.5b+: LLM rewrite (future)

    Attributes:
        mode: Quality processing mode
            - "off": No processing (DEFAULT)
            - "light": Conservative fixes only
            - "aggressive": More extensive polish (use with caution)

        domain: Content domain
            - "general": General text
            - "book": Book/novel translation
            - "stem": STEM/academic (NOT recommended for quality engine)

        enable_rule_based_pass: Enable rule-based normalization (Phase 3.5a)
        enable_llm_rewrite: Enable LLM rewriting (Phase 3.5b - not yet implemented)

        max_llm_cost_per_job: Cost ceiling for LLM operations (future)
        max_chars_per_pass: Maximum characters to process in one pass
    """
    # Core controls
    mode: Literal["off", "light", "aggressive"] = "off"  # DEFAULT OFF!
    domain: Literal["general", "book", "stem"] = "general"

    # Feature flags
    enable_rule_based_pass: bool = True  # Phase 3.5a
    enable_llm_rewrite: bool = False  # Phase 3.5b (not yet implemented)

    # Cost/resource limits
    max_llm_cost_per_job: float = 0.50  # For future LLM operations
    max_chars_per_pass: int = 200000  # Safety limit

    # Rule-based polish settings (Phase 3.5a)
    normalize_whitespace: bool = True
    normalize_punctuation: bool = True
    fix_spacing_around_punctuation: bool = True
    remove_redundant_phrases: bool = False  # Aggressive mode only

    # Phase 3.5a.1: Newline control
    max_consecutive_newlines: int = 2  # Max newlines to keep (1=single, 2=double)


@dataclass
class QualityReport:
    """
    Quality analysis report for translated text.

    Attributes:
        total_chars: Total characters analyzed
        issues_found: Number of issues detected
        issues_fixed: Number of issues fixed
        issue_breakdown: Dict of issue types and counts
        cost_usd: Cost of quality processing (for LLM operations)
    """
    total_chars: int
    issues_found: int
    issues_fixed: int
    issue_breakdown: Dict[str, int]
    cost_usd: float = 0.0


class TranslationQualityEngine:
    """
    Translation Quality Engine - Phase 3.5a (Rule-Based)

    Applies rule-based quality polish to translated text without changing meaning.

    Usage:
        config = TranslationQualityConfig(mode="light", domain="book")
        engine = TranslationQualityEngine(config)

        # Analyze text
        report = engine.analyze(text)

        # Polish text
        polished_text = engine.polish(text)

    Safety:
        - Default mode is "off" (no processing)
        - Only processes when explicitly enabled
        - Preserves semantic structures (headings, formulas, code, etc.)
        - Idempotent: running twice produces same result
    """

    def __init__(self, config: TranslationQualityConfig):
        """
        Initialize translation quality engine.

        Args:
            config: Quality engine configuration
        """
        self.config = config
        self._init_patterns()

    def _init_patterns(self):
        """Initialize regex patterns for quality checks."""
        # Patterns for detecting semantic structures that should NOT be modified
        self.protected_patterns = {
            'heading': re.compile(r'^(Chapter|Section|Part|Chương|Phần|Mục)\s+\d+', re.IGNORECASE),
            'theorem': re.compile(r'^(Theorem|Lemma|Corollary|Proof|Định lý|Bổ đề|Chứng minh):', re.IGNORECASE),
            'formula': re.compile(r'\$.*?\$|\\[(\[].*?\\[)\]]'),  # LaTeX math
            'code': re.compile(r'```|^```$|```.*?```', re.DOTALL | re.MULTILINE),  # Phase 3.5a.1: Improved code block detection
            'citation': re.compile(r'\[[\d,\s-]+\]'),
        }

        # Common translation artifacts to fix
        self.fix_patterns = {
            # Multiple spaces (2+) -> single space
            'multiple_spaces': (re.compile(r' {2,}'), ' '),

            # Space before punctuation (bad: "text ." -> good: "text.")
            'space_before_punct': (re.compile(r' +([.,!?;:])'), r'\1'),

            # No space after punctuation (bad: "text.Next" -> good: "text. Next")
            'no_space_after_punct': (re.compile(r'([.,!?;:])([A-ZĐ])'), r'\1 \2'),

            # Multiple newlines (3+) -> double newline
            'excessive_newlines': (re.compile(r'\n{3,}'), '\n\n'),

            # Trailing whitespace at end of lines
            'trailing_whitespace': (re.compile(r' +\n'), '\n'),

            # Leading whitespace at start of text
            'leading_whitespace': (re.compile(r'^\s+'), ''),

            # Trailing whitespace at end of text
            'ending_whitespace': (re.compile(r'\s+$'), ''),
        }

    def analyze(self, text: str) -> QualityReport:
        """
        Analyze text quality without modifying it.

        Args:
            text: Text to analyze

        Returns:
            QualityReport with analysis results
        """
        issues_found = {}

        # Check for common issues
        for issue_name, (pattern, _) in self.fix_patterns.items():
            matches = pattern.findall(text)
            if matches:
                issues_found[issue_name] = len(matches)

        total_issues = sum(issues_found.values())

        return QualityReport(
            total_chars=len(text),
            issues_found=total_issues,
            issues_fixed=0,  # Not fixing yet, just analyzing
            issue_breakdown=issues_found,
            cost_usd=0.0
        )

    def polish(self, text: str) -> str:
        """
        Apply quality polish to translated text.

        Phase 3.5a: Rule-based normalization only
        Phase 3.5b+: Optional LLM rewrite (future)

        Args:
            text: Translated text to polish

        Returns:
            Polished text (or original if mode="off")

        Safety:
            - Returns original text unchanged if mode="off"
            - Only applies safe, reversible transformations
            - Preserves semantic structures
        """
        # KILL SWITCH: If mode is "off", return original text unchanged
        if self.config.mode == "off":
            return text

        # Phase 3.5a: Rule-based polish
        if self.config.enable_rule_based_pass:
            text = self._apply_rule_based_polish(text)

        # Phase 3.5b: LLM rewrite (not yet implemented)
        if self.config.enable_llm_rewrite:
            # Placeholder for future LLM rewrite
            # text = self._apply_llm_rewrite(text)
            pass

        return text

    def _apply_rule_based_polish(self, text: str) -> str:
        """
        Apply rule-based polish transformations.

        Phase 3.5a: Conservative, deterministic fixes only
        Phase 3.5a.1: Added newline control, trailing whitespace fix, code block region detection

        Args:
            text: Text to polish

        Returns:
            Polished text
        """
        original_text = text

        # Phase 3.5a.1: Step 1 - Strip trailing whitespace from each line
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        text = '\n'.join(lines)

        # Split into paragraphs to preserve structure
        paragraphs = text.split('\n')
        polished_paragraphs = []

        # Phase 3.5a.1: Step 3 - Detect code block regions
        in_code_block = False

        for para in paragraphs:
            # Check for code block markers (opening or closing)
            if para.strip().startswith('```'):
                in_code_block = not in_code_block
                polished_paragraphs.append(para)  # Keep code block markers as-is
                continue

            # If we're inside a code block, preserve everything as-is
            if in_code_block:
                polished_paragraphs.append(para)
                continue

            # Skip empty paragraphs
            if not para.strip():
                polished_paragraphs.append(para)
                continue

            # Check if paragraph is protected (heading, theorem, etc.)
            if self._is_protected_content(para):
                polished_paragraphs.append(para)
                continue

            # Apply fixes to non-protected paragraphs
            polished_para = self._apply_fixes(para)
            polished_paragraphs.append(polished_para)

        # Rejoin paragraphs
        polished_text = '\n'.join(polished_paragraphs)

        # Phase 3.5a.1: Step 2 - Reduce excessive newlines (respect max_consecutive_newlines)
        if self.config.max_consecutive_newlines >= 1:
            # Build pattern dynamically based on config
            max_newlines = self.config.max_consecutive_newlines
            pattern = re.compile(r'\n{' + str(max_newlines + 1) + r',}')
            replacement = '\n' * max_newlines
            polished_text = pattern.sub(replacement, polished_text)

        return polished_text

    def _is_protected_content(self, text: str) -> bool:
        """
        Check if text contains protected content that should not be modified.

        Protected content:
            - Headings (Chapter, Section, etc.)
            - Theorems, lemmas, proofs
            - Mathematical formulas
            - Code blocks
            - Citations

        Args:
            text: Text to check

        Returns:
            True if text is protected, False otherwise
        """
        for pattern in self.protected_patterns.values():
            if pattern.search(text):
                return True
        return False

    def _apply_fixes(self, text: str) -> str:
        """
        Apply fix patterns to text.

        Args:
            text: Text to fix

        Returns:
            Fixed text
        """
        # Apply normalization fixes based on mode
        if self.config.normalize_whitespace:
            # Fix multiple spaces
            pattern, replacement = self.fix_patterns['multiple_spaces']
            text = pattern.sub(replacement, text)

            # Fix trailing whitespace
            pattern, replacement = self.fix_patterns['trailing_whitespace']
            text = pattern.sub(replacement, text)

        if self.config.fix_spacing_around_punctuation:
            # Fix space before punctuation
            pattern, replacement = self.fix_patterns['space_before_punct']
            text = pattern.sub(replacement, text)

            # Fix no space after punctuation
            pattern, replacement = self.fix_patterns['no_space_after_punct']
            text = pattern.sub(replacement, text)

        # Aggressive mode: additional fixes
        if self.config.mode == "aggressive" and self.config.remove_redundant_phrases:
            text = self._remove_redundant_phrases(text)

        return text

    def _remove_redundant_phrases(self, text: str) -> str:
        """
        Remove redundant phrases (aggressive mode only).

        CAUTION: This can change meaning, use only in "aggressive" mode.

        Args:
            text: Text to process

        Returns:
            Text with redundant phrases removed
        """
        # Example: Remove double negatives, redundant words, etc.
        # Phase 3.5a: NOT IMPLEMENTED (too risky)
        # Phase 3.5b+: Could use LLM for this
        return text

    def _apply_llm_rewrite(self, text: str) -> str:
        """
        Apply LLM-based sentence rewriting (Phase 3.5b - not yet implemented).

        FUTURE: This will use LLM to rewrite sentences for better flow
        while preserving meaning.

        Args:
            text: Text to rewrite

        Returns:
            Rewritten text
        """
        # Phase 3.5b: NOT YET IMPLEMENTED
        # This is a placeholder for future LLM integration

        # Planned approach:
        # 1. Split text into sentence chunks
        # 2. For each chunk:
        #    - Check if chunk needs rewriting (heuristic)
        #    - Send to LLM with strict prompt:
        #      "Preserve meaning, improve Vietnamese flow"
        #    - Apply sanity checks on LLM output
        #    - Use original if checks fail
        # 3. Reassemble chunks

        return text


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_default_config(domain: Literal["general", "book", "stem"] = "book") -> TranslationQualityConfig:
    """
    Create default configuration for translation quality engine.

    Args:
        domain: Content domain

    Returns:
        Default configuration (mode="off")
    """
    return TranslationQualityConfig(
        mode="off",  # DEFAULT: OFF
        domain=domain,
        enable_rule_based_pass=True,
        enable_llm_rewrite=False
    )


def create_light_config(domain: Literal["general", "book", "stem"] = "book") -> TranslationQualityConfig:
    """
    Create "light" mode configuration (conservative fixes only).

    Args:
        domain: Content domain

    Returns:
        Light mode configuration
    """
    return TranslationQualityConfig(
        mode="light",
        domain=domain,
        enable_rule_based_pass=True,
        enable_llm_rewrite=False,
        normalize_whitespace=True,
        normalize_punctuation=True,
        fix_spacing_around_punctuation=True,
        remove_redundant_phrases=False  # Too risky for light mode
    )


def create_aggressive_config(domain: Literal["general", "book", "stem"] = "book") -> TranslationQualityConfig:
    """
    Create "aggressive" mode configuration (more extensive polish).

    CAUTION: Use with care - may change sentence structure.

    Args:
        domain: Content domain

    Returns:
        Aggressive mode configuration
    """
    return TranslationQualityConfig(
        mode="aggressive",
        domain=domain,
        enable_rule_based_pass=True,
        enable_llm_rewrite=False,  # Phase 3.5b not yet implemented
        normalize_whitespace=True,
        normalize_punctuation=True,
        fix_spacing_around_punctuation=True,
        remove_redundant_phrases=False  # Phase 3.5b feature
    )
