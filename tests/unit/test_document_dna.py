"""Tests for core_v2/document_dna.py — DocumentDNA dataclass, detection, and extraction."""

import json
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock

from core_v2.document_dna import (
    DocumentDNA,
    extract_dna,
    quick_dna,
    detect_formula_notation,
    _detect_language_fallback,
)


# ==================== DocumentDNA Dataclass ====================


class TestDocumentDNADefaults:
    """DocumentDNA creation and default values."""

    def test_default_creation(self):
        dna = DocumentDNA()
        assert dna.document_id == ""
        assert dna.title == ""
        assert dna.genre == ""
        assert dna.has_chapters is False
        assert dna.has_formulas is False
        assert dna.formula_notation == "none"
        assert dna.characters == []
        assert dna.terminology == {}
        assert dna.word_count == 0

    def test_creation_with_values(self):
        dna = DocumentDNA(
            title="Test Book",
            genre="novel",
            tone="literary",
            has_chapters=True,
            characters=["Alice", "Bob"],
        )
        assert dna.title == "Test Book"
        assert dna.genre == "novel"
        assert dna.has_chapters is True
        assert dna.characters == ["Alice", "Bob"]

    def test_list_fields_are_independent(self):
        dna1 = DocumentDNA()
        dna2 = DocumentDNA()
        dna1.characters.append("Alice")
        assert dna2.characters == []

    def test_dict_fields_are_independent(self):
        dna1 = DocumentDNA()
        dna2 = DocumentDNA()
        dna1.terminology["hello"] = "xin chào"
        assert dna2.terminology == {}


class TestDocumentDNASerialization:
    """to_dict / to_json / from_dict / from_json round trips."""

    def test_to_dict(self):
        dna = DocumentDNA(title="Test", genre="novel")
        d = dna.to_dict()
        assert isinstance(d, dict)
        assert d["title"] == "Test"
        assert d["genre"] == "novel"

    def test_to_json(self):
        dna = DocumentDNA(title="Test")
        j = dna.to_json()
        parsed = json.loads(j)
        assert parsed["title"] == "Test"

    def test_from_dict(self):
        data = {"title": "From Dict", "genre": "essay", "word_count": 500}
        dna = DocumentDNA.from_dict(data)
        assert dna.title == "From Dict"
        assert dna.genre == "essay"
        assert dna.word_count == 500

    def test_from_dict_ignores_unknown_keys(self):
        data = {"title": "OK", "unknown_field": "ignored"}
        dna = DocumentDNA.from_dict(data)
        assert dna.title == "OK"
        assert not hasattr(dna, "unknown_field")

    def test_from_json(self):
        j = json.dumps({"title": "JSON Title", "tone": "formal"})
        dna = DocumentDNA.from_json(j)
        assert dna.title == "JSON Title"
        assert dna.tone == "formal"

    def test_round_trip(self):
        original = DocumentDNA(
            title="Round Trip",
            genre="academic_paper",
            has_formulas=True,
            characters=["Einstein"],
            terminology={"energy": "năng lượng"},
        )
        restored = DocumentDNA.from_json(original.to_json())
        assert restored.title == original.title
        assert restored.genre == original.genre
        assert restored.has_formulas == original.has_formulas
        assert restored.characters == original.characters
        assert restored.terminology == original.terminology


class TestToContextPrompt:
    """to_context_prompt() output."""

    def test_basic_prompt(self):
        dna = DocumentDNA(title="Test", genre="novel", tone="literary")
        prompt = dna.to_context_prompt()
        assert "Document: Test" in prompt
        assert "Genre: novel" in prompt
        assert "Tone: literary" in prompt

    def test_sub_genre_included(self):
        dna = DocumentDNA(genre="novel", sub_genre="thriller")
        prompt = dna.to_context_prompt()
        assert "novel (thriller)" in prompt

    def test_characters_included(self):
        dna = DocumentDNA(characters=["Alice", "Bob"])
        prompt = dna.to_context_prompt()
        assert "Characters: Alice, Bob" in prompt

    def test_terminology_included(self):
        dna = DocumentDNA(terminology={"hello": "xin chào"})
        prompt = dna.to_context_prompt()
        assert "hello → xin chào" in prompt

    def test_empty_fields_omitted(self):
        dna = DocumentDNA()
        prompt = dna.to_context_prompt()
        assert "Document:" not in prompt
        assert "Tone:" not in prompt


# ==================== detect_formula_notation ====================


class TestDetectFormulaNotation:
    """detect_formula_notation() classification."""

    def test_latex_inline_math(self):
        assert detect_formula_notation("The equation $E=mc^2$ is famous") == "latex"

    def test_latex_display_math(self):
        assert detect_formula_notation("$$\\sum_{i=1}^n x_i$$") == "latex"

    def test_latex_begin_equation(self):
        assert detect_formula_notation("\\begin{equation} x^2 \\end{equation}") == "latex"

    def test_latex_frac(self):
        assert detect_formula_notation("\\frac{a}{b}") == "latex"

    def test_latex_greek_letters(self):
        assert detect_formula_notation("\\alpha + \\beta = \\gamma") == "latex"

    def test_unicode_math(self):
        assert detect_formula_notation("The sum ∑ of all elements") == "unicode"

    def test_unicode_integral(self):
        assert detect_formula_notation("∫ f(x) dx") == "unicode"

    def test_plain_equation(self):
        assert detect_formula_notation("y = 2x + 3") == "plain"

    def test_no_math(self):
        assert detect_formula_notation("This is a normal paragraph without math.") == "none"


# ==================== _detect_language_fallback ====================


class TestDetectLanguageFallback:
    """Fallback language detection from character sets."""

    def test_english_text(self):
        text = "This is a normal English paragraph with enough words to meet the threshold."
        assert _detect_language_fallback(text) == "en"

    def test_vietnamese_text(self):
        text = "Đây là một đoạn văn tiếng Việt với đủ các ký tự đặc biệt " * 5
        assert _detect_language_fallback(text) == "vi"

    def test_korean_text(self):
        text = "한국어 텍스트입니다 이것은 테스트를 위한 충분한 텍스트입니다 " * 5
        assert _detect_language_fallback(text) == "ko"

    def test_short_text_defaults_to_english(self):
        assert _detect_language_fallback("Hello") == "en"

    def test_empty_text(self):
        assert _detect_language_fallback("") == "en"


# ==================== quick_dna ====================


class TestQuickDNA:
    """quick_dna() heuristic extraction."""

    def test_basic_text(self):
        dna = quick_dna("This is a simple paragraph of text for testing purposes.")
        assert dna.document_id != ""
        assert dna.word_count > 0
        assert dna.genre == "essay"  # default

    def test_detects_latex_formulas(self):
        dna = quick_dna("We have $E=mc^2$ and $$\\sum x$$")
        assert dna.has_formulas is True
        assert dna.formula_notation == "latex"
        assert dna.genre == "academic_paper"

    def test_detects_code(self):
        dna = quick_dna("Here is some code:\n```python\ndef hello():\n    pass\n```")
        assert dna.has_code is True
        assert dna.genre == "technical_doc"

    def test_detects_chapters(self):
        dna = quick_dna("chapter 1: Introduction\n\nSome text here.")
        assert dna.has_chapters is True
        assert dna.genre == "novel"

    def test_detects_citations(self):
        dna = quick_dna("According to research [1], the results show [2] improvements.")
        assert dna.has_citations is True
        assert dna.genre == "academic_paper"

    def test_empty_text(self):
        dna = quick_dna("")
        assert dna.word_count == 0
        assert dna.genre == "essay"

    def test_document_id_is_deterministic(self):
        text = "Same content for determinism test."
        dna1 = quick_dna(text)
        dna2 = quick_dna(text)
        assert dna1.document_id == dna2.document_id


# ==================== extract_dna (async with LLM) ====================


class TestExtractDNA:
    """extract_dna() with mocked LLM client."""

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "title": "Test Paper",
            "language": "en",
            "genre": "academic_paper",
            "tone": "formal",
            "has_formulas": True,
        })
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        text = "A" * 100
        dna = await extract_dna(text, mock_client)
        assert dna.title == "Test Paper"
        assert dna.genre == "academic_paper"
        assert dna.word_count > 0
        assert dna.document_id != ""

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self):
        mock_client = AsyncMock()
        mock_client.chat.side_effect = RuntimeError("API down")

        text = "Some English text for fallback detection."
        dna = await extract_dna(text, mock_client)
        assert dna.genre == "other"
        assert dna.language == "en"
        assert dna.document_id != ""

    @pytest.mark.asyncio
    async def test_unknown_language_triggers_fallback(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "title": "Test",
            "language": "unknown",
            "genre": "essay",
        })
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        dna = await extract_dna("Hello world " * 20, mock_client)
        assert dna.language == "en"

    @pytest.mark.asyncio
    async def test_long_text_is_sampled(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({"title": "Long", "language": "en", "genre": "novel"})
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        long_text = "word " * 10000
        dna = await extract_dna(long_text, mock_client, sample_size=3000)
        # Verify LLM was called with a trimmed sample
        call_args = mock_client.chat.call_args
        prompt_text = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0][0]["content"]
        assert len(prompt_text) < len(long_text)
