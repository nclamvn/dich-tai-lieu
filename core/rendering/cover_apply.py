"""Apply a chosen cover template to an already-produced export file.

Engine-agnostic on purpose: these helpers operate on the *finished* PDF/DOCX, so
a template cover works whether the document came from the legacy engine or the
AST pipeline. The cover is rendered at the produced file's own page size, so it
always matches.

``apply_cover_to_pdf`` merges a vector cover as page 1 (pypdf).
``apply_cover_to_docx`` inserts a full-bleed cover image as page 1 in its own
zero-margin section (python-docx), leaving the body's section/margins intact.

Both are best-effort: unknown template, missing file, or any error returns
``False`` and leaves the original file untouched (never fails the export).
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace

from core.rendering.cover_templates import (
    has_template,
    render_cover_image,
    render_cover_pdf,
)

logger = logging.getLogger(__name__)

_PT_PER_MM = 72.0 / 25.4          # PDF points per millimetre
_EMU_PER_MM = 36000.0            # DOCX English Metric Units per millimetre


def _meta(width_mm: float, height_mm: float, title: str, author: str, language: str):
    return SimpleNamespace(
        page_width_mm=width_mm,
        page_height_mm=height_mm,
        title=(title or "Untitled").strip() or "Untitled",
        author=(author or "").strip(),
        language=(language or "vi"),
    )


def apply_cover_to_pdf(
    pdf_path, template_id: str, *, title: str = "", author: str = "", language: str = "vi"
) -> bool:
    """Prepend a template cover (matched to the PDF's page size) as page 1."""
    pdf_path = Path(pdf_path)
    if not template_id or not has_template(template_id) or not pdf_path.is_file():
        return False
    try:
        import pypdf

        reader = pypdf.PdfReader(str(pdf_path))
        if not reader.pages:
            return False
        box = reader.pages[0].mediabox
        w_mm = float(box.width) / _PT_PER_MM
        h_mm = float(box.height) / _PT_PER_MM
        with tempfile.TemporaryDirectory() as td:
            cover = Path(td) / "cover.pdf"
            render_cover_pdf(template_id, _meta(w_mm, h_mm, title, author, language), cover)
            writer = pypdf.PdfWriter()
            for pg in pypdf.PdfReader(str(cover)).pages:
                writer.add_page(pg)
            for pg in reader.pages:
                writer.add_page(pg)
            with open(pdf_path, "wb") as fh:
                writer.write(fh)
        logger.info("applied '%s' cover to PDF %s", template_id, pdf_path.name)
        return True
    except Exception as e:  # pragma: no cover - never fail the export over a cover
        logger.warning("apply_cover_to_pdf failed (%s); PDF left unchanged", e)
        return False


def apply_cover_to_docx(
    docx_path, template_id: str, *, title: str = "", author: str = "", language: str = "vi"
) -> bool:
    """Insert a full-bleed cover image as page 1 in its own zero-margin section."""
    docx_path = Path(docx_path)
    if not template_id or not has_template(template_id) or not docx_path.is_file():
        return False
    try:
        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Emu, Pt

        document = docx.Document(str(docx_path))
        if not document.paragraphs:
            return False
        section = document.sections[0]
        pw, ph = int(section.page_width), int(section.page_height)  # EMU
        w_mm, h_mm = pw / _EMU_PER_MM, ph / _EMU_PER_MM

        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "cover.png"
            render_cover_image(
                template_id, _meta(w_mm, h_mm, title, author, language), img, scale=2.0
            )

            # New first paragraph carrying the full-page image.
            first = document.paragraphs[0]
            p = first.insert_paragraph_before()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf = p.paragraph_format
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            p.add_run().add_picture(str(img), width=Emu(pw), height=Emu(ph))

            # A sectPr on this paragraph makes it the last paragraph of a cover
            # section with the same page size but zero margins (true full-bleed);
            # the body keeps its own final sectPr / margins as the next section.
            # OOXML page size / margins are in twips (1/1440"), NOT EMU (1/914400").
            emu_to_twips = 635  # 914400 / 1440
            sect_pr = OxmlElement("w:sectPr")
            pg_sz = OxmlElement("w:pgSz")
            pg_sz.set(qn("w:w"), str(pw // emu_to_twips))
            pg_sz.set(qn("w:h"), str(ph // emu_to_twips))
            sect_pr.append(pg_sz)
            pg_mar = OxmlElement("w:pgMar")
            for edge in ("top", "right", "bottom", "left", "header", "footer", "gutter"):
                pg_mar.set(qn(f"w:{edge}"), "0")
            sect_pr.append(pg_mar)
            p._p.get_or_add_pPr().append(sect_pr)

            document.save(str(docx_path))
        logger.info("applied '%s' cover to DOCX %s", template_id, docx_path.name)
        return True
    except Exception as e:  # pragma: no cover - never fail the export over a cover
        logger.warning("apply_cover_to_docx failed (%s); DOCX left unchanged", e)
        return False
