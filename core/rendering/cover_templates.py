"""Pre-built book-cover templates rendered natively with ReportLab.

A small library of professional cover designs — the backend counterpart of the
front-end template picker. Each template is a pure drawing function over a
ReportLab canvas, so a cover renders with **no extra dependencies** (ReportLab +
pypdf already ship with the app) and works on every install, unlike an
HTML→PDF/Chromium approach that would force a heavy runtime download on users.

Text is drawn with the same Vietnamese-capable serif/sans faces the PDF adapter
registers (``_ensure_fonts``), so diacritics render correctly. Titles are
auto-fitted (shrink-to-fit + wrap) so any length lays out without overflow.

Public API
----------
``list_templates()``              -> [{id, name, category, description}, …]
``has_template(id)``              -> bool
``render_cover_pdf(id, meta, out, *, title=None, kicker=None)`` -> Path

The rendered cover is a single page at the document's page size; the PDF adapter
merges it as page 1 (see ``render_pdf_from_ast(cover_template=…)``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Fonts / context
# --------------------------------------------------------------------------- #
def _faces() -> dict:
    """Serif + sans (and their bold variants) registered by the PDF adapter."""
    from core.rendering.pdf_adapter import _ensure_fonts

    f = _ensure_fonts()

    def bold(name: str) -> str:
        return "Helvetica-Bold" if name == "Helvetica" else f"{name}-Bold"

    return {
        "serif": f["serif"], "serif_b": bold(f["serif"]),
        "sans": f["sans"], "sans_b": bold(f["sans"]),
    }


def _initials(title: str, author: str) -> str:
    src = (title or author or "").strip()
    words = [w for w in re.split(r"\s+", src) if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return (src[:2] or "•").upper()


@dataclass
class CoverContext:
    title: str
    author: str = ""
    kicker: Optional[str] = None
    language: str = "vi"
    faces: dict = field(default_factory=dict)
    initials: str = ""

    def kick(self, default_vi: str = "TIỂU THUYẾT", default_en: str = "A NOVEL") -> str:
        if self.kicker is not None:
            return self.kicker
        return default_vi if (self.language or "").startswith("vi") else default_en


# --------------------------------------------------------------------------- #
# Drawing helpers (top-left friendly: callers pass y measured from the top)
# --------------------------------------------------------------------------- #
def _C(hex_or_color):
    from reportlab.lib.colors import HexColor

    return HexColor(hex_or_color) if isinstance(hex_or_color, str) else hex_or_color


def _bg(c, W, H, color):
    c.setFillColor(_C(color))
    c.rect(0, 0, W, H, fill=1, stroke=0)


def _vgradient(c, W, H, top, bottom):
    """Full-page vertical gradient; falls back to a solid fill on any error."""
    try:
        c.linearGradient(0, H, 0, 0, [_C(top), _C(bottom)], extend=True)
    except Exception:  # pragma: no cover - reportlab version guard
        _bg(c, W, H, bottom)


def _radial(c, W, H, cx, cy, r, inner, outer):
    try:
        c.radialGradient(cx, cy, r, [_C(inner), _C(outer)], extend=True)
    except Exception:  # pragma: no cover
        _bg(c, W, H, outer)


def _wrap(c, text, font, size, max_w):
    words = text.split()
    if not words:
        return [text]
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if not cur or c.stringWidth(t, font, size) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(c, text, font, max_size, min_size, max_w, max_lines):
    """Largest size in [min,max] whose wrap fits max_w within max_lines."""
    size = max_size
    while size > min_size:
        lines = _wrap(c, text, font, size, max_w)
        if len(lines) <= max_lines and max(c.stringWidth(x, font, size) for x in lines) <= max_w:
            return size, lines
        size -= 1
    return min_size, _wrap(c, text, font, min_size, max_w)[:max_lines]


def _draw_lines(c, lines, cx, top_y, font, size, leading, color, align="center", left_x=None):
    c.setFillColor(_C(color))
    c.setFont(font, size)
    y = top_y
    for ln in lines:
        if align == "center":
            c.drawCentredString(cx, y, ln)
        else:
            c.drawString(left_x if left_x is not None else cx, y, ln)
        y -= leading
    return y


def _text(c, s, x, y, font, size, color, align="center", tracking=0.0, upper=False):
    if not s:
        return
    if upper:
        s = s.upper()
    c.setFillColor(_C(color))
    c.setFont(font, size)
    if not tracking:
        if align == "center":
            c.drawCentredString(x, y, s)
        elif align == "right":
            c.drawRightString(x, y, s)
        else:
            c.drawString(x, y, s)
        return
    # Letter-spacing needs a text object (Canvas has no char-space setter).
    width = c.stringWidth(s, font, size) + tracking * max(len(s) - 1, 0)
    sx = x - width / 2 if align == "center" else (x - width if align == "right" else x)
    to = c.beginText(sx, y)
    to.setFont(font, size)
    to.setCharSpace(tracking)
    to.setFillColor(_C(color))
    to.textOut(s)
    c.drawText(to)


def _kick_above(c, text, x, first_baseline, title_size, font, ksize, color, tracking, align="center"):
    """Draw a kicker safely ABOVE a title whose first line sits at
    ``first_baseline`` — text rises ~0.72·size above its baseline, so a naive
    fixed y overlaps the title. Places the kicker a clear gap above the cap."""
    ky = first_baseline + 0.72 * title_size + ksize + 6
    _text(c, text, x, ky, font, ksize, color, align=align, tracking=tracking, upper=True)


# --------------------------------------------------------------------------- #
# Templates — each draws a full-bleed cover on canvas c of size (W, H)
# --------------------------------------------------------------------------- #
def _classic(c, W, H, ctx):
    _bg(c, W, H, "#f4efe3")
    cx, maxw = W / 2, W * 0.78
    _text(c, ctx.kick(), cx, H * 0.86, ctx.faces["sans"], W * 0.028, "#9c8a67",
          tracking=W * 0.006, upper=True)
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.14, W * 0.06, maxw, 3)
    c.setStrokeColor(_C("#b9a986"))
    c.setLineWidth(0.8)
    c.line(cx - W * 0.09, H * 0.66, cx + W * 0.09, H * 0.66)
    y = _draw_lines(c, lines, cx, H * 0.52, ctx.faces["serif_b"], size, size * 1.05, "#26211a")
    c.line(cx - W * 0.09, y + size * 0.15, cx + W * 0.09, y + size * 0.15)
    _text(c, ctx.author, cx, H * 0.12, ctx.faces["serif"], W * 0.042, "#4a4235")


def _minimal(c, W, H, ctx):
    _bg(c, W, H, "#ffffff")
    lx, maxw = W * 0.12, W * 0.76
    _text(c, ctx.kick(), lx, H * 0.86, ctx.faces["sans"], W * 0.026, "#111",
          align="left", tracking=W * 0.004, upper=True)
    size, lines = _fit(c, ctx.title, ctx.faces["sans"], W * 0.13, W * 0.06, maxw, 3)
    _draw_lines(c, lines, lx, H * 0.78, ctx.faces["sans"], size, size * 1.08, "#111",
                align="left", left_x=lx)
    c.setStrokeColor(_C("#111"))
    c.setLineWidth(1)
    c.line(lx, H * 0.5, lx + maxw, H * 0.5)
    c.setFillColor(_C("#e5484d"))
    c.circle(lx + W * 0.02, H * 0.44, W * 0.02, fill=1, stroke=0)
    _text(c, ctx.author, lx, H * 0.1, ctx.faces["sans"], W * 0.036, "#7a7a7a", align="left")


def _bold(c, W, H, ctx):
    _bg(c, W, H, "#121212")
    lx, maxw = W * 0.08, W * 0.84
    _text(c, ctx.author, lx, H * 0.9, ctx.faces["sans"], W * 0.03, "#8a8a8a",
          align="left", tracking=W * 0.004, upper=True)
    size, lines = _fit(c, ctx.title, ctx.faces["sans_b"], W * 0.2, W * 0.09, maxw, 3)
    total = size * 0.95 * len(lines)
    top = H / 2 + total / 2
    y = top
    c.setFont(ctx.faces["sans_b"], size)
    for i, ln in enumerate(lines):
        c.setFillColor(_C("#ffd400" if i == len(lines) - 1 else "#ffffff"))
        c.drawString(lx, y, ln.upper())
        y -= size * 0.95
    _text(c, ctx.kick(), lx, H * 0.08, ctx.faces["sans"], W * 0.03, "#bdbdbd",
          align="left", tracking=W * 0.004, upper=True)


def _noir(c, W, H, ctx):
    _radial(c, W, H, W / 2, H * 0.98, H * 0.9, "#241419", "#0c0b0e")
    lx, maxw = W * 0.09, W * 0.82
    _text(c, ctx.kick("THRILLER", "THRILLER"), lx, H * 0.9, ctx.faces["sans"],
          W * 0.028, "#c0392b", align="left", tracking=W * 0.007, upper=True)
    c.setStrokeColor(_C("#c0392b"))
    c.setLineWidth(2)
    c.line(lx, H * 0.5, lx + W * 0.22, H * 0.5)
    size, lines = _fit(c, ctx.title, ctx.faces["sans_b"], W * 0.17, W * 0.08, maxw, 3)
    _draw_lines(c, lines, lx, H * 0.44, ctx.faces["sans_b"], size, size * 1.0, "#f3ede4",
                align="left", left_x=lx)
    _text(c, ctx.author, lx, H * 0.1, ctx.faces["sans"], W * 0.036, "#a99",
          align="left", tracking=W * 0.003, upper=True)


def _gradient(c, W, H, ctx):
    _vgradient(c, W, H, "#4f46e5", "#f43f5e")
    cx, maxw = W / 2, W * 0.72
    first = H * 0.5
    size, lines = _fit(c, ctx.title, ctx.faces["sans_b"], W * 0.15, W * 0.07, maxw, 3)
    _kick_above(c, ctx.kick(), cx, first, size, ctx.faces["sans"], W * 0.03, "#ffffff", W * 0.005)
    _draw_lines(c, lines, cx, first, ctx.faces["sans_b"], size, size * 1.05, "#ffffff")
    _text(c, ctx.author, cx, H * 0.1, ctx.faces["sans"], W * 0.038, "#ffffff",
          tracking=W * 0.004, upper=True)


def _duotone(c, W, H, ctx):
    _vgradient(c, W, H, "#123a5c", "#06172a")
    # simple moon + horizon suggestion (kept minimal, pure vector)
    c.setFillColor(_C("#f0b64a"))
    c.circle(W * 0.74, H * 0.8, W * 0.06, fill=1, stroke=0)
    c.setFillColor(_C("#0a2036"))
    c.rect(0, 0, W, H * 0.22, fill=1, stroke=0)
    lx, maxw = W * 0.09, W * 0.82
    first = H * 0.4
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.14, W * 0.07, maxw, 3)
    _kick_above(c, ctx.kick(), lx, first, size, ctx.faces["sans"], W * 0.026, "#8fb4dd",
                W * 0.006, align="left")
    _draw_lines(c, lines, lx, first, ctx.faces["serif_b"], size, size * 1.02, "#eaf2ff",
                align="left", left_x=lx)
    _text(c, ctx.author, lx, H * 0.1, ctx.faces["sans"], W * 0.034, "#b9cde6", align="left")


def _geometric(c, W, H, ctx):
    _bg(c, W, H, "#f6f3ec")
    c.setFillColor(_C("#f2b705"))
    c.circle(W * 0.82, H * 0.82, W * 0.22, fill=1, stroke=0)
    c.setFillColor(_C("#2d6cdf"))
    p = c.beginPath()
    p.moveTo(0, H * 0.42)
    p.lineTo(W * 0.34, H * 0.42)
    p.lineTo(0, H * 0.12)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(_C("#e5484d"))
    c.rect(W * 0.72, H * 0.1, W * 0.14, W * 0.14, fill=1, stroke=0)
    lx, maxw = W * 0.09, W * 0.7
    first = H * 0.5
    size, lines = _fit(c, ctx.title, ctx.faces["sans_b"], W * 0.15, W * 0.07, maxw, 3)
    _kick_above(c, ctx.kick(), lx, first, size, ctx.faces["sans"], W * 0.026, "#111",
                W * 0.005, align="left")
    _draw_lines(c, lines, lx, first, ctx.faces["sans_b"], size, size * 1.02, "#111",
                align="left", left_x=lx)
    _text(c, ctx.author, lx, H * 0.055, ctx.faces["sans_b"], W * 0.036, "#111", align="left")


def _framed(c, W, H, ctx):
    _bg(c, W, H, "#fbf7ef")
    m = W * 0.08
    c.setStrokeColor(_C("#b79b6b"))
    c.setLineWidth(1)
    c.rect(m, m, W - 2 * m, H - 2 * m, fill=0, stroke=1)
    c.setLineWidth(0.6)
    c.rect(m + 4, m + 4, W - 2 * m - 8, H - 2 * m - 8, fill=0, stroke=1)
    cx, maxw = W / 2, W * 0.66
    _text(c, ctx.kick(), cx, H * 0.72, ctx.faces["sans"], W * 0.026, "#a2854f",
          tracking=W * 0.005, upper=True)
    c.setStrokeColor(_C("#b79b6b"))
    c.circle(cx, H * 0.63, W * 0.045, fill=0, stroke=1)
    _text(c, "✦", cx, H * 0.628 - W * 0.02, ctx.faces["serif"], W * 0.04, "#a2854f")
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.14, W * 0.06, maxw, 3)
    _draw_lines(c, lines, cx, H * 0.5, ctx.faces["serif_b"], size, size * 1.05, "#2a2115")
    _text(c, ctx.author, cx, H * 0.16, ctx.faces["serif"], W * 0.044, "#5a4a30")


def _colorblock(c, W, H, ctx):
    _bg(c, W, H, "#f5f5f4")
    c.setFillColor(_C("#0f766e"))
    c.rect(0, H * 0.4, W, H * 0.6, fill=1, stroke=0)
    lx, maxw = W * 0.09, W * 0.82
    _text(c, ctx.kick(), lx, H * 0.86, ctx.faces["sans"], W * 0.026, "#cfeae6",
          align="left", tracking=W * 0.006, upper=True)
    size, lines = _fit(c, ctx.title, ctx.faces["sans_b"], W * 0.15, W * 0.07, maxw, 3)
    _draw_lines(c, lines, lx, H * 0.62, ctx.faces["sans_b"], size, size * 1.02, "#ffffff",
                align="left", left_x=lx)
    _text(c, ctx.author, lx, H * 0.2, ctx.faces["sans_b"], W * 0.044, "#111", align="left")


def _academic(c, W, H, ctx):
    _bg(c, W, H, "#ffffff")
    c.setFillColor(_C("#1e3a8a"))
    c.rect(0, H - H * 0.14, W, H * 0.14, fill=1, stroke=0)
    _text(c, "AI PUBLISHER PRO", W * 0.09, H - H * 0.09, ctx.faces["sans"], W * 0.024,
          "#ffffff", align="left", tracking=W * 0.006, upper=True)
    cx, maxw = W / 2, W * 0.78
    first = H * 0.52
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.12, W * 0.06, maxw, 3)
    _kick_above(c, ctx.kick("CHUYÊN KHẢO", "MONOGRAPH"), cx, first, size, ctx.faces["sans"],
                W * 0.026, "#8a93a6", W * 0.006)
    _draw_lines(c, lines, cx, first, ctx.faces["serif_b"], size, size * 1.05, "#15223b")
    c.setStrokeColor(_C("#c9d2e3"))
    c.setLineWidth(1)
    c.line(cx - W * 0.13, H * 0.42, cx + W * 0.13, H * 0.42)
    _text(c, ctx.author, cx, H * 0.15, ctx.faces["serif_b"], W * 0.04, "#15223b")
    _text(c, "NHÀ XUẤT BẢN · 2024", cx, H * 0.11, ctx.faces["sans"], W * 0.024,
          "#8a93a6", tracking=W * 0.005, upper=True)


def _vintage(c, W, H, ctx):
    _bg(c, W, H, "#e9dcc0")
    m = W * 0.09
    c.setStrokeColor(_C("#7a5c31"))
    c.setLineWidth(2.4)
    c.rect(m, m, W - 2 * m, H - 2 * m, fill=0, stroke=1)
    c.setLineWidth(0.8)
    c.rect(m + 5, m + 5, W - 2 * m - 10, H - 2 * m - 10, fill=0, stroke=1)
    cx, maxw = W / 2, W * 0.64
    _text(c, "❦", cx, H * 0.76, ctx.faces["serif"], W * 0.06, "#7a5c31")
    _text(c, ctx.kick(), cx, H * 0.68, ctx.faces["sans"], W * 0.024, "#7a5c31",
          tracking=W * 0.006, upper=True)
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.15, W * 0.07, maxw, 3)
    _draw_lines(c, lines, cx, H * 0.56, ctx.faces["serif_b"], size, size * 1.04, "#3a2c1a")
    _text(c, ctx.author, cx, H * 0.24, ctx.faces["serif"], W * 0.046, "#5a4426")
    _text(c, "— EST. 2024 —", cx, H * 0.18, ctx.faces["sans"], W * 0.022, "#8a6d3e",
          tracking=W * 0.006, upper=True)


def _emblem(c, W, H, ctx):
    _radial(c, W, H, W / 2, H, H * 0.95, "#123f39", "#0c2a26")
    cx = W / 2
    c.setStrokeColor(_C("#c9a24b"))
    c.setLineWidth(1)
    c.circle(cx, H * 0.72, W * 0.11, fill=0, stroke=1)
    c.setLineWidth(0.6)
    c.circle(cx, H * 0.72, W * 0.095, fill=0, stroke=1)
    _text(c, ctx.initials, cx, H * 0.72 - W * 0.04, ctx.faces["serif_b"], W * 0.08, "#c9a24b")
    first = H * 0.4
    size, lines = _fit(c, ctx.title, ctx.faces["serif_b"], W * 0.14, W * 0.06, W * 0.74, 3)
    _kick_above(c, ctx.kick(), cx, first, size, ctx.faces["sans"], W * 0.026, "#c9a24b", W * 0.007)
    _draw_lines(c, lines, cx, first, ctx.faces["serif_b"], size, size * 1.04, "#f2ead4")
    _text(c, ctx.author, cx, H * 0.1, ctx.faces["sans"], W * 0.034, "#cbb98a",
          tracking=W * 0.004, upper=True)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CoverTemplate:
    id: str
    name: str
    category: str
    description: str
    draw: Callable


COVER_TEMPLATES: dict = {
    t.id: t for t in [
        CoverTemplate("classic", "Classic", "literary", "Serif cổ điển, căn giữa, nền kem — chuẩn văn học.", _classic),
        CoverTemplate("minimal", "Minimal", "minimal", "Tối giản, nhiều khoảng trắng, sans mảnh.", _minimal),
        CoverTemplate("bold", "Bold Type", "modern", "Chữ tựa cực lớn phủ bìa, điểm nhấn vàng.", _bold),
        CoverTemplate("noir", "Noir", "thriller", "Nền tối, vạch đỏ, chữ đậm — trinh thám/kinh dị.", _noir),
        CoverTemplate("gradient", "Gradient", "modern", "Nền gradient rực rỡ, tựa đậm căn giữa.", _gradient),
        CoverTemplate("duotone", "Duotone", "art", "Tông đôi trầm, trăng + đường chân trời, tựa dưới.", _duotone),
        CoverTemplate("geometric", "Geometric", "art", "Bauhaus: khối màu cơ bản, tựa bên trái.", _geometric),
        CoverTemplate("framed", "Framed", "literary", "Khung viền đôi thanh lịch, huy hiệu, serif.", _framed),
        CoverTemplate("colorblock", "Color Block", "modern", "Chia khối hai tông, tựa trên nền màu.", _colorblock),
        CoverTemplate("academic", "Academic", "academic", "Dải màu trên, serif căn giữa, dòng NXB.", _academic),
        CoverTemplate("vintage", "Vintage", "literary", "Giấy cũ, viền đôi, hoa văn, cảm giác in typo.", _vintage),
        CoverTemplate("emblem", "Emblem", "literary", "Sang trọng: huy hiệu vòng vàng, nền xanh rêu.", _emblem),
    ]
}


def has_template(template_id: str) -> bool:
    return template_id in COVER_TEMPLATES


def list_templates() -> list:
    return [
        {"id": t.id, "name": t.name, "category": t.category, "description": t.description}
        for t in COVER_TEMPLATES.values()
    ]


def render_cover_pdf(
    template_id: str,
    metadata,
    output_path,
    *,
    title: Optional[str] = None,
    kicker: Optional[str] = None,
) -> Path:
    """Render ``template_id`` as a single-page cover PDF at the document's page
    size. Raises ``KeyError`` for an unknown template."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    tmpl = COVER_TEMPLATES.get(template_id)
    if tmpl is None:
        raise KeyError(f"unknown cover template: {template_id!r}")

    W = float(getattr(metadata, "page_width_mm", 210.0)) * mm
    H = float(getattr(metadata, "page_height_mm", 297.0)) * mm
    ttl = (title or getattr(metadata, "title", None) or "Untitled").strip()
    author = (getattr(metadata, "author", None) or "").strip()
    lang = (getattr(metadata, "language", "") or "vi").lower()

    ctx = CoverContext(
        title=ttl, author=author, kicker=kicker, language=lang,
        faces=_faces(), initials=_initials(ttl, author),
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=(W, H))
    try:
        tmpl.draw(c, W, H, ctx)
    except Exception:
        logger.exception("cover template %r failed; drawing plain fallback", template_id)
        _classic(c, W, H, ctx)
    c.showPage()
    c.save()
    logger.info("cover rendered: template=%s -> %s", template_id, output_path)
    return output_path


def render_cover_image(
    template_id: str,
    metadata,
    output_path,
    *,
    scale: float = 2.0,
    title: Optional[str] = None,
    kicker: Optional[str] = None,
) -> Path:
    """Render ``template_id`` to a raster PNG (for DOCX/EPUB covers and previews).

    Draws the vector cover, then rasterizes page 1 with PyMuPDF at ``scale``×
    (2.0 ≈ 144 dpi). Same page aspect as the document, so it fills a page cleanly.
    """
    import tempfile

    import pymupdf as fitz  # PyMuPDF (already a dependency)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "cover.pdf"
        render_cover_pdf(template_id, metadata, pdf, title=title, kicker=kicker)
        doc = fitz.open(str(pdf))
        try:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pix.save(str(output_path))
        finally:
            doc.close()
    logger.info("cover image rendered: template=%s -> %s", template_id, output_path)
    return output_path
