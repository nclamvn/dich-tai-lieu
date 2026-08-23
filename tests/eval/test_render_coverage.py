"""CI guard: the live renderer must not lose source content.

Successor of ``test_ast_engine_soak.py`` — the engine-vs-AST comparison retired
with the legacy engines (stage 5); what remains is the absolute invariant. A
fast subset of ``scripts/soak_render_coverage.py``: renders one representative
document to DOCX and PDF and asserts source-token coverage stays at or above
the recorded floors.
"""

import asyncio

import pytest

from scripts.soak_render_coverage import (
    FLOORS,
    _coverage,
    _docx_text,
    _pdf_text,
    _render,
    _source_tokens,
    _tokens,
)

SAMPLE = (
    "# Chương một\n\n"
    "Đoạn văn có **chữ đậm**, *nghiêng* và `mã` — tiếng Việt đủ dấu.\n\n"
    "- mục **một**\n- mục hai\n\n"
    "1. bước đầu\n2. bước hai\n\n"
    "| Cột A | Cột B |\n| --- | --- |\n| dữ liệu | 1200 |\n"
)


@pytest.mark.parametrize("fmt,extract", [("docx", _docx_text), ("pdf", _pdf_text)])
def test_render_keeps_source_content(tmp_path, fmt, extract):
    from core_v2.output_converter import OutputConverter

    converter = OutputConverter(temp_dir=tmp_path / "_t")
    src = _source_tokens(SAMPLE)

    async def _go():
        out = tmp_path / f"doc.{fmt}"
        await _render(converter, fmt, SAMPLE, out)
        return set(_tokens(extract(out)))

    produced = asyncio.run(_go())
    cov = _coverage(src, produced)
    assert cov + 1e-9 >= FLOORS[fmt], (
        f"{fmt} coverage {cov:.3f} fell below floor {FLOORS[fmt]:.2f}; "
        f"missing tokens: {sorted(src - produced)[:10]}"
    )
