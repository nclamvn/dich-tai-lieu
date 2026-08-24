"""TOC-entry detection and aligned rendering.

A source book's printed contents page extracts as ragged "Title......<page>"
lines (literal dots, page numbers landing wherever the text ends). These must be
reclassified as TOC entries and rendered with a right-aligned page number + dot
leader — in PDF and DOCX — so the whole contents list aligns to one right margin.
"""

import pytest

from core.rendering.document_extractor import parse_toc_line, extract_to_ast
from core.rendering.document_ast import (
    DocumentAST, DocumentMetadata, StyleSheet, Paragraph, ListBlock, ParagraphRole,
)


class TestParseTocLine:
    @pytest.mark.parametrize("line,title,page", [
        ("The Devil's Flame..............9", "The Devil's Flame", "9"),
        ("The Dance of Numbers..........25", "The Dance of Numbers", "25"),
        ("Lock and Key.................163", "Lock and Key", "163"),
        ("Notes . . . . . . 349", "Notes", "349"),  # space-separated dots
        ("The Source……341", "The Source", "341"),   # unicode ellipsis leaders
    ])
    def test_matches_toc_lines(self, line, title, page):
        assert parse_toc_line(line) == (title, page)

    @pytest.mark.parametrize("line", [
        "This is ordinary prose that ends in 1999",   # no dot leader
        "Deepfake: mimicking faces and voices.",        # no trailing number
        "1 . . . 2",                                     # no alphabetic title
        "See the note.",                                 # single dot, no number
        "",
    ])
    def test_rejects_non_toc(self, line):
        assert parse_toc_line(line) is None


def _ast(blocks):
    ast = DocumentAST(metadata=DocumentMetadata(title="t"), styles=StyleSheet())
    ast.blocks = blocks
    return ast


class TestDetectTocEntries:
    def test_converts_paragraph_toc_lines(self, tmp_path):
        md = tmp_path / "c.md"
        md.write_text(
            "## Table of Contents\n\n"
            "The Devil's Flame..............9\n\n"
            "The Source...................341\n"
        )
        ast = extract_to_ast(md)
        entries = [b for b in ast.blocks
                   if isinstance(b, Paragraph) and b.role == ParagraphRole.TOC_ENTRY]
        assert len(entries) == 2
        assert entries[0].text == "The Devil's Flame" and entries[0].page == "9"
        assert entries[1].text == "The Source" and entries[1].page == "341"

    def test_converts_misdetected_numbered_list(self, tmp_path):
        # A source TOC that markdown parsed as an ordered list (11. Title...page).
        md = tmp_path / "c.md"
        md.write_text(
            "## Contents\n\n"
            "11. The Devil's Flame..............9\n"
            "12. The Dance of Numbers..........25\n"
            "13. The Last Words................47\n"
        )
        ast = extract_to_ast(md)
        entries = [b for b in ast.blocks
                   if isinstance(b, Paragraph) and b.role == ParagraphRole.TOC_ENTRY]
        assert [e.text for e in entries] == [
            "The Devil's Flame", "The Dance of Numbers", "The Last Words"]
        assert [e.page for e in entries] == ["9", "25", "47"]
        # the bogus "11./12./13." list numbering is gone
        assert not any(isinstance(b, ListBlock) for b in ast.blocks)

    def test_leaves_normal_numbered_list_alone(self, tmp_path):
        md = tmp_path / "c.md"
        md.write_text(
            "1. Deepfake mimics faces and voices.\n"
            "2. AI has potentials and challenges.\n"
            "3. Stuxnet targeted control systems.\n"
        )
        ast = extract_to_ast(md)
        assert any(isinstance(b, ListBlock) for b in ast.blocks)
        assert not any(
            isinstance(b, Paragraph) and b.role == ParagraphRole.TOC_ENTRY
            for b in ast.blocks
        )


class TestRenderersAlignTocEntries:
    def test_pdf_emits_toc_line_flowable(self):
        from core.rendering.pdf_adapter import _PdfRenderer, _ensure_fonts
        ast = _ast([Paragraph(text="The Source", role=ParagraphRole.TOC_ENTRY, page="341")])
        r = _PdfRenderer(ast, _ensure_fonts())
        flows = r.flowables_for(ast.blocks[0])
        assert len(flows) == 1
        f = flows[0]
        assert type(f).__name__ == "_TocLineImpl"
        assert f.title == "The Source" and f.page == "341"

    def test_docx_writes_right_tab_with_dot_leader(self, tmp_path):
        import zipfile
        from core.rendering.docx_adapter import render_docx_from_ast
        ast = _ast([
            Paragraph(text="The Devil's Flame", role=ParagraphRole.TOC_ENTRY, page="9"),
        ])
        out = tmp_path / "toc.docx"
        render_docx_from_ast(ast, out, title="t", template="ebook",
                             title_page=False, toc=False, header_footer=False)
        xml = zipfile.ZipFile(out).read("word/document.xml").decode()
        assert 'w:val="right"' in xml and 'w:leader="dot"' in xml
        assert "The Devil's Flame" in xml and ">9<" in xml
