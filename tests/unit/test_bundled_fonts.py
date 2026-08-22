"""The repo bundles Vietnamese-capable fonts (Noto Sans/Serif) and the PDF
adapter prefers them, so covers and PDFs render diacritics on every machine
(not just those with DejaVu/Arial installed). Regression guard for the cover
font bug where serif templates fell back to Helvetica → ▪ for ự/ủ/ạ.
"""

from pathlib import Path

import pytest

from core.rendering.pdf_adapter import (
    _BUNDLED_FONTS,
    _FONT_FAMILIES,
    _SERIF_FAMILIES,
    _ensure_fonts,
)

_REQUIRED = (
    "NotoSans-Regular.ttf",
    "NotoSans-Bold.ttf",
    "NotoSerif-Regular.ttf",
    "NotoSerif-Bold.ttf",
)


def test_bundled_font_files_present():
    for name in _REQUIRED:
        f = _BUNDLED_FONTS / name
        assert f.is_file() and f.stat().st_size > 10_000, name


def test_bundled_fonts_are_first_choice():
    # Bundled Noto must be the first candidate for both sans and serif, so it
    # wins over (or stands in for missing) system fonts everywhere.
    for family in (_FONT_FAMILIES, _SERIF_FAMILIES):
        reg = family[0][0]
        assert str(_BUNDLED_FONTS) in reg
        assert Path(reg).is_file()


def test_ensure_fonts_registers_real_unicode_faces():
    faces = _ensure_fonts()
    # A real Unicode TTF (not the Helvetica fallback that lacks Vietnamese).
    assert faces["serif"] != "Helvetica"
    assert faces["sans"] != "Helvetica"


def test_bundled_fonts_cover_vietnamese():
    pytest.importorskip("fontTools")
    from fontTools.ttLib import TTFont

    need = [0x1EF1, 0x1EE7, 0x1EA1, 0x1EA3, 0x1ED3, 0x1EC5]  # ự ủ ạ ả ồ ễ
    for name in ("NotoSans-Regular.ttf", "NotoSerif-Regular.ttf"):
        cmap = TTFont(str(_BUNDLED_FONTS / name)).getBestCmap()
        missing = [hex(c) for c in need if c not in cmap]
        assert not missing, f"{name} missing {missing}"
