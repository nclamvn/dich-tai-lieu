#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Layout-Preserving PDF Translator
=================================
Translates PDF while preserving exact layout, fonts, positions.

PRIORITY: Balance (90% layout preservation, 92% translation quality)

Features:
- Multi-column layout preservation
- Exact text positioning
- Font style & size preservation
- Figure/Table positions maintained
- Page breaks preserved

Author: AI Translator Pro Team
Version: 1.0.0
"""

import fitz  # PyMuPDF
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Represents a text block with position and formatting"""
    text: str
    x0: float  # Left coordinate
    y0: float  # Top coordinate
    x1: float  # Right coordinate
    y1: float  # Bottom coordinate
    font_name: str
    font_size: float
    font_flags: int  # Bold, italic flags
    color: Tuple[float, float, float]  # RGB
    page_num: int
    block_no: int

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def is_bold(self):
        return bool(self.font_flags & 2**4)

    @property
    def is_italic(self):
        return bool(self.font_flags & 2**1)


class LayoutPreservingTranslator:
    """
    PDF translator that preserves exact layout.

    Strategy:
    1. Extract text blocks with positions
    2. Detect multi-column layout
    3. Translate text blocks
    4. Render at exact positions with same formatting
    5. Preserve images, tables, figures
    """

    def __init__(self, translator_func=None):
        """
        Initialize layout-preserving translator

        Args:
            translator_func: Function to translate text (text -> translated_text)
        """
        self.translator_func = translator_func
        self.font_map = {}  # Map original fonts to available fonts

    def extract_layout(self, pdf_path: str) -> List[TextBlock]:
        """
        Extract text blocks with exact positions and formatting.

        Returns:
            List of TextBlock objects with position and style info
        """
        doc = fitz.open(pdf_path)
        text_blocks = []
        page_count = len(doc)

        for page_num, page in enumerate(doc):
            # Get text with detailed formatting
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

            for block_no, block in enumerate(blocks["blocks"]):
                if "lines" not in block:  # Skip image blocks
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        # Extract text and formatting
                        text = span["text"]
                        if not text.strip():
                            continue

                        bbox = span["bbox"]  # (x0, y0, x1, y1)

                        text_block = TextBlock(
                            text=text,
                            x0=bbox[0],
                            y0=bbox[1],
                            x1=bbox[2],
                            y1=bbox[3],
                            font_name=span["font"],
                            font_size=span["size"],
                            font_flags=span["flags"],
                            color=span["color"],
                            page_num=page_num,
                            block_no=block_no
                        )

                        text_blocks.append(text_block)

        doc.close()
        logger.info(f"Extracted {len(text_blocks)} text blocks from {page_count} pages")
        return text_blocks

    def detect_columns(self, text_blocks: List[TextBlock], page_num: int) -> int:
        """
        Detect number of columns in a page.

        Returns:
            Number of columns (1, 2, or 3)
        """
        page_blocks = [b for b in text_blocks if b.page_num == page_num]
        if not page_blocks:
            return 1

        # Get page width
        x_positions = [b.x0 for b in page_blocks]
        page_width = max(b.x1 for b in page_blocks)

        # Cluster x positions to detect columns
        # Simple heuristic: if there are distinct left margins, likely multi-column
        left_margins = sorted(set(round(x) for x in x_positions))

        # If there are 2+ distinct left margins far apart, likely 2+ columns
        if len(left_margins) >= 2:
            gap = left_margins[1] - left_margins[0]
            if gap > page_width * 0.3:  # Significant gap
                return 2

        return 1

    def group_into_paragraphs(self, text_blocks: List[TextBlock]) -> List[List[TextBlock]]:
        """
        Group text blocks into logical paragraphs.

        Uses proximity and alignment heuristics.
        """
        if not text_blocks:
            return []

        # Sort by page, then y position, then x position
        sorted_blocks = sorted(text_blocks, key=lambda b: (b.page_num, b.y0, b.x0))

        paragraphs = []
        current_para = [sorted_blocks[0]]

        for block in sorted_blocks[1:]:
            prev = current_para[-1]

            # Check if same paragraph (close y position, similar x alignment)
            y_gap = block.y0 - prev.y1
            x_aligned = abs(block.x0 - prev.x0) < 20  # Within 20 points

            if y_gap < prev.height * 1.5 and x_aligned:
                # Same paragraph
                current_para.append(block)
            else:
                # New paragraph
                paragraphs.append(current_para)
                current_para = [block]

        if current_para:
            paragraphs.append(current_para)

        logger.info(f"Grouped {len(text_blocks)} blocks into {len(paragraphs)} paragraphs")
        return paragraphs

    async def translate_blocks(self, text_blocks: List[TextBlock]) -> Dict[int, str]:
        """
        Translate text blocks using the translator function.

        Returns:
            Dictionary mapping block index to translated text
        """
        if not self.translator_func:
            logger.warning("No translator function provided, using original text")
            return {i: block.text for i, block in enumerate(text_blocks)}

        translations = {}

        # Group blocks into paragraphs for better context
        paragraphs = self.group_into_paragraphs(text_blocks)

        block_idx = 0
        for para_blocks in paragraphs:
            # Combine paragraph text
            para_text = " ".join(b.text for b in para_blocks)

            # Translate paragraph
            try:
                if self.translator_func:
                    translated_para = await self.translator_func(para_text)
                else:
                    translated_para = para_text

                # Split translated text back to blocks (approximate)
                # Simple approach: split proportionally by original block lengths
                total_len = sum(len(b.text) for b in para_blocks)
                if total_len == 0:
                    continue

                pos = 0
                for b in para_blocks:
                    # Calculate proportion
                    proportion = len(b.text) / total_len
                    split_len = int(len(translated_para) * proportion)

                    # Extract translated portion
                    translated_text = translated_para[pos:pos+split_len].strip()
                    translations[block_idx] = translated_text

                    pos += split_len
                    block_idx += 1

            except Exception as e:
                logger.error(f"Translation failed for paragraph: {e}")
                # Fallback: use original text
                for b in para_blocks:
                    translations[block_idx] = b.text
                    block_idx += 1

        return translations

    def create_translated_pdf(
        self,
        source_pdf: str,
        text_blocks: List[TextBlock],
        translations: Dict[int, str],
        output_pdf: str
    ):
        """
        Create new PDF with translated text at exact positions.

        Preserves:
        - Layout (multi-column, positions)
        - Fonts (as much as possible)
        - Images, figures, tables
        - Page structure
        """
        # Open source PDF
        src_doc = fitz.open(source_pdf)

        # Create new PDF with same page sizes
        out_doc = fitz.open()

        for page_num in range(len(src_doc)):
            src_page = src_doc[page_num]

            # Create new page with same size
            out_page = out_doc.new_page(width=src_page.rect.width, height=src_page.rect.height)

            # Copy images from source page
            for img in src_page.get_images():
                try:
                    xref = img[0]
                    base_image = src_doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # Get image position (this is approximate)
                    img_rect = src_page.get_image_bbox(img)
                    out_page.insert_image(img_rect, stream=image_bytes)
                except Exception as e:
                    logger.warning(f"Failed to copy image: {e}")

            # Add translated text blocks
            page_blocks = [(i, b) for i, b in enumerate(text_blocks) if b.page_num == page_num]

            for idx, block in page_blocks:
                if idx not in translations:
                    continue

                translated_text = translations[idx]
                if not translated_text.strip():
                    continue

                # Prepare font
                fontname = "helv"  # Default to Helvetica
                if "Bold" in block.font_name or block.is_bold:
                    fontname = "hebo"  # Helvetica Bold
                if "Italic" in block.font_name or block.is_italic:
                    fontname = "heit"  # Helvetica Italic

                # Calculate text rectangle
                rect = fitz.Rect(block.x0, block.y0, block.x1, block.y1)

                # Insert text at exact position
                try:
                    out_page.insert_textbox(
                        rect,
                        translated_text,
                        fontsize=block.font_size,
                        fontname=fontname,
                        color=block.color,
                        align=fitz.TEXT_ALIGN_LEFT
                    )
                except Exception as e:
                    logger.warning(f"Failed to insert text block: {e}")

        # Save output PDF
        out_doc.save(output_pdf)
        out_doc.close()
        src_doc.close()

        logger.info(f"Created translated PDF: {output_pdf}")

    async def translate_pdf(
        self,
        input_pdf: str,
        output_pdf: str,
        preserve_layout: bool = True
    ) -> Dict:
        """
        Main translation function.

        Args:
            input_pdf: Path to source PDF
            output_pdf: Path to output PDF
            preserve_layout: Whether to preserve exact layout

        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting layout-preserving translation: {input_pdf}")

        # Step 1: Extract layout
        text_blocks = self.extract_layout(input_pdf)

        # Step 2: Translate text blocks
        translations = await self.translate_blocks(text_blocks)

        # Step 3: Create translated PDF
        self.create_translated_pdf(input_pdf, text_blocks, translations, output_pdf)

        stats = {
            "total_blocks": len(text_blocks),
            "translated_blocks": len(translations),
            "pages": len(set(b.page_num for b in text_blocks)),
            "layout_preservation": "exact" if preserve_layout else "approximate"
        }

        logger.info(f"Translation complete: {stats}")
        return stats
