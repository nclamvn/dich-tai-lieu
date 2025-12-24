#!/usr/bin/env python3
"""
Create DOCX Templates

Generates pre-configured DOCX templates for each document type.
These templates have all styles pre-defined, reducing runtime overhead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE

TEMPLATES_DIR = Path(__file__).parent.parent / "core" / "layout" / "templates"


def create_base_styles(doc: Document, template_type: str = "book"):
    """Create all APS styles in the document"""
    styles = doc.styles

    # Style configurations by template type
    configs = {
        "book": {
            "font_body": "Times New Roman",
            "font_heading": "Georgia",
            "size_body": 11,
            "line_spacing": 1.5,
        },
        "report": {
            "font_body": "Arial",
            "font_heading": "Arial",
            "size_body": 11,
            "line_spacing": 1.15,
        },
        "academic": {
            "font_body": "Times New Roman",
            "font_heading": "Times New Roman",
            "size_body": 12,
            "line_spacing": 2.0,
        },
        "default": {
            "font_body": "Arial",
            "font_heading": "Arial",
            "size_body": 11,
            "line_spacing": 1.15,
        },
    }

    cfg = configs.get(template_type, configs["default"])

    # Define all APS styles
    style_defs = [
        {
            "name": "APS_Title",
            "font": cfg["font_heading"],
            "size": 24,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.CENTER,
            "space_before": 0,
            "space_after": 24,
        },
        {
            "name": "APS_Subtitle",
            "font": cfg["font_body"],
            "size": 14,
            "bold": False,
            "italic": True,
            "align": WD_ALIGN_PARAGRAPH.CENTER,
            "space_before": 0,
            "space_after": 12,
            "color": RGBColor(100, 100, 100),
        },
        {
            "name": "APS_Chapter",
            "font": cfg["font_heading"],
            "size": 18,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 36,
            "space_after": 18,
        },
        {
            "name": "APS_Section",
            "font": cfg["font_heading"],
            "size": 14,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 24,
            "space_after": 12,
        },
        {
            "name": "APS_Heading1",
            "font": cfg["font_heading"],
            "size": 16,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 18,
            "space_after": 6,
        },
        {
            "name": "APS_Heading2",
            "font": cfg["font_heading"],
            "size": 14,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 12,
            "space_after": 6,
        },
        {
            "name": "APS_Heading3",
            "font": cfg["font_heading"],
            "size": 12,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 10,
            "space_after": 4,
        },
        {
            "name": "APS_Paragraph",
            "font": cfg["font_body"],
            "size": cfg["size_body"],
            "bold": False,
            "align": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "space_before": 0,
            "space_after": 8,
            "first_line_indent": 0.5 if template_type == "book" else 0,
            "line_spacing": cfg["line_spacing"],
        },
        {
            "name": "APS_Quote",
            "font": cfg["font_body"],
            "size": cfg["size_body"],
            "bold": False,
            "italic": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 12,
            "space_after": 12,
            "left_indent": 0.5,
            "right_indent": 0.5,
        },
        {
            "name": "APS_Code",
            "font": "Courier New",
            "size": 10,
            "bold": False,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 6,
            "space_after": 6,
            "left_indent": 0.25,
        },
        {
            "name": "APS_List",
            "font": cfg["font_body"],
            "size": cfg["size_body"],
            "bold": False,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 0,
            "space_after": 4,
            "left_indent": 0.25,
        },
        {
            "name": "APS_Footnote",
            "font": cfg["font_body"],
            "size": 9,
            "bold": False,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 0,
            "space_after": 2,
        },
        {
            "name": "APS_TOC1",
            "font": cfg["font_heading"],
            "size": 12,
            "bold": True,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 6,
            "space_after": 3,
        },
        {
            "name": "APS_TOC2",
            "font": cfg["font_body"],
            "size": 11,
            "bold": False,
            "align": WD_ALIGN_PARAGRAPH.LEFT,
            "space_before": 0,
            "space_after": 2,
            "left_indent": 0.25,
        },
    ]

    for sd in style_defs:
        try:
            # Check if style exists
            style = styles[sd["name"]]
        except KeyError:
            # Create new style
            style = styles.add_style(sd["name"], WD_STYLE_TYPE.PARAGRAPH)

        # Configure font
        font = style.font
        font.name = sd["font"]
        font.size = Pt(sd["size"])
        font.bold = sd.get("bold", False)
        font.italic = sd.get("italic", False)

        if "color" in sd:
            font.color.rgb = sd["color"]

        # Configure paragraph format
        pf = style.paragraph_format
        pf.alignment = sd.get("align", WD_ALIGN_PARAGRAPH.LEFT)
        pf.space_before = Pt(sd.get("space_before", 0))
        pf.space_after = Pt(sd.get("space_after", 0))

        if "left_indent" in sd:
            pf.left_indent = Inches(sd["left_indent"])
        if "right_indent" in sd:
            pf.right_indent = Inches(sd["right_indent"])
        if "first_line_indent" in sd:
            pf.first_line_indent = Inches(sd["first_line_indent"])
        if "line_spacing" in sd:
            pf.line_spacing = sd["line_spacing"]

    return doc


def set_page_setup(doc: Document, template_type: str = "book", page_size: str = "A4"):
    """Configure page setup"""
    section = doc.sections[0]

    # Page sizes
    sizes = {
        "A4": (Cm(21), Cm(29.7)),
        "A5": (Cm(14.8), Cm(21)),
        "letter": (Inches(8.5), Inches(11)),
        "B5": (Cm(17.6), Cm(25)),
    }

    width, height = sizes.get(page_size, sizes["A4"])
    section.page_width = width
    section.page_height = height

    # Margins by template
    margins = {
        "book": {"top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.0},
        "report": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
        "academic": {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54},
        "default": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
    }

    m = margins.get(template_type, margins["default"])
    section.top_margin = Cm(m["top"])
    section.bottom_margin = Cm(m["bottom"])
    section.left_margin = Cm(m["left"])
    section.right_margin = Cm(m["right"])

    return doc


def create_template(template_type: str = "book", page_size: str = "A4") -> Path:
    """Create a complete template"""
    doc = Document()

    # Set page setup
    set_page_setup(doc, template_type, page_size)

    # Create all styles
    create_base_styles(doc, template_type)

    # Add placeholder paragraph (will be removed when using template)
    doc.add_paragraph("{{APS_CONTENT_START}}", style="APS_Paragraph")

    # Save template
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEMPLATES_DIR / f"base_{template_type}.docx"
    doc.save(str(output_path))

    print(f"  Created: {output_path}")
    return output_path


def create_all_templates():
    """Create all templates"""
    print("\n" + "="*60)
    print("       CREATING DOCX TEMPLATES")
    print("="*60 + "\n")

    templates = [
        ("book", "A4"),
        ("report", "A4"),
        ("academic", "letter"),
        ("default", "A4"),
    ]

    for template_type, page_size in templates:
        create_template(template_type, page_size)

    print(f"\n All templates created in: {TEMPLATES_DIR}")


if __name__ == "__main__":
    create_all_templates()
