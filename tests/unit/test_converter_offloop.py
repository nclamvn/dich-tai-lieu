"""Off-loop rendering test for OutputConverter.convert_markdown_to_docx_professional.

Verifies the (blocking) professional DOCX render runs in a worker thread, so a
concurrent coroutine (ticker) keeps making progress while the render sleeps.

The heavy AST renderer (``render_docx_from_ast`` — the only DOCX stack since
Option A stage 5) is monkeypatched with a slow blocking fake, so only the
off-loop behaviour is under test.
"""
import asyncio
import time
from pathlib import Path

import pytest

import core.rendering.docx_adapter as docx_adapter
from core_v2.output_converter import OutputConverter


def _slow_fake_render(ast, output_path, **kwargs):
    time.sleep(0.2)  # simulates a slow blocking render
    Path(output_path).write_text("x")


@pytest.mark.asyncio
async def test_convert_docx_professional_runs_off_loop(tmp_path, monkeypatch):
    # _markdown_to_docx_via_ast does `from core.rendering.docx_adapter import
    # render_docx_from_ast` at call time, so patching the adapter module works.
    monkeypatch.setattr(docx_adapter, "render_docx_from_ast", _slow_fake_render)

    ticks = []

    async def ticker():
        for _ in range(6):
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    conv = OutputConverter(temp_dir=tmp_path / "t")
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
