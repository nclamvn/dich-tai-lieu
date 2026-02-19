"""
Unit tests for api/services/file_handler.py — target 90%+ coverage.
"""
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from api.services.file_handler import (
    resolve_output_path,
    validate_project_path,
    safe_filename,
    generate_docx_preview,
    generate_text_preview,
    PROJECT_ROOT,
)


# ---------------------------------------------------------------------------
# resolve_output_path
# ---------------------------------------------------------------------------

class TestResolveOutputPath:
    def test_absolute_path_unchanged(self, tmp_path):
        p = tmp_path / "output.docx"
        result = resolve_output_path(str(p))
        assert result == p.resolve()

    def test_relative_path_resolved_from_project_root(self):
        result = resolve_output_path("outputs/test.docx")
        assert result == (PROJECT_ROOT / "outputs" / "test.docx").resolve()

    def test_returns_path_object(self):
        result = resolve_output_path("/tmp/x.txt")
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# validate_project_path
# ---------------------------------------------------------------------------

class TestValidateProjectPath:
    def test_relative_inside_project(self):
        result = validate_project_path("uploads/file.pdf")
        assert str(result).startswith(str(PROJECT_ROOT))

    def test_absolute_inside_project(self):
        inside = PROJECT_ROOT / "uploads" / "safe.pdf"
        result = validate_project_path(str(inside))
        assert result == inside.resolve()

    def test_traversal_rejected(self):
        with pytest.raises(ValueError, match="outside project"):
            validate_project_path("../../../etc/passwd")

    def test_absolute_outside_rejected(self):
        with pytest.raises(ValueError, match="outside project"):
            validate_project_path("/etc/passwd")

    def test_sneaky_traversal(self):
        with pytest.raises(ValueError, match="outside project"):
            validate_project_path("uploads/../../../../../../etc/shadow")


# ---------------------------------------------------------------------------
# safe_filename
# ---------------------------------------------------------------------------

class TestSafeFilename:
    def test_normal_filename(self):
        result = safe_filename("j1", "report", "docx")
        assert result == "report.docx"

    def test_special_characters_stripped(self):
        result = safe_filename("j1", 'my<doc>:file"name', "pdf")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert result.endswith(".pdf")

    def test_unicode_preserved(self):
        result = safe_filename("j1", "báo_cáo_dịch", "docx")
        assert "báo" in result
        assert result.endswith(".docx")

    def test_japanese_preserved(self):
        result = safe_filename("j1", "翻訳レポート", "txt")
        assert "翻訳" in result

    def test_empty_name_uses_job_id(self):
        result = safe_filename("abc123", "", "docx")
        assert result == "abc123.docx"

    def test_only_special_chars_uses_job_id(self):
        result = safe_filename("j1", ':::"""', "pdf")
        assert result == "j1.pdf"

    def test_multiple_underscores_collapsed(self):
        result = safe_filename("j1", "a:::b", "txt")
        assert "__" not in result

    def test_null_bytes_stripped(self):
        result = safe_filename("j1", "file\x00name", "txt")
        assert "\x00" not in result


# ---------------------------------------------------------------------------
# generate_docx_preview
# ---------------------------------------------------------------------------

class TestGenerateDocxPreview:
    def _mock_doc(self, texts):
        """Create a mock docx Document with given paragraph texts."""
        doc = MagicMock()
        paras = []
        for t in texts:
            p = MagicMock()
            p.text = t
            paras.append(p)
        doc.paragraphs = paras
        return doc

    def _mock_detector(self, heading_map=None):
        """Create a mock HeadingDetector. heading_map: {text: level}."""
        detector = MagicMock()
        mapping = heading_map or {}
        detector.detect_heading_level.side_effect = lambda t: mapping.get(t)
        return detector

    def test_simple_paragraphs(self):
        doc = self._mock_doc(["Hello world", "Second paragraph"])
        det = self._mock_detector()
        result = generate_docx_preview(doc, det, limit=2000)

        assert result["is_structured"] is True
        assert len(result["preview"]) == 2
        assert result["preview"][0]["type"] == "paragraph"
        assert result["total_words"] == 4
        assert result["is_truncated"] is False

    def test_heading_detected(self):
        doc = self._mock_doc(["Chapter 1", "Content here"])
        det = self._mock_detector({"Chapter 1": 1})
        result = generate_docx_preview(doc, det, limit=2000)

        assert result["preview"][0]["type"] == "heading1"
        assert result["preview"][0]["level"] == 1
        assert result["preview"][1]["type"] == "paragraph"

    def test_truncation_at_limit(self):
        doc = self._mock_doc(["word " * 10, "extra " * 10])
        det = self._mock_detector()
        result = generate_docx_preview(doc, det, limit=10)

        assert result["is_truncated"] is True
        assert result["preview_words"] == 10

    def test_truncation_partial_paragraph(self):
        doc = self._mock_doc(["word " * 5, "extra " * 20])
        det = self._mock_detector()
        result = generate_docx_preview(doc, det, limit=10)

        assert result["is_truncated"] is True
        # First paragraph fits (5 words), second is truncated
        assert len(result["preview"]) == 2
        assert result["preview"][1]["text"].endswith("...")

    def test_truncation_exact_limit_no_room(self):
        doc = self._mock_doc(["word " * 10, "extra " * 20])
        det = self._mock_detector()
        # limit=10 → first paragraph exactly fills it, second triggers truncation
        # with word_count == limit, so no partial paragraph added
        result = generate_docx_preview(doc, det, limit=10)
        assert result["is_truncated"] is True

    def test_empty_paragraphs_skipped(self):
        doc = self._mock_doc(["Hello", "", "  ", "World"])
        det = self._mock_detector()
        result = generate_docx_preview(doc, det, limit=2000)

        assert len(result["preview"]) == 2
        texts = [e["text"] for e in result["preview"]]
        assert "Hello" in texts
        assert "World" in texts

    def test_empty_document(self):
        doc = self._mock_doc([])
        det = self._mock_detector()
        result = generate_docx_preview(doc, det, limit=2000)

        assert result["preview"] == []
        assert result["total_words"] == 0
        assert result["is_truncated"] is False


# ---------------------------------------------------------------------------
# generate_text_preview
# ---------------------------------------------------------------------------

class TestGenerateTextPreview:
    def test_short_text(self):
        result = generate_text_preview("Hello world foo bar")
        assert result["total_words"] == 4
        assert result["preview_words"] == 4
        assert result["is_truncated"] is False
        assert result["is_structured"] is False

    def test_truncation(self):
        text = " ".join(f"w{i}" for i in range(100))
        result = generate_text_preview(text, limit=10)
        assert result["preview_words"] == 10
        assert result["total_words"] == 100
        assert result["is_truncated"] is True

    def test_empty_text(self):
        result = generate_text_preview("")
        assert result["total_words"] == 0
        assert result["is_truncated"] is False

    def test_exact_limit(self):
        text = "a b c d e"
        result = generate_text_preview(text, limit=5)
        assert result["is_truncated"] is False
        assert result["preview_words"] == 5
