"""PDF Adapter — render a Document AST to PDF via ReportLab (Sóng 1).

A second output path off the single L0 AST, parallel to ``docx_adapter``.
Covers the same blocks: headings, paragraphs, blockquote/epigraph/scene-break,
equations (LaTeX text fallback — ReportLab can't do OMML), theorem/proof,
references, tables, figures, lists, captions and page breaks.

Vietnamese matters here: ReportLab's built-in fonts don't cover Vietnamese
diacritics, so we register a Unicode TTF (DejaVuSans family) when available and
fall back to Helvetica with a warning otherwise.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

from core.rendering.document_ast import (
    Block,
    Blockquote,
    Caption,
    DocumentAST,
    Epigraph,
    Equation,
    Figure,
    Heading,
    ListBlock,
    PageBreak,
    Paragraph,
    ProofBox,
    ReferenceEntry,
    SceneBreak,
    TableBlock,
    TheoremBox,
)

logger = logging.getLogger(__name__)

# Font families to try, in order: (regular, bold, italic). First existing wins.
_FONT_FAMILIES = [
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ),
    (
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ),
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
    ),
]

_FONT_NAME = "DocFont"
_font_ready = False


def _ensure_font() -> str:
    """Register a Vietnamese-capable font family; return the family name.

    Falls back to the built-in 'Helvetica' (limited Vietnamese) if no Unicode
    TTF is found — a warning is logged so production can install one.
    """
    global _font_ready
    if _font_ready:
        return _FONT_NAME

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular, bold, italic in _FONT_FAMILIES:
        if not Path(regular).is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME, regular))
            pdfmetrics.registerFont(TTFont(f"{_FONT_NAME}-Bold", bold if Path(bold).is_file() else regular))
            pdfmetrics.registerFont(TTFont(f"{_FONT_NAME}-Italic", italic if Path(italic).is_file() else regular))
            pdfmetrics.registerFontFamily(
                _FONT_NAME,
                normal=_FONT_NAME,
                bold=f"{_FONT_NAME}-Bold",
                italic=f"{_FONT_NAME}-Italic",
                boldItalic=f"{_FONT_NAME}-Bold",
            )
            _font_ready = True
            return _FONT_NAME
        except Exception as e:  # pragma: no cover - registration edge cases
            logger.warning("Font registration failed for %s: %s", regular, e)

    logger.warning(
        "No Unicode TTF found; PDF falls back to Helvetica (limited Vietnamese). "
        "Install a Vietnamese-capable font (e.g. DejaVuSans) for production."
    )
    return "Helvetica"


class _PdfRenderer:
    def __init__(self, ast: DocumentAST, font: str):
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle

        self.ast = ast
        self.font = font
        bold = f"{font}-Bold" if font == _FONT_NAME else "Helvetica-Bold"
        size = ast.metadata.body_size_pt

        self.body = ParagraphStyle("body", fontName=font, fontSize=size, leading=size * 1.35, alignment=TA_JUSTIFY)
        self.headings = {
            1: ParagraphStyle("h1", fontName=bold, fontSize=16, leading=20, spaceBefore=14, spaceAfter=8),
            2: ParagraphStyle("h2", fontName=bold, fontSize=13, leading=17, spaceBefore=12, spaceAfter=6),
            3: ParagraphStyle("h3", fontName=bold, fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=5),
        }
        self.caption = ParagraphStyle("cap", fontName=font, fontSize=9.5, leading=12, alignment=TA_CENTER)
        self.quote = ParagraphStyle(
            "quote", fontName=font, fontSize=size - 0.5, leading=(size - 0.5) * 1.3,
            leftIndent=28, rightIndent=28, alignment=TA_JUSTIFY,
        )
        self.right = ParagraphStyle("right", fontName=font, fontSize=size - 1, leading=size * 1.2, alignment=TA_RIGHT)
        self.center = ParagraphStyle("center", fontName=font, fontSize=size, leading=size * 1.3, alignment=TA_CENTER)
        self.cell = ParagraphStyle("cell", fontName=font, fontSize=size - 1, leading=(size - 1) * 1.2)
        self.mono = ParagraphStyle("mono", fontName=font, fontSize=size, leading=size * 1.3, alignment=TA_CENTER)

    def flowables_for(self, block: Block) -> list:
        from reportlab.platypus import Paragraph as P
        from reportlab.platypus import PageBreak as RLPageBreak

        if isinstance(block, Heading):
            level = getattr(block.level, "value", 1)
            style = self.headings.get(level, self.headings[3])
            prefix = f"{block.number}. " if block.number else ""
            return [P(f"<b>{escape(prefix + block.text)}</b>", style)]
        if isinstance(block, Paragraph):
            return [P(escape(block.text), self.body)]
        if isinstance(block, Blockquote):
            out = [P(escape(block.text), self.quote)]
            if block.attribution:
                out.append(P(f"— {escape(block.attribution)}", self.right))
            return out
        if isinstance(block, Epigraph):
            out = [P(f"<i>{escape(block.text)}</i>", self.right)]
            if block.attribution:
                out.append(P(f"— {escape(block.attribution)}", self.right))
            return out
        if isinstance(block, SceneBreak):
            return [P(escape(block.symbol), self.center)]
        if isinstance(block, Equation):
            return [P(escape(f"$$ {block.latex} $$"), self.mono)]
        if isinstance(block, TheoremBox):
            title = block.title + (f" {block.number}" if block.number else "")
            return [P(f"<b>{escape(title)}</b>", self.body), P(escape(block.content), self.quote)]
        if isinstance(block, ProofBox):
            return [P(f"<i>Proof.</i> {escape(block.content)} {escape(block.qed_symbol)}", self.body)]
        if isinstance(block, ReferenceEntry):
            text = f"[{block.key}] {block.citation}" if block.key else block.citation
            return [P(escape(text), self.cell)]
        if isinstance(block, TableBlock):
            return self._table(block)
        if isinstance(block, Figure):
            return self._figure(block)
        if isinstance(block, ListBlock):
            return self._list(block)
        if isinstance(block, Caption):
            label = f"{block.target.capitalize()} {block.number}. " if (block.target and block.number) else ""
            return [P(escape(label + block.text), self.caption)]
        if isinstance(block, PageBreak):
            return [RLPageBreak()]
        logger.warning("PDF: unknown block type %s", type(block).__name__)
        return []

    def _table(self, block: TableBlock) -> list:
        from reportlab.lib import colors
        from reportlab.platypus import Paragraph as P
        from reportlab.platypus import Table, TableStyle

        rows = block.rows or []
        if not rows:
            return []
        n_cols = max(len(r) for r in rows)
        data = []
        for r, row in enumerate(rows):
            cells = []
            for c in range(n_cols):
                text = escape(row[c] if c < len(row) else "")
                cells.append(P(f"<b>{text}</b>" if r < block.header_rows else text, self.cell))
            data.append(cells)

        table = Table(data, repeatRows=max(0, block.header_rows))
        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        if block.header_rows > 0:
            style.append(("BACKGROUND", (0, 0), (-1, block.header_rows - 1), colors.Color(0.9, 0.9, 0.9)))
        table.setStyle(TableStyle(style))

        out = [table]
        if block.caption:
            out.append(P(escape(block.caption), self.caption))
        return out

    def _list(self, block: ListBlock) -> list:
        from reportlab.platypus import ListFlowable, ListItem
        from reportlab.platypus import Paragraph as P

        items = [ListItem(P(escape(text), self.body)) for text in block.items]
        return [ListFlowable(items, bulletType="1" if block.ordered else "bullet", leftIndent=20)]

    def _figure(self, block: Figure) -> list:
        from reportlab.platypus import Image
        from reportlab.platypus import Paragraph as P

        out: list = []
        ref = block.image_ref or ""
        added = False

        def _scaled(image) -> None:
            max_w = 400.0
            if image.drawWidth > max_w:
                ratio = max_w / image.drawWidth
                image.drawWidth *= ratio
                image.drawHeight *= ratio
            out.append(image)

        if block.image_bytes:
            try:
                from io import BytesIO

                _scaled(Image(BytesIO(block.image_bytes)))
                added = True
            except Exception as e:  # fall through to ref/placeholder
                logger.warning("PDF figure add from bytes failed: %s", e)

        if not added:
            try:
                if ref and not ref.startswith(("embedded", "/word/")) and Path(ref).is_file():
                    _scaled(Image(ref))
                    added = True
            except Exception as e:
                logger.warning("PDF figure add failed (%s): %s", ref, e)
        if not added:
            label = block.alt_text or block.caption or ref or "image"
            out.append(P(f"[Figure: {escape(label)}]", self.caption))
        if block.caption:
            prefix = f"Hình {block.number}. " if block.number else ""
            out.append(P(escape(prefix + block.caption), self.caption))
        return out


def render_pdf_from_ast(ast: DocumentAST, output_path: Path, title: Optional[str] = None) -> None:
    """Render a DocumentAST to a PDF file."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font = _ensure_font()
    renderer = _PdfRenderer(ast, font)
    md = ast.metadata

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=md.margin_top_mm * mm,
        bottomMargin=md.margin_bottom_mm * mm,
        leftMargin=md.margin_left_mm * mm,
        rightMargin=md.margin_right_mm * mm,
        title=title or md.title or "",
        author=md.author or "",
    )

    flowables: List = []
    for block in ast.blocks:
        try:
            flowables.extend(renderer.flowables_for(block))
        except Exception as e:
            logger.error("PDF render failed for block %s: %s", type(block).__name__, e)

    if not flowables:
        flowables.append(Spacer(1, 1))

    doc.build(flowables)
    logger.info("PDF saved: %s", output_path)
