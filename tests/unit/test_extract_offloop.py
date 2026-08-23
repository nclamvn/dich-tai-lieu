"""Off-loop legacy PDF extraction tests for core_v2.orchestrator.

Verifies the blocking fitz/pdfplumber work now lives in the module-level
`_extract_pdf_text_sync` and that the async `_extract_pdf_text_legacy`
delegates to it (running it off the event loop via run_blocking).
"""
import pymupdf as fitz  # PyMuPDF (installed in this repo)
import pytest

from core_v2.orchestrator import UniversalPublisher, _extract_pdf_text_sync


def _make_pdf(path):
    """Build a tiny real PDF containing the text 'Hello Aurora'."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello Aurora")
    doc.save(str(path))
    doc.close()


def test_extract_pdf_text_sync_reads_text(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    text = _extract_pdf_text_sync(pdf_path)
    assert "Aurora" in text


@pytest.mark.asyncio
async def test_extract_pdf_text_legacy_offloop(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    # The method never touches self, so a bare instance is enough (avoids the
    # heavy __init__ that would need a real LLM client).
    publisher = object.__new__(UniversalPublisher)
    text = await publisher._extract_pdf_text_legacy(pdf_path)
    assert "Aurora" in text


@pytest.mark.asyncio
async def test_extract_pdf_text_legacy_delegates_to_sync(monkeypatch, tmp_path):
    called = {}

    def fake_sync(p):
        called["path"] = p
        return "FAKE TEXT"

    monkeypatch.setattr("core_v2.orchestrator._extract_pdf_text_sync", fake_sync)
    publisher = object.__new__(UniversalPublisher)
    pdf_path = tmp_path / "x.pdf"
    result = await publisher._extract_pdf_text_legacy(pdf_path)
    assert result == "FAKE TEXT"
    assert called["path"] == pdf_path
