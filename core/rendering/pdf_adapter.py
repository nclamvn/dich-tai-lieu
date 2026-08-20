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

# Serif faces (drive the ebook/academic templates); sans reuses the list above.
_SERIF_FAMILIES = [
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ),
]

# AST font families that map to the *sans* face; everything else (Georgia,
# Cambria, Times, "serif", …) maps to the serif face.
_SANS_FAMILY_NAMES = {
    "arial", "helvetica", "calibri", "verdana", "tahoma", "segoe ui",
    "sans", "sans-serif", "dejavusans", "liberation sans",
}

_faces_ready = False
_FACES = {"serif": "Helvetica", "sans": "Helvetica"}


def _register_family(name: str, candidates) -> str:
    """Register the first available (regular, bold, italic) TTF triple under
    *name*; return *name* on success, else 'Helvetica'."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular, bold, italic in candidates:
        if not Path(regular).is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, regular))
            pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold if Path(bold).is_file() else regular))
            pdfmetrics.registerFont(TTFont(f"{name}-Italic", italic if Path(italic).is_file() else regular))
            pdfmetrics.registerFontFamily(
                name, normal=name, bold=f"{name}-Bold",
                italic=f"{name}-Italic", boldItalic=f"{name}-Bold",
            )
            return name
        except Exception as e:  # pragma: no cover - registration edge cases
            logger.warning("Font registration failed for %s: %s", regular, e)
    return "Helvetica"


def _ensure_fonts() -> dict:
    """Register a serif + a sans Vietnamese-capable family; return their names.

    Serif drives the ebook/academic templates, sans the business template.
    Falls back to Helvetica (limited Vietnamese) if no Unicode TTF is found.
    """
    global _faces_ready, _FACES
    if _faces_ready:
        return _FACES
    _FACES = {
        "serif": _register_family("DocSerif", _SERIF_FAMILIES),
        "sans": _register_family("DocSans", _FONT_FAMILIES),
    }
    if _FACES["serif"] == "Helvetica" and _FACES["sans"] == "Helvetica":
        logger.warning(
            "No Unicode TTF found; PDF falls back to Helvetica (limited Vietnamese). "
            "Install a Vietnamese-capable font (e.g. DejaVu) for production."
        )
    _faces_ready = True
    return _FACES


def _face_for(family: str, faces: dict) -> str:
    """Pick the sans or serif registered face for an AST font-family name."""
    key = (family or "").strip().lower()
    return faces["sans"] if key in _SANS_FAMILY_NAMES else faces["serif"]


def _stylesheet_for_template(name: str):
    """Map a template name to a StyleSheet (kept in sync with
    docx_adapter._stylesheet_for_template; de-duplicate in a later cleanup)."""
    from core.rendering.document_ast import (
        create_academic_stylesheet,
        create_book_stylesheet,
    )

    key = (name or "").strip().lower()
    if key in ("academic", "stem"):
        return create_academic_stylesheet()
    if key in ("business", "report"):
        sheet = create_book_stylesheet()
        for ps in (sheet.heading_1, sheet.heading_2, sheet.heading_3, sheet.body):
            ps.font.family = "Arial"
        sheet.body.alignment = "left"
        sheet.body.spacing.first_line_indent_pt = 0.0
        return sheet
    return create_book_stylesheet()  # ebook / book / default


class _PdfRenderer:
    def __init__(self, ast: DocumentAST, faces: dict):
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle

        self.ast = ast
        s = ast.styles
        align_map = {"justify": TA_JUSTIFY, "left": TA_LEFT, "right": TA_RIGHT, "center": TA_CENTER}

        def _bold(face):
            return f"{face}-Bold" if face != "Helvetica" else "Helvetica-Bold"

        body_face = _face_for(s.body.font.family, faces)
        self.font = body_face
        size = s.body.font.size_pt
        self.body = ParagraphStyle(
            "body", fontName=body_face, fontSize=size,
            leading=size * (s.body.spacing.line_spacing or 1.35),
            alignment=align_map.get(s.body.alignment, TA_JUSTIFY),
        )
        self.headings = {
            lvl: ParagraphStyle(
                f"h{lvl}",
                fontName=_bold(_face_for(hs.font.family, faces)),
                fontSize=hs.font.size_pt,
                leading=hs.font.size_pt * 1.25,
                spaceBefore=hs.spacing.space_before_pt,
                spaceAfter=hs.spacing.space_after_pt,
            )
            for lvl, hs in ((1, s.heading_1), (2, s.heading_2), (3, s.heading_3))
        }
        self.caption = ParagraphStyle("cap", fontName=body_face, fontSize=9.5, leading=12, alignment=TA_CENTER)
        self.quote = ParagraphStyle(
            "quote", fontName=body_face, fontSize=size - 0.5, leading=(size - 0.5) * 1.3,
            leftIndent=28, rightIndent=28, alignment=TA_JUSTIFY,
        )
        self.right = ParagraphStyle("right", fontName=body_face, fontSize=size - 1, leading=size * 1.2, alignment=TA_RIGHT)
        self.center = ParagraphStyle("center", fontName=body_face, fontSize=size, leading=size * 1.3, alignment=TA_CENTER)
        self.cell = ParagraphStyle("cell", fontName=body_face, fontSize=size - 1, leading=(size - 1) * 1.2)
        self.mono = ParagraphStyle("mono", fontName=body_face, fontSize=size, leading=size * 1.3, alignment=TA_CENTER)

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


def render_pdf_from_ast(
    ast: DocumentAST,
    output_path: Path,
    title: Optional[str] = None,
    template: Optional[str] = None,
) -> None:
    """Render a DocumentAST to a PDF file. ``template`` (ebook/academic/business)
    swaps the stylesheet — serif face for ebook/academic, sans for business —
    mirroring the DOCX renderer; when None, the AST's own styles are used."""
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer

    if template:
        import dataclasses

        ast = dataclasses.replace(ast, styles=_stylesheet_for_template(template))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    faces = _ensure_fonts()
    renderer = _PdfRenderer(ast, faces)
    md = ast.metadata

    doc = SimpleDocTemplate(
        str(output_path),
        # Page size from metadata (defaults to A4) — parity with the legacy
        # engine's page presets instead of a hardcoded A4.
        pagesize=(md.page_width_mm * mm, md.page_height_mm * mm),
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
