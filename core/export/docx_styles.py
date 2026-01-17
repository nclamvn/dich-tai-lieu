#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DOCX Styling System - Phase 9 (Premium Output)
==============================================
Dynamic styling system supporting multiple professional themes.
Replaces static StyleApplicator with validatable ThemeConfig and StyleManager.

Themes:
- Academic Standard (Times New Roman) - Default
- Modern Sans (Arial/Roboto) - Clean, Digital-first
- Classic Serif (Garamond/Georgia) - Book/Literature
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ============================================================================
# PAGE LAYOUT CONSTANTS
# ============================================================================

PAGE_MARGINS = {
    'academic': {'top': Inches(1.0), 'bottom': Inches(1.0), 'left': Inches(1.0), 'right': Inches(1.0)},
    'book': {'top': Cm(2.0), 'bottom': Cm(2.0), 'left': Cm(2.5), 'right': Cm(1.5)}, # Mirror margins handled in builder
    'wide': {'top': Inches(1.0), 'bottom': Inches(1.0), 'left': Inches(0.75), 'right': Inches(0.75)},
    'ebook': {'top': Inches(0.8), 'bottom': Inches(0.8), 'left': Inches(1.0), 'right': Inches(1.0)},  # Balanced for digital
    'default': {'top': Inches(1.0), 'bottom': Inches(1.0), 'left': Inches(1.0), 'right': Inches(1.0)},
}

PAGE_SIZES = {
    'a4': {'width': Cm(21.0), 'height': Cm(29.7)},
    'letter': {'width': Inches(8.5), 'height': Inches(11.0)},
    '6x9': {'width': Inches(6.0), 'height': Inches(9.0)}, # Trade Paperback
}

# ============================================================================
# THEME CONFIGURATION
# ============================================================================

@dataclass
class FontConfig:
    body: str
    heading: str
    math: str
    code: str

@dataclass
class SpacingConfig:
    line_spacing: float
    para_before: int # Points
    para_after: int # Points
    heading_before: int # Points
    heading_after: int # Points

@dataclass
class ThemeConfig:
    name: str
    fonts: FontConfig
    spacing: SpacingConfig
    colors: Dict[str, RGBColor]
    font_sizes: Dict[str, int] # Points

# ============================================================================
# PRESET THEMES
# ============================================================================

# 1. ACADEMIC STANDARD (Times New Roman / Cambria Math)
THEME_ACADEMIC = ThemeConfig(
    name="academic",
    fonts=FontConfig(
        body="Times New Roman",
        heading="Times New Roman",
        math="Cambria Math",
        code="Consolas"
    ),
    spacing=SpacingConfig(
        line_spacing=1.15,
        para_before=0,
        para_after=6,
        heading_before=12,
        heading_after=6
    ),
    colors={
        'body': RGBColor(0, 0, 0),
        'heading': RGBColor(0, 0, 0),
        'accent': RGBColor(0, 0, 0), # No color in strict academic
        'theorem_bg': RGBColor(245, 245, 245), # Light Grey
        'theorem_border': RGBColor(0, 0, 0)
    },
    font_sizes={
        'body': 11,
        'h1': 14,
        'h2': 12,
        'h3': 11,
        'caption': 10
    }
)

# 2. MODERN SANS (Arial / Roboto) - Clean, approachable
THEME_MODERN = ThemeConfig(
    name="modern",
    fonts=FontConfig(
        body="Arial",
        heading="Arial",
        math="Cambria Math", # Fallback
        code="Consolas"
    ),
    spacing=SpacingConfig(
        line_spacing=1.3,
        para_before=0,
        para_after=8,
        heading_before=18,
        heading_after=8
    ),
    colors={
        'body': RGBColor(38, 38, 38), # Dark Grey
        'heading': RGBColor(0, 0, 0),
        'accent': RGBColor(0, 86, 179), # Primary Blue
        'theorem_bg': RGBColor(240, 248, 255), # Alice Blue
        'theorem_border': RGBColor(0, 86, 179)
    },
    font_sizes={
        'body': 10, # Sans fonts often read bigger
        'h1': 16,
        'h2': 13,
        'h3': 11,
        'caption': 9
    }
)

# 3. CLASSIC SERIF (Garamond / Georgia) - Book, Literature
THEME_CLASSIC = ThemeConfig(
    name="classic",
    fonts=FontConfig(
        body="Georgia",
        heading="Georgia",
        math="Cambria Math",
        code="Consolas"
    ),
    spacing=SpacingConfig(
        line_spacing=1.2,
        para_before=0,
        para_after=6,
        heading_before=16,
        heading_after=8
    ),
    colors={
        'body': RGBColor(18, 18, 18), # Near Black
        'heading': RGBColor(60, 20, 20), # Deep Dark Brown/Red
        'accent': RGBColor(128, 0, 0), # Maroon
        'theorem_bg': RGBColor(255, 250, 240), # Floral White
        'theorem_border': RGBColor(128, 0, 0)
    },
    font_sizes={
        'body': 11,
        'h1': 16,
        'h2': 14,
        'h3': 12,
        'caption': 10
    }
)

# 4. EBOOK COMMERCIAL (Optimized for digital reading)
# Professional ebook typography with proper spacing and readability
THEME_EBOOK = ThemeConfig(
    name="ebook",
    fonts=FontConfig(
        body="Georgia",  # Excellent screen readability
        heading="Arial",  # Clean sans-serif for headings
        math="Cambria Math",
        code="Consolas"
    ),
    spacing=SpacingConfig(
        line_spacing=1.5,  # Comfortable reading
        para_before=0,
        para_after=12,  # Clear paragraph separation (12pt)
        heading_before=24,  # Strong visual hierarchy
        heading_after=12
    ),
    colors={
        'body': RGBColor(30, 30, 30),  # Soft black for less eye strain
        'heading': RGBColor(0, 0, 0),  # True black for headings
        'accent': RGBColor(0, 102, 153),  # Professional blue
        'theorem_bg': RGBColor(248, 248, 248),  # Very light grey
        'theorem_border': RGBColor(200, 200, 200)
    },
    font_sizes={
        'body': 12,  # Larger for ebook readability
        'h1': 24,  # Chapter titles
        'h2': 18,  # Section headers
        'h3': 14,  # Subsections
        'caption': 10
    }
)

THEMES = {
    'academic': THEME_ACADEMIC,
    'modern': THEME_MODERN,
    'classic': THEME_CLASSIC,
    'ebook': THEME_EBOOK
}

# ============================================================================
# STYLE MANAGER
# ============================================================================

class StyleManager:
    """
    Manages application of styles based on active theme.
    Replaces static StyleApplicator methods.
    """
    
    def __init__(self, theme_name: str = 'academic'):
        self.theme = THEMES.get(theme_name, THEME_ACADEMIC)

    def apply_heading_style(self, paragraph, level: int = 1):
        """Apply H1-H3 styling based on theme."""
        # Font
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        font = run.font
        font.name = self.theme.fonts.heading
        
        # Size mapping
        size_key = f'h{level}'
        size_pt = self.theme.font_sizes.get(size_key, self.theme.font_sizes['h1'])
        font.size = Pt(size_pt)
        
        # Color & Bold
        font.bold = True
        font.color.rgb = self.theme.colors['heading']
        
        # Spacing
        paragraph.paragraph_format.space_before = Pt(self.theme.spacing.heading_before)
        paragraph.paragraph_format.space_after = Pt(self.theme.spacing.heading_after)

    def apply_body_style(self, paragraph):
        """Apply body text styling."""
        paragraph.paragraph_format.line_spacing = self.theme.spacing.line_spacing
        paragraph.paragraph_format.space_after = Pt(self.theme.spacing.para_after)
        
        for run in paragraph.runs:
            run.font.name = self.theme.fonts.body
            run.font.size = Pt(self.theme.font_sizes['body'])
            run.font.color.rgb = self.theme.colors['body']

    def apply_theorem_box(self, paragraph, box_type: str = 'theorem'):
        """Apply premium box styling (Border + Shading)."""
        # Base body style first
        self.apply_body_style(paragraph)
        
        # Indent content slightly
        paragraph.paragraph_format.left_indent = Pt(12)
        paragraph.paragraph_format.right_indent = Pt(12)
        
        # Add Border & Shading (Low-level XML)
        self._add_border_and_shading(
            paragraph, 
            bg_color=self.theme.colors['theorem_bg'],
            border_color=self.theme.colors['theorem_border']
        )

    def _add_border_and_shading(self, paragraph, bg_color: RGBColor, border_color: RGBColor):
        """Inject XML for borders and shading."""
        pPr = paragraph._element.get_or_add_pPr()
        
        # 1. Shading (Background)
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        # Convert RGB tuple to hex string
        hex_bg = f'{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}'
        shd.set(qn('w:fill'), hex_bg)
        pPr.append(shd)
        
        # 2. Borders
        pbdr = OxmlElement('w:pBdr')
        
        hex_border = f'{border_color[0]:02x}{border_color[1]:02x}{border_color[2]:02x}'
        
        for side in ['top', 'left', 'bottom', 'right']:
            bd = OxmlElement(f'w:{side}')
            bd.set(qn('w:val'), 'single')
            bd.set(qn('w:sz'), '4') # 1/2 pt
            bd.set(qn('w:space'), '6') # Padding between border and text
            bd.set(qn('w:color'), hex_border)
            pbdr.append(bd)
            
        pPr.append(pbdr)

# Constants
THEOREM_TYPES = [
    'theorem', 'lemma', 'coronavirus', 'proposition', 'definition', 'example', 'remark', 'note'
]

HEADING_LEVELS = {
    'chapter': 1,
    'section': 2,
    'subsection': 3,
    'subsubsection': 4,
}

# Re-export for compatibility
DEFAULT_OPTIONS = {
    'page_size': 'a4',
    'margin_style': 'academic',
    'theme': 'academic'
}
