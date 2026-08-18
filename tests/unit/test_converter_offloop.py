"""Off-loop rendering test for OutputConverter.convert_markdown_to_docx_professional.

Verifies the (blocking) professional DOCX render runs in a worker thread, so a
concurrent coroutine (ticker) keeps making progress while the render sleeps.

The real DocxRenderer is monkeypatched with a fake so we don't need python-docx
templates or i18n assets to fail/succeed — only the off-loop behaviour matters.
"""
import asyncio
import time
from pathlib import Path

import pytest

from core_v2 import output_converter
from core_v2.output_converter import OutputConverter


class _FakeToc:
    """TOC stub whose .title is settable by the converter."""
    title = None


class _FakeDoc:
    def __init__(self):
        self.toc = _FakeToc()
        self.glossary = None
        self.bibliography = None


class _FakeNormalizer:
    def from_markdown(self, markdown_content, meta):
        return _FakeDoc()


class _FakeDocxRenderer:
    def __init__(self, template=None):
        self.normalizer = _FakeNormalizer()

    def render_document(self, doc, path):
        time.sleep(0.2)  # simulates a slow blocking render
        Path(path).write_text("x")
        return path


@pytest.mark.asyncio
async def test_convert_docx_professional_runs_off_loop(tmp_path, monkeypatch):
    # DocxRenderer is imported at module top of output_converter.py.
    monkeypatch.setattr(output_converter, "DocxRenderer", _FakeDocxRenderer)

    ticks = []

    async def ticker():
        for _ in range(6):
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    conv = OutputConverter()
    out = tmp_path / "o.docx"

    result, _ = await asyncio.gather(
        conv.convert_markdown_to_docx_professional("# hi", out),
        ticker(),
    )

    assert Path(out).exists()
    assert str(out) == str(result)
    assert len(ticks) == 6
    gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
    # A blocking on-loop render (0.2s) would show up as one ~0.2s gap.
    assert max(gaps) < 0.15, f"event loop was blocked; gaps={gaps}"
