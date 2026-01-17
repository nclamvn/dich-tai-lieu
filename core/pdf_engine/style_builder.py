"""
Font management and style building utilities for PDF rendering.

This module handles:
- Font file discovery and registration
- ReportLab ParagraphStyle creation from template specs
- Style caching for performance
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from functools import lru_cache

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from .templates.base import PdfTemplate, FontSpec, ParagraphSpec


logger = logging.getLogger(__name__)


class FontManager:
    """
    Manages font registration for ReportLab.

    Handles:
    - Font file discovery across multiple paths
    - TTF font registration with ReportLab
    - Font family mapping (regular, bold, italic, bold_italic)
    """

    # Default search paths for fonts
    DEFAULT_SEARCH_PATHS = [
        # System paths (Linux)
        '/usr/share/fonts/truetype/dejavu/',
        '/usr/share/fonts/TTF/',
        '/usr/local/share/fonts/',

        # User paths
        os.path.expanduser('~/.fonts/'),
        os.path.expanduser('~/.local/share/fonts/'),

        # macOS paths
        '/Library/Fonts/',
        '/System/Library/Fonts/',
        os.path.expanduser('~/Library/Fonts/'),

        # Project paths
        './fonts/',
        './assets/fonts/',
        str(Path(__file__).parent.parent.parent / 'assets' / 'fonts'),
    ]

    # DejaVu font files - these have excellent Vietnamese support
    DEJAVU_FONTS = {
        'DejaVuSerif': 'DejaVuSerif.ttf',
        'DejaVuSerif-Bold': 'DejaVuSerif-Bold.ttf',
        'DejaVuSerif-Italic': 'DejaVuSerif-Italic.ttf',
        'DejaVuSerif-BoldItalic': 'DejaVuSerif-BoldItalic.ttf',
        'DejaVuSans': 'DejaVuSans.ttf',
        'DejaVuSans-Bold': 'DejaVuSans-Bold.ttf',
        'DejaVuSans-Oblique': 'DejaVuSans-Oblique.ttf',
        'DejaVuSans-BoldOblique': 'DejaVuSans-BoldOblique.ttf',
        'DejaVuSansMono': 'DejaVuSansMono.ttf',
        'DejaVuSansMono-Bold': 'DejaVuSansMono-Bold.ttf',
    }

    def __init__(self, additional_paths: Optional[List[str]] = None):
        """
        Initialize FontManager.

        Args:
            additional_paths: Extra paths to search for fonts
        """
        self.search_paths = list(self.DEFAULT_SEARCH_PATHS)
        if additional_paths:
            self.search_paths.extend(additional_paths)

        self._registered_fonts: Dict[str, str] = {}
        self._font_cache: Dict[str, str] = {}

    def find_font_file(self, filename: str) -> Optional[str]:
        """
        Find a font file in search paths.

        Args:
            filename: Font filename (e.g., 'DejaVuSerif.ttf')

        Returns:
            Full path to font file, or None if not found
        """
        # Check cache first
        if filename in self._font_cache:
            return self._font_cache[filename]

        for search_path in self.search_paths:
            path = Path(search_path) / filename
            if path.exists():
                self._font_cache[filename] = str(path)
                return str(path)

        logger.warning(f"Font file not found: {filename}")
        return None

    def register_font(self, font_name: str, font_file: str) -> bool:
        """
        Register a single font with ReportLab.

        Args:
            font_name: Name to register (e.g., 'DejaVuSerif')
            font_file: Font filename (e.g., 'DejaVuSerif.ttf')

        Returns:
            True if registration successful
        """
        if font_name in self._registered_fonts:
            return True

        font_path = self.find_font_file(font_file)
        if not font_path:
            logger.error(f"Cannot register font {font_name}: file not found")
            return False

        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            self._registered_fonts[font_name] = font_path
            logger.debug(f"Registered font: {font_name} from {font_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to register font {font_name}: {e}")
            return False

    def register_template_fonts(self, template: PdfTemplate) -> bool:
        """
        Register all fonts required by a template.

        Args:
            template: PDF template instance

        Returns:
            True if all fonts registered successfully
        """
        fonts = template.get_fonts()
        success = True

        # Register main font variants
        font_mapping = {
            'regular': template.SERIF if hasattr(template, 'SERIF') else template.SANS,
            'bold': f"{template.SERIF if hasattr(template, 'SERIF') else template.SANS}-Bold",
            'italic': f"{template.SERIF if hasattr(template, 'SERIF') else template.SANS}-Italic",
            'bold_italic': f"{template.SERIF if hasattr(template, 'SERIF') else template.SANS}-BoldItalic",
        }

        for variant, font_name in font_mapping.items():
            if variant in fonts:
                if not self.register_font(font_name, fonts[variant]):
                    success = False

        # Register mono font if present
        if 'mono' in fonts:
            mono_name = template.MONO if hasattr(template, 'MONO') else 'DejaVuSansMono'
            if not self.register_font(mono_name, fonts['mono']):
                success = False

        return success

    def register_dejavu_fonts(self) -> bool:
        """
        Register all DejaVu fonts for Vietnamese support.

        Returns:
            True if all fonts registered successfully
        """
        success = True
        for font_name, font_file in self.DEJAVU_FONTS.items():
            if not self.register_font(font_name, font_file):
                success = False

        # If fonts not found, register fallback mappings
        if not success:
            logger.warning("DejaVu fonts not found, using fallback fonts")
            self._register_fallback_fonts()

        return success

    def _register_fallback_fonts(self):
        """Register fallback font mappings for systems without DejaVu."""
        from reportlab.pdfbase.pdfmetrics import registerFontFamily

        # Standard fonts are always available in ReportLab
        # Map DejaVu names to standard PostScript fonts
        self._fallback_mapping = {
            'DejaVuSerif': 'Times-Roman',
            'DejaVuSerif-Bold': 'Times-Bold',
            'DejaVuSerif-Italic': 'Times-Italic',
            'DejaVuSerif-BoldItalic': 'Times-BoldItalic',
            'DejaVuSans': 'Helvetica',
            'DejaVuSans-Bold': 'Helvetica-Bold',
            'DejaVuSans-Oblique': 'Helvetica-Oblique',
            'DejaVuSans-BoldOblique': 'Helvetica-BoldOblique',
            'DejaVuSansMono': 'Courier',
            'DejaVuSansMono-Bold': 'Courier-Bold',
        }
        self._use_fallback = True

    def get_font_name(self, requested_name: str) -> str:
        """Get actual font name (may be fallback if original not available)."""
        if hasattr(self, '_use_fallback') and self._use_fallback:
            return self._fallback_mapping.get(requested_name, requested_name)
        return requested_name

    def get_registered_fonts(self) -> Dict[str, str]:
        """Get dict of registered font names to paths."""
        return dict(self._registered_fonts)


class StyleBuilder:
    """
    Builds ReportLab ParagraphStyles from template specifications.

    Converts ParagraphSpec dataclasses to ReportLab-compatible styles.
    """

    def __init__(self, template: PdfTemplate, font_manager: Optional[FontManager] = None):
        """
        Initialize StyleBuilder with a template.

        Args:
            template: PDF template to build styles from
            font_manager: Optional FontManager for font resolution
        """
        self.template = template
        self.font_manager = font_manager
        self._styles: Dict[str, ParagraphStyle] = {}
        self._base_stylesheet = getSampleStyleSheet()

    def _resolve_font_name(self, font_name: str) -> str:
        """Resolve font name through font manager if available."""
        if self.font_manager:
            return self.font_manager.get_font_name(font_name)
        return font_name

    def build_paragraph_style(
        self,
        name: str,
        spec: ParagraphSpec
    ) -> ParagraphStyle:
        """
        Build a ReportLab ParagraphStyle from a ParagraphSpec.

        Args:
            name: Style name
            spec: Paragraph specification

        Returns:
            ReportLab ParagraphStyle
        """
        font = spec.font

        # Get font name based on bold/italic, then resolve through font manager
        font_name = self._resolve_font_name(font.get_font_name())

        style = ParagraphStyle(
            name=name,
            fontName=font_name,
            fontSize=font.size,
            leading=font.leading,
            textColor=font.color,
            alignment=spec.alignment,
            spaceBefore=spec.space_before,
            spaceAfter=spec.space_after,
            firstLineIndent=spec.first_line_indent,
            leftIndent=spec.left_indent,
            rightIndent=spec.right_indent,
            allowWidows=spec.allow_widows,
            allowOrphans=spec.allow_orphans,
        )

        return style

    def build_all_styles(self) -> Dict[str, ParagraphStyle]:
        """
        Build all styles defined in the template.

        Returns:
            Dict mapping style names to ParagraphStyles
        """
        if self._styles:
            return self._styles

        specs = self.template.get_styles()

        for name, spec in specs.items():
            self._styles[name] = self.build_paragraph_style(name, spec)

        return self._styles

    def get_style(self, name: str) -> ParagraphStyle:
        """
        Get a specific style by name.

        Args:
            name: Style name (e.g., 'body', 'heading_1')

        Returns:
            ParagraphStyle for the given name

        Raises:
            KeyError: If style not found
        """
        if not self._styles:
            self.build_all_styles()

        if name not in self._styles:
            # Fall back to body style
            logger.warning(f"Style '{name}' not found, using 'body'")
            return self._styles.get('body', self._base_stylesheet['Normal'])

        return self._styles[name]

    def get_header_footer_style(self) -> ParagraphStyle:
        """
        Get style for header/footer text.

        Returns:
            ParagraphStyle for headers/footers
        """
        hf_spec = self.template.get_header_footer()
        font = hf_spec.font

        return ParagraphStyle(
            name='header_footer',
            fontName=self._resolve_font_name(font.get_font_name()),
            fontSize=font.size,
            leading=font.leading,
            textColor=font.color,
            alignment=TA_CENTER,
        )


def create_style_builder(template_name: str) -> Tuple[FontManager, StyleBuilder]:
    """
    Factory function to create FontManager and StyleBuilder for a template.

    Args:
        template_name: Template name ('ebook', 'academic', 'business')

    Returns:
        Tuple of (FontManager, StyleBuilder)
    """
    from .templates import create_pdf_template

    template = create_pdf_template(template_name)

    # Create and initialize font manager
    font_manager = FontManager()
    font_manager.register_dejavu_fonts()
    font_manager.register_template_fonts(template)

    # Create style builder
    style_builder = StyleBuilder(template)
    style_builder.build_all_styles()

    return font_manager, style_builder
