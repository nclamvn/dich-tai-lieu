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
from core.rendering.inline import parse_inline

logger = logging.getLogger(__name__)

# Bundled fonts (shipped in the repo) — full Vietnamese coverage, so covers and
# PDFs render diacritics correctly on every machine regardless of system fonts.
_BUNDLED_FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"

# Font families to try, in order: (regular, bold, italic). First existing wins.
# Bundled Noto Sans is tried FIRST; system fonts remain as fallbacks.
_FONT_FAMILIES = [
    (
        str(_BUNDLED_FONTS / "NotoSans-Regular.ttf"),
        str(_BUNDLED_FONTS / "NotoSans-Bold.ttf"),
        str(_BUNDLED_FONTS / "NotoSans-Italic.ttf"),
    ),
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
# Bundled Noto Serif (full Vietnamese) is tried FIRST; system fonts fall back.
_SERIF_FAMILIES = [
    (
        str(_BUNDLED_FONTS / "NotoSerif-Regular.ttf"),
        str(_BUNDLED_FONTS / "NotoSerif-Bold.ttf"),
        str(_BUNDLED_FONTS / "NotoSerif-Italic.ttf"),
    ),
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


def _runs_to_rl_markup(runs) -> str:
    """Render inline runs as ReportLab intra-paragraph markup.

    ``<b>``/``<i>`` resolve to the registered font family's bold/italic faces
    (see ``_register_family``'s ``registerFontFamily``); inline code uses the
    always-available built-in ``Courier``. Run text is XML-escaped; the tags are
    literal markup. Tags nest code → italic → bold (innermost to outermost).
    """
    parts = []
    for r in runs:
        t = escape(r.text)
        if r.code:
            t = f'<font face="Courier">{t}</font>'
        if r.italic:
            t = f"<i>{t}</i>"
        if r.bold:
            t = f"<b>{t}</b>"
        parts.append(t)
    return "".join(parts)


def _inline_markup(text: str) -> str:
    """ReportLab intra-paragraph markup for *text*: inline emphasis spans when the
    text has Markdown markers, else the escaped plain text (unchanged)."""
    runs = parse_inline(text)
    return _runs_to_rl_markup(runs) if runs else escape(text)


def _toc_flowable_base():
    """Lazily build the ``_TocLine`` flowable class (keeps reportlab off the
    module import path)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import Flowable

    class _TocLineImpl(Flowable):
        """One contents line: title flush-left, page flush-right, a dot leader
        filling the gap. Renders identically whatever the title/page lengths, so
        the whole contents list aligns to a single right margin — the fix for
        source-book TOC pages that extract as ragged literal-dot paragraphs."""

        def __init__(self, title: str, page: str, style):
            super().__init__()
            self.title = title
            self.page = page
            self.style = style

        def wrap(self, avail_w, avail_h):
            self.width = avail_w
            self.height = self.style.leading
            return avail_w, self.height

        def draw(self):
            c = self.canv
            st = self.style
            fn, fs = st.fontName, st.fontSize
            y = (self.height - fs) / 2.0 + fs * 0.18  # visually-centered baseline
            c.setFont(fn, fs)
            title_w = stringWidth(self.title, fn, fs)
            page_w = stringWidth(self.page, fn, fs)
            c.drawString(0, y, self.title)
            c.drawRightString(self.width, y, self.page)
            dot = "."
            dot_w = stringWidth(dot, fn, fs)
            gap = fs * 0.4
            start = title_w + gap
            end = self.width - page_w - gap
            if end > start and dot_w > 0:
                n = int((end - start) / dot_w)
                if n > 0:
                    # right-align the dot run against the page number (classic look)
                    c.drawString(end - n * dot_w, y, dot * n)

    return _TocLineImpl


# Built once on first use.
_TocLine = None  # type: ignore


def _ensure_toc_line():
    global _TocLine
    if _TocLine is None:
        _TocLine = _toc_flowable_base()
    return _TocLine


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
        # Body honors the stylesheet's paragraph spacing — space_after so
        # paragraphs breathe, first-line indent for the classic book look.
        # (Headings always consumed these; body silently dropped them, which
        # rendered novels as a solid justified wall of text.)
        self.body = ParagraphStyle(
            "body", fontName=body_face, fontSize=size,
            leading=size * (s.body.spacing.line_spacing or 1.35),
            alignment=align_map.get(s.body.alignment, TA_JUSTIFY),
            spaceAfter=s.body.spacing.space_after_pt,
            firstLineIndent=s.body.spacing.first_line_indent_pt,
        )
        # First paragraph after a heading/section break: no indent
        # (commercial convention — mirrors the DOCX adapter's role handling).
        self.body_first = ParagraphStyle(
            "body_first", parent=self.body, firstLineIndent=0.0,
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
            from core.rendering.document_ast import ParagraphRole

            role = getattr(block, "role", None)
            if role == ParagraphRole.TOC_ENTRY and getattr(block, "page", None):
                return [_ensure_toc_line()(block.text, str(block.page), self.body)]
            style = (
                self.body_first
                if role == ParagraphRole.FIRST_PARAGRAPH
                else self.body
            )
            if block.runs:
                return [P(_runs_to_rl_markup(block.runs), style)]
            return [P(escape(block.text), style)]
        if isinstance(block, Blockquote):
            out = [P(_inline_markup(block.text), self.quote)]
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
                markup = _inline_markup(row[c] if c < len(row) else "")
                cells.append(P(f"<b>{markup}</b>" if r < block.header_rows else markup, self.cell))
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

        items = [ListItem(P(_inline_markup(text), self.body)) for text in block.items]
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

    # ---- Front matter (Option A: PDF parity with the DOCX book layout) ----
    def _toc_title(self) -> str:
        lang = (self.ast.metadata.language or "").strip().lower()
        return {"vi": "Mục lục"}.get(lang, "Contents")

    def title_page_flowables(self, title: Optional[str], author: Optional[str]) -> list:
        """A centered cover page (title + author) followed by a page break."""
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import PageBreak as _PB
        from reportlab.platypus import Paragraph as _P
        from reportlab.platypus import Spacer

        title_style = ParagraphStyle(
            "cover_title", fontName=self.headings[1].fontName,
            fontSize=26, leading=32, alignment=TA_CENTER,
        )
        author_style = ParagraphStyle(
            "cover_author", fontName=self.font, fontSize=14, leading=20, alignment=TA_CENTER,
        )
        out: list = [Spacer(1, 120)]
        if title:
            out.append(_P(escape(title), title_style))
        if author:
            out.append(Spacer(1, 24))
            out.append(_P(escape(author), author_style))
        out.append(_PB())
        return out

    def toc_flowables(self) -> list:
        """A localized heading + a real TableOfContents (page numbers resolved by
        the multiBuild pass), followed by a page break."""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import PageBreak as _PB
        from reportlab.platypus import Paragraph as _P
        from reportlab.platypus.tableofcontents import TableOfContents

        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle("toc1", fontName=self.font, fontSize=12, leading=18,
                           leftIndent=20, firstLineIndent=-20),
            ParagraphStyle("toc2", fontName=self.font, fontSize=11, leading=16,
                           leftIndent=40, firstLineIndent=-20),
            ParagraphStyle("toc3", fontName=self.font, fontSize=10, leading=14,
                           leftIndent=60, firstLineIndent=-20),
        ]
        heading = _P(f"<b>{escape(self._toc_title())}</b>", self.headings[1])
        return [heading, toc, _PB()]


def _make_footer(page_face: str, page_width_pt: float, bottom_margin_pt: float, skip_first: bool):
    """Build an onPage callback that draws a centered page number, skipping the
    cover (page 1) when *skip_first* is set."""
    def _draw(canvas, doc) -> None:
        if skip_first and doc.page <= 1:
            return
        canvas.saveState()
        canvas.setFont(page_face, 9)
        canvas.drawCentredString(page_width_pt / 2.0, max(bottom_margin_pt / 2.0, 12.0), str(doc.page))
        canvas.restoreState()

    return _draw


def _toc_doc_template_cls():
    """A SimpleDocTemplate subclass that feeds heading flowables to the TOC (via
    ``notify('TOCEntry', …)``) so page numbers resolve during ``multiBuild``.
    Built lazily to keep reportlab off the module import path."""
    from reportlab.platypus import Paragraph as _P
    from reportlab.platypus import SimpleDocTemplate

    class _TocDocTemplate(SimpleDocTemplate):
        def afterFlowable(self, flowable) -> None:  # noqa: N802 (reportlab hook name)
            style = getattr(flowable, "style", None)
            if isinstance(flowable, _P) and style is not None and style.name in ("h1", "h2", "h3"):
                self.notify("TOCEntry", (int(style.name[1]) - 1, flowable.getPlainText(), self.page))

    return _TocDocTemplate


def render_pdf_from_ast(
    ast: DocumentAST,
    output_path: Path,
    title: Optional[str] = None,
    template: Optional[str] = None,
    title_page: bool = False,
    toc: bool = False,
    header_footer: bool = False,
    cover_template: Optional[str] = None,
) -> None:
    """Render a DocumentAST to a PDF file.

    ``template`` (ebook/academic/business) swaps the stylesheet — serif face for
    ebook/academic, sans for business — mirroring the DOCX renderer; when None,
    the AST's own styles are used. The front-matter flags mirror the DOCX book
    layout (all default-off): ``title_page`` prepends a centered cover,
    ``toc`` inserts a real table of contents with page numbers (built via
    multiBuild), and ``header_footer`` adds a centered page-number footer (the
    cover is left unnumbered)."""
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer

    output_path = Path(output_path)

    # Pre-built cover template: render the body WITHOUT the plain Platypus cover,
    # render the chosen template to its own page, and merge it in as page 1.
    # Default-safe: unknown template falls through to the normal cover path.
    if cover_template:
        from core.rendering import cover_templates as _covers

        if _covers.has_template(cover_template):
            import tempfile

            import pypdf

            with tempfile.TemporaryDirectory() as _td:
                body = Path(_td) / "body.pdf"
                cover = Path(_td) / "cover.pdf"
                render_pdf_from_ast(
                    ast, body, title=title, template=template,
                    title_page=False, toc=toc, header_footer=header_footer,
                )
                _covers.render_cover_pdf(cover_template, ast.metadata, cover, title=title)
                writer = pypdf.PdfWriter()
                for pg in pypdf.PdfReader(str(cover)).pages:
                    writer.add_page(pg)
                for pg in pypdf.PdfReader(str(body)).pages:
                    writer.add_page(pg)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as fh:
                    writer.write(fh)
            logger.info("PDF saved with '%s' cover: %s", cover_template, output_path)
            return
        logger.warning("unknown cover_template %r; using default cover path", cover_template)

    if template:
        import dataclasses

        ast = dataclasses.replace(ast, styles=_stylesheet_for_template(template))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    faces = _ensure_fonts()
    renderer = _PdfRenderer(ast, faces)
    md = ast.metadata

    doc_cls = _toc_doc_template_cls() if toc else SimpleDocTemplate
    doc = doc_cls(
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
    if title_page:
        flowables.extend(renderer.title_page_flowables(title or md.title, md.author))
    if toc:
        flowables.extend(renderer.toc_flowables())
    for block in ast.blocks:
        try:
            flowables.extend(renderer.flowables_for(block))
        except Exception as e:
            logger.error("PDF render failed for block %s: %s", type(block).__name__, e)

    if not flowables:
        flowables.append(Spacer(1, 1))

    build_kwargs = {}
    if header_footer:
        footer = _make_footer(
            renderer.font, md.page_width_mm * mm, md.margin_bottom_mm * mm, skip_first=title_page
        )
        build_kwargs = {"onFirstPage": footer, "onLaterPages": footer}

    if toc:
        doc.multiBuild(flowables, **build_kwargs)
    else:
        doc.build(flowables, **build_kwargs)
    logger.info("PDF saved: %s", output_path)
