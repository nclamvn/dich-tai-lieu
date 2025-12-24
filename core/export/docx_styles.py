#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DOCX Styling System - Phase 2.0.5 + 1.4 Consolidation
========================================================
Centralized styling definitions for all DOCX exporters.

Contains:
- Page layout constants (margins, sizes)
- Font and color definitions
- Spacing configurations
- Theorem/proof/equation styles
- Default export options
"""

from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ============================================================================
# PAGE LAYOUT CONSTANTS
# ============================================================================

PAGE_MARGINS = {
    'academic': {
        'top': Inches(1.0),
        'bottom': Inches(1.0),
        'left': Inches(1.0),
        'right': Inches(1.0),
    },
    'thesis': {
        'top': Inches(1.0),
        'bottom': Inches(1.0),
        'left': Inches(1.5),  # Extra for binding
        'right': Inches(1.0),
    },
    'manuscript': {
        'top': Inches(1.25),
        'bottom': Inches(1.25),
        'left': Inches(1.25),
        'right': Inches(1.25),
    },
    'book': {
        'top': Cm(2.5),
        'bottom': Cm(2.5),
        'left': Cm(3.0),
        'right': Cm(2.0),
    },
    'default': {
        'top': Inches(1.0),
        'bottom': Inches(1.0),
        'left': Inches(1.0),
        'right': Inches(1.0),
    },
}

PAGE_SIZES = {
    'a4': {
        'width': Cm(21.0),
        'height': Cm(29.7),
    },
    'letter': {
        'width': Inches(8.5),
        'height': Inches(11.0),
    },
    'legal': {
        'width': Inches(8.5),
        'height': Inches(14.0),
    },
}

DEFAULT_OPTIONS = {
    # Document properties
    'page_size': 'a4',
    'margin_style': 'academic',

    # Typography
    'font_name': 'Times New Roman',
    'font_size': 11,
    'line_spacing': 1.15,

    # Paragraph spacing
    'paragraph_before': 6,
    'paragraph_after': 6,

    # Language
    'language': 'vi',  # Vietnamese default

    # Features
    'include_toc': False,
    'include_page_numbers': True,
    'include_header': False,
    'include_footer': False,
}


class AcademicStyles:
    """Centralized academic document styling definitions"""

    # ========== COLOR PALETTE ==========

    COLORS = {
        # Theorem box backgrounds (light, subtle)
        'theorem_bg': RGBColor(240, 248, 255),      # Alice blue
        'lemma_bg': RGBColor(240, 255, 240),        # Honeydew (light green)
        'corollary_bg': RGBColor(255, 250, 205),    # Lemon chiffon (light yellow)
        'definition_bg': RGBColor(255, 255, 255),   # White
        'proposition_bg': RGBColor(255, 245, 238),  # Seashell (light peach)
        'example_bg': RGBColor(245, 245, 245),      # White smoke (light gray)

        # Border colors (matching backgrounds, darker)
        'theorem_border': RGBColor(70, 130, 180),   # Steel blue
        'lemma_border': RGBColor(60, 179, 113),     # Medium sea green
        'corollary_border': RGBColor(255, 215, 0),  # Gold
        'definition_border': RGBColor(105, 105, 105),  # Dim gray
        'proposition_border': RGBColor(255, 140, 0),   # Dark orange
        'example_border': RGBColor(169, 169, 169),     # Dark gray

        # Text colors
        'heading_text': RGBColor(0, 0, 0),          # Black
        'body_text': RGBColor(0, 0, 0),             # Black
        'proof_text': RGBColor(50, 50, 50),         # Dark gray
    }

    # ========== FONT DEFINITIONS ==========

    FONTS = {
        'body': 'Cambria',              # Serif, excellent for math
        'heading': 'Cambria',           # Same as body for consistency
        'math': 'Cambria Math',         # Best for OMML
        'code': 'Consolas',             # Monospace
        'fallback': 'Times New Roman',  # Universal fallback
    }

    FONT_SIZES = {
        'body': Pt(11),
        'heading_1': Pt(14),
        'heading_2': Pt(12),
        'heading_3': Pt(11),
        'theorem_title': Pt(11),
        'equation': Pt(11),
        'caption': Pt(10),
        'footnote': Pt(9),
    }

    # ========== SPACING DEFINITIONS ==========

    SPACING = {
        # Line spacing
        'line_spacing': 1.15,  # Academic standard

        # Paragraph spacing
        'paragraph_before': Pt(6),
        'paragraph_after': Pt(6),

        # Section spacing
        'section_before': Pt(18),
        'section_after': Pt(12),

        # Theorem box spacing
        'theorem_before': Pt(12),
        'theorem_after': Pt(12),

        # Equation spacing
        'equation_before': Pt(12),
        'equation_after': Pt(12),

        # Proof spacing
        'proof_before': Pt(6),
        'proof_after': Pt(12),
        'proof_indent': Inches(0.3),  # Left indent for proof body
    }

    # ========== BORDER DEFINITIONS ==========

    BORDERS = {
        'theorem': {
            'width': Pt(0.75),
            'color_key': 'theorem_border',
            'style': 'single',
        },
        'lemma': {
            'width': Pt(0.75),
            'color_key': 'lemma_border',
            'style': 'single',
        },
        'corollary': {
            'width': Pt(0.75),
            'color_key': 'corollary_border',
            'style': 'single',
        },
        'definition': {
            'width': Pt(1.0),
            'color_key': 'definition_border',
            'style': 'single',
        },
        'proposition': {
            'width': Pt(0.75),
            'color_key': 'proposition_border',
            'style': 'single',
        },
        'example': {
            'width': Pt(0.5),
            'color_key': 'example_border',
            'style': 'dashed',
        },
    }

    # ========== PADDING DEFINITIONS ==========

    PADDING = {
        'theorem': {
            'top': Pt(8),
            'bottom': Pt(8),
            'left': Pt(12),
            'right': Pt(12),
        },
        'proof': {
            'left': Inches(0.3),  # Indent from left
        },
    }

    # ========== THEOREM BOX STYLES ==========

    @classmethod
    def get_theorem_style(cls, box_type='theorem'):
        """
        Get complete style configuration for a theorem box type

        Args:
            box_type: 'theorem', 'lemma', 'corollary', 'definition', 'proposition', 'example'

        Returns:
            dict: Complete style configuration
        """
        bg_key = f'{box_type}_bg'
        border_key = box_type

        return {
            'background_color': cls.COLORS.get(bg_key, cls.COLORS['theorem_bg']),
            'border': cls.BORDERS.get(border_key, cls.BORDERS['theorem']),
            'border_color': cls.COLORS.get(
                cls.BORDERS.get(border_key, cls.BORDERS['theorem'])['color_key'],
                cls.COLORS['theorem_border']
            ),
            'padding': cls.PADDING['theorem'],
            'font': cls.FONTS['body'],
            'font_size': cls.FONT_SIZES['theorem_title'],
            'spacing_before': cls.SPACING['theorem_before'],
            'spacing_after': cls.SPACING['theorem_after'],
        }

    @classmethod
    def get_proof_style(cls):
        """Get style configuration for proof blocks"""
        return {
            'indent_left': cls.SPACING['proof_indent'],
            'font': cls.FONTS['body'],
            'font_size': cls.FONT_SIZES['body'],
            'text_color': cls.COLORS['proof_text'],
            'spacing_before': cls.SPACING['proof_before'],
            'spacing_after': cls.SPACING['proof_after'],
            'line_spacing': cls.SPACING['line_spacing'],
        }

    @classmethod
    def get_equation_style(cls, centered=True, numbered=False):
        """Get style configuration for equations"""
        return {
            'alignment': WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT,
            'font': cls.FONTS['math'],
            'font_size': cls.FONT_SIZES['equation'],
            'spacing_before': cls.SPACING['equation_before'],
            'spacing_after': cls.SPACING['equation_after'],
            'numbered': numbered,
        }

    @classmethod
    def get_heading_style(cls, level=1):
        """Get style configuration for headings (H1, H2, H3)"""
        size_map = {
            1: cls.FONT_SIZES['heading_1'],
            2: cls.FONT_SIZES['heading_2'],
            3: cls.FONT_SIZES['heading_3'],
        }

        return {
            'font': cls.FONTS['heading'],
            'font_size': size_map.get(level, cls.FONT_SIZES['heading_1']),
            'bold': True,
            'color': cls.COLORS['heading_text'],
            'spacing_before': cls.SPACING['section_before'],
            'spacing_after': cls.SPACING['section_after'],
        }

    @classmethod
    def get_body_style(cls):
        """Get style configuration for body text"""
        return {
            'font': cls.FONTS['body'],
            'font_size': cls.FONT_SIZES['body'],
            'color': cls.COLORS['body_text'],
            'line_spacing': cls.SPACING['line_spacing'],
            'spacing_before': cls.SPACING['paragraph_before'],
            'spacing_after': cls.SPACING['paragraph_after'],
        }


class StyleApplicator:
    """Helper class to apply styles to DOCX paragraphs"""

    @staticmethod
    def apply_theorem_box(paragraph, box_type='theorem'):
        """
        Apply theorem box styling to a paragraph

        Args:
            paragraph: python-docx paragraph object
            box_type: Type of theorem box
        """
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        style = AcademicStyles.get_theorem_style(box_type)

        # Font and size
        paragraph.style.font.name = style['font']
        paragraph.style.font.size = style['font_size']

        # Spacing
        paragraph.paragraph_format.space_before = style['spacing_before']
        paragraph.paragraph_format.space_after = style['spacing_after']

        # Background shading - Use OxmlElement for low-level XML manipulation
        pPr = paragraph._element.get_or_add_pPr()
        shading_elm = OxmlElement('w:shd')
        bg_color = style['background_color']
        # RGBColor is a tuple subclass - access components by index
        shading_elm.set(qn('w:fill'),
                       f'{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}'.upper())
        pPr.append(shading_elm)

        # Borders - Use OxmlElement for low-level XML manipulation
        border_config = style['border']
        border_color = style['border_color']

        # Create pBdr (paragraph borders) element
        pBdr = OxmlElement('w:pBdr')

        # Add borders for all four sides
        for border_side in ['top', 'left', 'bottom', 'right']:
            border_elm = OxmlElement(f'w:{border_side}')
            border_elm.set(qn('w:val'), border_config['style'])
            border_elm.set(qn('w:sz'), str(int(border_config['width'].pt * 8)))  # 1/8 pt units
            # RGBColor is a tuple subclass - access components by index
            border_elm.set(qn('w:color'),
                          f'{border_color[0]:02x}{border_color[1]:02x}{border_color[2]:02x}'.upper())
            border_elm.set(qn('w:space'), '4')  # Border spacing
            pBdr.append(border_elm)

        pPr.append(pBdr)

    @staticmethod
    def apply_proof_style(paragraph):
        """Apply proof block styling to a paragraph"""
        style = AcademicStyles.get_proof_style()

        # Font and size
        paragraph.style.font.name = style['font']
        paragraph.style.font.size = style['font_size']

        # Color
        paragraph.style.font.color.rgb = style['text_color']

        # Indentation
        paragraph.paragraph_format.left_indent = style['indent_left']

        # Spacing
        paragraph.paragraph_format.space_before = style['spacing_before']
        paragraph.paragraph_format.space_after = style['spacing_after']
        paragraph.paragraph_format.line_spacing = style['line_spacing']

    @staticmethod
    def apply_equation_style(paragraph, centered=True, numbered=False):
        """Apply equation styling to a paragraph"""
        style = AcademicStyles.get_equation_style(centered, numbered)

        # Alignment
        paragraph.alignment = style['alignment']

        # Font
        paragraph.style.font.name = style['font']
        paragraph.style.font.size = style['font_size']

        # Spacing
        paragraph.paragraph_format.space_before = style['spacing_before']
        paragraph.paragraph_format.space_after = style['spacing_after']

    @staticmethod
    def apply_heading_style(paragraph, level=1):
        """Apply heading styling to a paragraph"""
        style = AcademicStyles.get_heading_style(level)

        # Font
        paragraph.style.font.name = style['font']
        paragraph.style.font.size = style['font_size']
        paragraph.style.font.bold = style['bold']
        paragraph.style.font.color.rgb = style['color']

        # Spacing
        paragraph.paragraph_format.space_before = style['spacing_before']
        paragraph.paragraph_format.space_after = style['spacing_after']

    @staticmethod
    def apply_body_style(paragraph):
        """Apply body text styling to a paragraph"""
        style = AcademicStyles.get_body_style()

        # Font
        paragraph.style.font.name = style['font']
        paragraph.style.font.size = style['font_size']
        paragraph.style.font.color.rgb = style['color']

        # Spacing
        paragraph.paragraph_format.line_spacing = style['line_spacing']
        paragraph.paragraph_format.space_before = style['spacing_before']
        paragraph.paragraph_format.space_after = style['spacing_after']


# Quick access constants
THEOREM_TYPES = ['theorem', 'lemma', 'corollary', 'definition', 'proposition', 'example']
HEADING_LEVELS = [1, 2, 3]

# Convenience exports
__all__ = [
    # Page layout
    'PAGE_MARGINS',
    'PAGE_SIZES',
    'DEFAULT_OPTIONS',
    # Classes
    'AcademicStyles',
    'StyleApplicator',
    # Constants
    'THEOREM_TYPES',
    'HEADING_LEVELS',
]
