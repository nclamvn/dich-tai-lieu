"""CI guard: the AST output pipeline must not lose content vs the legacy engine.

A fast subset of ``scripts/soak_ast_vs_engine.py`` — renders one representative
document through OUTPUT_PIPELINE=engine and =ast for DOCX and PDF and asserts the
AST path drops no source token the engine kept and covers the source at least as
well. This is the objective, no-API-key gate for the Option-A stage-4 default flip.
"""

import asyncio

import pytest

from scripts.soak_ast_vs_engine import (
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


@pytest.fixture(autouse=True)
def _restore_pipeline_env(monkeypatch):
    # _render mutates os.environ["OUTPUT_PIPELINE"]; monkeypatch restores it.
    monkeypatch.setenv("OUTPUT_PIPELINE", "engine")
    yield


def _coverage(source, produced):
    return 1.0 if not source else len(source & produced) / len(source)


@pytest.mark.parametrize("fmt,extract", [("docx", _docx_text), ("pdf", _pdf_text)])
def test_ast_pipeline_not_worse_than_engine(tmp_path, fmt, extract):
    from core_v2.output_converter import OutputConverter

    converter = OutputConverter(temp_dir=tmp_path / "_t")
    src = _source_tokens(SAMPLE)

    async def _go():
        eng = tmp_path / f"engine.{fmt}"
        ast = tmp_path / f"ast.{fmt}"
        await _render(converter, fmt, SAMPLE, eng, "engine")
        await _render(converter, fmt, SAMPLE, ast, "ast")
        return set(_tokens(extract(eng))), set(_tokens(extract(ast)))

    eng_tok, ast_tok = asyncio.run(_go())

    dropped = sorted((src & eng_tok) - ast_tok)
    assert not dropped, f"AST dropped source tokens the engine kept ({fmt}): {dropped}"
    assert _coverage(src, ast_tok) + 1e-9 >= _coverage(src, eng_tok), (
        f"AST source coverage < engine for {fmt}"
    )
