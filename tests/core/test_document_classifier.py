"""Tests for core.document_classifier — DocumentClassifier."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.document_classifier import DocumentClassifier


class TestDocumentClassifierFilenames:
    """Test classification by filename patterns (no PDF content needed)."""

    def test_arxiv_pattern_with_dash(self):
        result = DocumentClassifier.classify(
            "arxiv-1509.05363.pdf", check_content=False
        )
        assert result["document_type"] in ("arxiv", "stem")

    def test_arxiv_pattern_with_underscore(self):
        result = DocumentClassifier.classify(
            "arxiv_2301.12345.pdf", check_content=False
        )
        assert result["document_type"] in ("arxiv", "stem")

    def test_bare_arxiv_id(self):
        result = DocumentClassifier.classify(
            "2301.12345.pdf", check_content=False
        )
        assert result["document_type"] in ("arxiv", "stem", "general")

    def test_latex_source_tex(self):
        result = DocumentClassifier.classify(
            "paper.tex", check_content=False
        )
        assert result["document_type"] in ("arxiv", "stem")

    def test_latex_source_tar_gz(self):
        result = DocumentClassifier.classify(
            "paper.tar.gz", check_content=False
        )
        assert result["document_type"] in ("arxiv", "stem")

    def test_general_document(self):
        result = DocumentClassifier.classify(
            "meeting-notes.pdf", check_content=False
        )
        assert result["document_type"] == "general"

    def test_general_txt_file(self):
        result = DocumentClassifier.classify(
            "readme.txt", check_content=False
        )
        assert result["document_type"] == "general"


class TestDocumentClassifierOutput:
    """Test classification output structure."""

    def test_result_has_required_keys(self):
        result = DocumentClassifier.classify(
            "document.pdf", check_content=False
        )
        assert "document_type" in result
        assert "confidence" in result
        assert "recommended_settings" in result
        assert "reasons" in result

    def test_confidence_in_range(self):
        result = DocumentClassifier.classify(
            "document.pdf", check_content=False
        )
        assert 0.0 <= result["confidence"] <= 1.0

    def test_reasons_is_list(self):
        result = DocumentClassifier.classify(
            "document.pdf", check_content=False
        )
        assert isinstance(result["reasons"], list)

    def test_recommended_settings_is_dict(self):
        result = DocumentClassifier.classify(
            "document.pdf", check_content=False
        )
        assert isinstance(result["recommended_settings"], dict)
