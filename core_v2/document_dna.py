"""
Document DNA - Claude-Extracted Document Metadata

Instead of regex-based extraction, we let Claude analyze the document
and extract its "DNA" - the essential characteristics needed for translation.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class DocumentDNA:
    """
    The DNA of a document - extracted by Claude, not regex.

    This captures everything Claude needs to know to translate consistently.
    """

    # Basic info
    document_id: str = ""
    title: str = ""
    author: str = ""
    language: str = ""

    # Genre detection
    genre: str = ""  # novel, academic, business, etc.
    sub_genre: str = ""  # thriller, romance, technical, etc.

    # Style analysis
    tone: str = ""  # formal, casual, literary, technical
    voice: str = ""  # first-person, third-person, etc.
    reading_level: str = ""  # elementary, high-school, academic, expert

    # Structure
    has_chapters: bool = False
    has_sections: bool = False
    has_footnotes: bool = False
    has_citations: bool = False
    has_formulas: bool = False
    has_code: bool = False
    has_tables: bool = False
    has_images: bool = False

    # Formula notation type (NEW for FIX-002)
    formula_notation: str = "none"  # "latex", "unicode", "plain", "none"

    # Key entities (extracted by Claude)
    characters: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    key_terms: List[str] = field(default_factory=list)
    proper_nouns: List[str] = field(default_factory=list)

    # Consistency requirements
    terminology: Dict[str, str] = field(default_factory=dict)  # term -> translation
    style_notes: List[str] = field(default_factory=list)

    # Statistics
    word_count: int = 0
    chunk_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentDNA":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, json_str: str) -> "DocumentDNA":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_context_prompt(self) -> str:
        """Generate context section for translation prompts."""
        parts = [
            f"Document: {self.title}" if self.title else "",
            f"Author: {self.author}" if self.author else "",
            f"Genre: {self.genre}" + (f" ({self.sub_genre})" if self.sub_genre else ""),
            f"Tone: {self.tone}" if self.tone else "",
            f"Voice: {self.voice}" if self.voice else "",
        ]

        if self.characters:
            parts.append(f"Characters: {', '.join(self.characters[:10])}")

        if self.key_terms:
            parts.append(f"Key Terms: {', '.join(self.key_terms[:10])}")

        if self.terminology:
            term_list = [f"{k} → {v}" for k, v in list(self.terminology.items())[:10]]
            parts.append(f"Terminology:\n  " + "\n  ".join(term_list))

        if self.style_notes:
            parts.append(f"Style Notes:\n  - " + "\n  - ".join(self.style_notes[:5]))

        return "\n".join(p for p in parts if p)


# ==================== DNA EXTRACTION ====================

DNA_EXTRACTION_PROMPT = """Analyze this document and extract its DNA - the essential characteristics needed for consistent translation.

Document Sample:
{sample_text}

Respond in JSON format:
{{
    "title": "detected title or empty",
    "author": "detected author or empty",
    "language": "source language code (en, zh, ja, etc.)",
    "genre": "novel|poetry|essay|business_report|white_paper|academic_paper|arxiv_paper|thesis|textbook|technical_doc|api_doc|user_manual|other",
    "sub_genre": "more specific genre if applicable",
    "tone": "formal|casual|literary|technical|academic|conversational",
    "voice": "first-person|second-person|third-person|mixed",
    "reading_level": "elementary|middle-school|high-school|undergraduate|graduate|expert",
    "has_chapters": true/false,
    "has_sections": true/false,
    "has_footnotes": true/false,
    "has_citations": true/false,
    "has_formulas": true/false,
    "has_code": true/false,
    "has_tables": true/false,
    "characters": ["list of character names if fiction"],
    "locations": ["list of important locations"],
    "key_terms": ["domain-specific terms that need consistent translation"],
    "proper_nouns": ["names, places, organizations to preserve"],
    "style_notes": ["any special style observations"]
}}
"""


async def extract_dna(
    text: str,
    llm_client: Any,
    sample_size: int = 5000
) -> DocumentDNA:
    """
    Extract document DNA using Claude.

    Args:
        text: Full document text
        llm_client: LLM client with async chat method
        sample_size: Characters to sample for analysis

    Returns:
        DocumentDNA with extracted characteristics
    """
    # Get representative sample (beginning, middle, end)
    if len(text) <= sample_size:
        sample = text
    else:
        third = sample_size // 3
        sample = (
            text[:third] +
            "\n\n[...]\n\n" +
            text[len(text)//2 - third//2 : len(text)//2 + third//2] +
            "\n\n[...]\n\n" +
            text[-third:]
        )

    # Create prompt
    prompt = DNA_EXTRACTION_PROMPT.format(sample_text=sample)

    # Call Claude
    try:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # Parse response
        data = json.loads(response.content)
        dna = DocumentDNA.from_dict(data)

        # Add statistics
        dna.word_count = len(text.split())
        dna.document_id = hashlib.md5(text[:1000].encode()).hexdigest()[:12]

        return dna

    except Exception as e:
        # Return basic DNA on error
        return DocumentDNA(
            document_id=hashlib.md5(text[:1000].encode()).hexdigest()[:12],
            word_count=len(text.split()),
            language="unknown",
            genre="other"
        )


def detect_formula_notation(content: str) -> str:
    """
    Detect what kind of math notation is used in the document.

    Returns:
        "latex" - LaTeX notation ($...$, \\sum, \\frac, etc.)
        "unicode" - Unicode math symbols (∑, ∫, ∂, etc.)
        "plain" - Plain text equations (a = b + c)
        "none" - No math detected
    """
    import re

    # LaTeX patterns - check first as most specific
    latex_patterns = [
        r'\$[^$]+\$',           # Inline math $...$
        r'\$\$[^$]+\$\$',       # Display math $$...$$
        r'\\begin\{equation\}',  # Equation environment
        r'\\begin\{align\}',     # Align environment
        r'\\frac\{',             # Fractions
        r'\\sum[_^]',            # Summation with sub/super
        r'\\int[_^]',            # Integration with sub/super
        r'\\mathbb\{',           # Blackboard bold
        r'\\mathcal\{',          # Calligraphic
        r'\\nabla',              # Gradient
        r'\\partial',            # Partial derivative
        r'\\alpha|\\beta|\\gamma|\\delta|\\epsilon',  # Greek letters
    ]

    for pattern in latex_patterns:
        if re.search(pattern, content):
            return "latex"

    # Unicode math patterns
    unicode_math = ['∑', '∫', '∂', '∇', '∈', '∀', '∃', '√', 'ℝ', 'ℕ', 'ℤ', 'ℂ',
                    '∞', '≤', '≥', '≠', '≈', '∝', '⊂', '⊃', '∪', '∩', '×', '÷']
    if any(char in content for char in unicode_math):
        return "unicode"

    # Plain math patterns (basic equations)
    if re.search(r'[a-z]\s*=\s*[a-z0-9+\-*/()]+', content, re.I):
        return "plain"

    return "none"


def quick_dna(text: str) -> DocumentDNA:
    """
    Quick DNA extraction without LLM (for testing or fallback).

    Uses simple heuristics instead of Claude.
    """
    dna = DocumentDNA()
    dna.document_id = hashlib.md5(text[:1000].encode()).hexdigest()[:12]
    dna.word_count = len(text.split())

    # Simple detection
    text_lower = text.lower()

    # Detect formula notation (NEW for FIX-002)
    dna.formula_notation = detect_formula_notation(text)

    # Detect formulas - use notation detection
    if dna.formula_notation in ("latex", "unicode"):
        dna.has_formulas = True
        dna.genre = "academic_paper"
    elif "$$" in text or "\\begin{equation}" in text or "\\frac" in text:
        dna.has_formulas = True
        dna.formula_notation = "latex"
        dna.genre = "academic_paper"

    # Detect code
    if "```" in text or "def " in text or "function " in text:
        dna.has_code = True
        if not dna.genre:
            dna.genre = "technical_doc"

    # Detect chapters
    if "chapter " in text_lower or "chương " in text_lower:
        dna.has_chapters = True
        if not dna.genre:
            dna.genre = "novel"

    # Detect citations
    if "[" in text and "]" in text:
        import re
        if re.search(r'\[\d+\]', text) or re.search(r'\[.*\d{4}\]', text):
            dna.has_citations = True
            if not dna.genre:
                dna.genre = "academic_paper"

    # Default
    if not dna.genre:
        dna.genre = "essay"

    return dna
