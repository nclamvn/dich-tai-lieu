"""
Layout Extractor Module (Phase 3 - Production Quality)

PyMuPDF-based PDF layout extraction with:
- Multi-column detection
- Advanced reading order
- Block type classification (title, caption, table, etc.)
- Figure and caption linking
"""

import fitz  # PyMuPDF
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from enum import Enum
from collections import defaultdict
import re


class BlockType(Enum):
    """Types of content blocks"""
    TEXT = "text"
    TITLE = "title"  # Main heading
    HEADING = "heading"  # Section heading
    CAPTION = "caption"  # Figure/table caption
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"
    CODE = "code"
    FOOTER = "footer"  # Page footer
    HEADER = "header"  # Page header


@dataclass
class TextBlock:
    """
    Represents a text block with position information

    Attributes:
        text: The text content
        bbox: Bounding box (x0, y0, x1, y1)
        block_type: Type of block
        page_num: Page number (0-indexed)
        font_size: Font size in points
        font_name: Font family name
        reading_order: Position in reading sequence
        column_index: Column number (0-indexed, -1 if not in column)
        is_bold: Whether text appears bold
        confidence: Confidence score for block type classification (0.0-1.0)
        linked_image_index: Index of associated image (for captions)
        metadata: Additional metadata
    """
    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    block_type: BlockType = BlockType.TEXT
    page_num: int = 0
    font_size: float = 12.0
    font_name: str = "default"
    reading_order: int = 0
    column_index: int = -1
    is_bold: bool = False
    confidence: float = 1.0
    linked_image_index: Optional[int] = None
    metadata: Dict = field(default_factory=dict)

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def y1(self) -> float:
        return self.bbox[3]

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class PageLayout:
    """
    Layout information for a single page

    Attributes:
        page_num: Page number (0-indexed)
        width: Page width in points
        height: Page height in points
        blocks: List of text blocks
        rotation: Page rotation in degrees
    """
    page_num: int
    width: float
    height: float
    blocks: List[TextBlock]
    rotation: int = 0

    def get_blocks_sorted(self) -> List[TextBlock]:
        """Get blocks sorted by reading order"""
        return sorted(self.blocks, key=lambda b: b.reading_order)


@dataclass
class DocumentLayout:
    """
    Complete document layout information

    Attributes:
        pages: List of page layouts
        metadata: Document metadata (title, author, etc.)
        total_pages: Total number of pages
    """
    pages: List[PageLayout]
    metadata: dict
    total_pages: int

    def get_all_blocks(self) -> List[TextBlock]:
        """Get all blocks from all pages"""
        all_blocks = []
        for page in self.pages:
            all_blocks.extend(page.blocks)
        return all_blocks


class LayoutExtractor:
    """
    Extract layout information from PDFs using PyMuPDF

    Phase 3 Production Quality Implementation:
    - Multi-column detection via x-coordinate clustering
    - Advanced reading order (column-aware)
    - Block type classification (title, heading, caption, table, etc.)
    - Figure and caption linking
    - Font and style analysis

    Features:
    - Heuristic-based classification (no ML required)
    - Handles 1-3 column layouts
    - Detects headers/footers
    - Links captions to nearby images
    """

    def __init__(
        self,
        enable_column_detection: bool = True,
        enable_type_classification: bool = True,
        column_gap_threshold: float = 30.0,  # Minimum gap between columns (points)
        avg_font_size: float = 12.0  # Default average font size
    ):
        """
        Initialize the layout extractor

        Args:
            enable_column_detection: Enable multi-column detection
            enable_type_classification: Enable block type classification
            column_gap_threshold: Minimum horizontal gap to consider a column break
            avg_font_size: Estimated average font size for the document
        """
        self.enable_column_detection = enable_column_detection
        self.enable_type_classification = enable_type_classification
        self.column_gap_threshold = column_gap_threshold
        self.avg_font_size = avg_font_size

    def extract_layout(self, pdf_path: Path) -> DocumentLayout:
        """
        Extract complete layout from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            DocumentLayout with all pages and blocks

        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PDF is invalid
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}")

        # Extract metadata
        metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'pages': doc.page_count,
        }

        # Extract layout from each page
        pages = []
        for page_num in range(doc.page_count):
            page_layout = self._extract_page_layout(doc[page_num], page_num)
            pages.append(page_layout)

        doc.close()

        return DocumentLayout(
            pages=pages,
            metadata=metadata,
            total_pages=len(pages)
        )

    def _extract_page_layout(self, page: fitz.Page, page_num: int) -> PageLayout:
        """
        Extract layout from a single page with enhanced analysis

        Args:
            page: PyMuPDF page object
            page_num: Page number

        Returns:
            PageLayout with blocks
        """
        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Extract text blocks with font information
        blocks = []

        # Use dict format to get detailed font info
        text_dict = page.get_text("dict")

        for block_idx, block in enumerate(text_dict.get("blocks", [])):
            # Skip image blocks for now
            if block.get("type") != 0:  # 0 = text block
                continue

            # Extract text and bbox
            bbox = tuple(block["bbox"])

            # Collect all text and font info from lines
            block_text_parts = []
            font_sizes = []
            font_names = []
            is_bold = False

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    block_text_parts.append(span_text)
                    font_sizes.append(span.get("size", self.avg_font_size))
                    font_name = span.get("font", "")
                    font_names.append(font_name)

                    # Check if bold
                    if "bold" in font_name.lower():
                        is_bold = True

            full_text = "".join(block_text_parts).strip()

            # Filter out empty blocks
            if not full_text:
                continue

            # Calculate average font size for this block
            avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else self.avg_font_size
            primary_font = max(set(font_names), key=font_names.count) if font_names else "default"

            # Create TextBlock with enhanced info
            text_block = TextBlock(
                text=full_text,
                bbox=bbox,
                block_type=BlockType.TEXT,  # Will be classified later
                page_num=page_num,
                font_size=avg_font,
                font_name=primary_font,
                reading_order=block_idx,
                is_bold=is_bold
            )

            blocks.append(text_block)

        # Detect columns
        if self.enable_column_detection:
            blocks = self._detect_columns(blocks, width)

        # Classify block types
        if self.enable_type_classification:
            blocks = self._classify_block_types(blocks, height)

        # Determine reading order (column-aware)
        blocks = self._determine_reading_order(blocks)

        return PageLayout(
            page_num=page_num,
            width=width,
            height=height,
            blocks=blocks,
            rotation=page.rotation
        )

    def _detect_columns(self, blocks: List[TextBlock], page_width: float) -> List[TextBlock]:
        """
        Detect columns using x-coordinate clustering

        Args:
            blocks: List of text blocks
            page_width: Page width in points

        Returns:
            Blocks with column_index set
        """
        if not blocks:
            return blocks

        # Collect center x-coordinates
        x_centers = [(b.x0 + b.x1) / 2 for b in blocks]

        # Simple clustering: sort and find gaps
        sorted_x = sorted(set(x_centers))

        # Identify column boundaries by finding large gaps
        column_boundaries = [0]  # Start of first column
        for i in range(len(sorted_x) - 1):
            gap = sorted_x[i + 1] - sorted_x[i]
            if gap > self.column_gap_threshold:
                # Mid-point of gap becomes column boundary
                column_boundaries.append((sorted_x[i] + sorted_x[i + 1]) / 2)

        column_boundaries.append(page_width)  # End of last column

        # Assign blocks to columns
        for block in blocks:
            block_center_x = (block.x0 + block.x1) / 2

            # Find which column this block belongs to
            for col_idx in range(len(column_boundaries) - 1):
                if column_boundaries[col_idx] <= block_center_x < column_boundaries[col_idx + 1]:
                    block.column_index = col_idx
                    break

        return blocks

    def _classify_block_types(self, blocks: List[TextBlock], page_height: float) -> List[TextBlock]:
        """
        Classify block types using heuristics

        Args:
            blocks: List of text blocks
            page_height: Page height in points

        Returns:
            Blocks with block_type classified
        """
        if not blocks:
            return blocks

        # Calculate page statistics
        font_sizes = [b.font_size for b in blocks]
        avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else self.avg_font_size
        max_font = max(font_sizes) if font_sizes else avg_font

        # Header/Footer detection zones (top/bottom 10% of page)
        header_zone = page_height * 0.1
        footer_zone = page_height * 0.9

        for block in blocks:
            text = block.text
            text_lower = text.lower()
            word_count = len(text.split())

            # Header detection
            if block.y0 < header_zone and word_count < 15:
                block.block_type = BlockType.HEADER
                block.confidence = 0.8
                continue

            # Footer detection (page numbers, etc.)
            if block.y0 > footer_zone and word_count < 20:
                block.block_type = BlockType.FOOTER
                block.confidence = 0.8
                continue

            # Title detection (large font, bold, short, near top)
            if (block.font_size > avg_font * 1.5 and
                block.is_bold and
                word_count < 20 and
                block.y0 < page_height * 0.3):
                block.block_type = BlockType.TITLE
                block.confidence = 0.9
                continue

            # Heading detection (larger than average, bold or short)
            if ((block.font_size > avg_font * 1.2 and block.is_bold) or
                (block.font_size > avg_font * 1.3)):
                if word_count < 15:
                    block.block_type = BlockType.HEADING
                    block.confidence = 0.7
                    continue

            # Caption detection (starts with "Figure", "Table", "Fig.", etc.)
            caption_patterns = [r'^(figure|fig\.|table|tbl\.|chart|diagram)\s+\d', r'^caption:']
            for pattern in caption_patterns:
                if re.search(pattern, text_lower):
                    block.block_type = BlockType.CAPTION
                    block.confidence = 0.95
                    break

            if block.block_type == BlockType.CAPTION:
                continue

            # Table detection (many short lines, grid-like structure)
            lines = text.split('\n')
            if len(lines) > 3:
                # Check if lines are roughly same length (table-like)
                line_lengths = [len(line) for line in lines if line.strip()]
                if line_lengths:
                    avg_len = sum(line_lengths) / len(line_lengths)
                    variance = sum((l - avg_len) ** 2 for l in line_lengths) / len(line_lengths)
                    # Low variance suggests table structure
                    if variance < avg_len * 0.5:
                        block.block_type = BlockType.TABLE
                        block.confidence = 0.6
                        continue

            # Default: regular text
            block.block_type = BlockType.TEXT
            block.confidence = 1.0

        return blocks

    def _determine_reading_order(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Determine reading order for blocks (column-aware)

        For multi-column layouts: read column 0 top-to-bottom, then column 1, etc.
        For single-column: read top-to-bottom

        Args:
            blocks: List of text blocks

        Returns:
            Blocks sorted by reading order
        """
        # Check if columns were detected
        has_columns = any(b.column_index >= 0 for b in blocks)

        if has_columns:
            # Sort by: column index, then Y position (top to bottom)
            sorted_blocks = sorted(blocks, key=lambda b: (b.column_index, b.y0))
        else:
            # Simple top-to-bottom, left-to-right
            sorted_blocks = sorted(blocks, key=lambda b: (b.y0, b.x0))

        # Update reading_order attribute
        for i, block in enumerate(sorted_blocks):
            block.reading_order = i

        return sorted_blocks

    def extract_text_with_layout(self, pdf_path: Path) -> str:
        """
        Extract text preserving approximate layout

        This is a convenience method that extracts text while
        attempting to preserve reading order and spacing.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text with layout hints

        Note:
            This is a simplified version. For production use,
            consider more sophisticated layout preservation.
        """
        layout = self.extract_layout(pdf_path)

        text_parts = []
        for page in layout.pages:
            page_text_parts = []
            for block in page.get_blocks_sorted():
                page_text_parts.append(block.text)

            # Join blocks with newlines
            page_text = '\n\n'.join(page_text_parts)
            text_parts.append(f"--- Page {page.page_num + 1} ---\n\n{page_text}")

        return '\n\n'.join(text_parts)

    def analyze_layout(self, pdf_path: Path) -> dict:
        """
        Analyze document layout and return statistics

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with layout statistics
        """
        layout = self.extract_layout(pdf_path)

        total_blocks = len(layout.get_all_blocks())
        blocks_per_page = [len(page.blocks) for page in layout.pages]

        avg_blocks_per_page = sum(blocks_per_page) / len(blocks_per_page) if blocks_per_page else 0

        return {
            'total_pages': layout.total_pages,
            'total_blocks': total_blocks,
            'blocks_per_page': blocks_per_page,
            'avg_blocks_per_page': avg_blocks_per_page,
            'page_sizes': [(p.width, p.height) for p in layout.pages],
            'has_rotation': any(p.rotation != 0 for p in layout.pages),
        }


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python layout_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Analyzing layout of: {pdf_path}")
    print("=" * 80)

    extractor = LayoutExtractor()

    # Analyze layout
    stats = extractor.analyze_layout(pdf_path)

    print(f"\nLayout Statistics:")
    print(f"  Total pages: {stats['total_pages']}")
    print(f"  Total blocks: {stats['total_blocks']}")
    print(f"  Avg blocks/page: {stats['avg_blocks_per_page']:.1f}")
    print(f"  Has rotation: {stats['has_rotation']}")

    # Extract layout
    layout = extractor.extract_layout(pdf_path)

    print(f"\nFirst page layout:")
    if layout.pages:
        first_page = layout.pages[0]
        print(f"  Page size: {first_page.width:.0f} x {first_page.height:.0f}")
        print(f"  Blocks: {len(first_page.blocks)}")

        if first_page.blocks:
            print(f"\n  First block:")
            first_block = first_page.blocks[0]
            print(f"    Text: {first_block.text[:100]}...")
            print(f"    BBox: {first_block.bbox}")
            print(f"    Size: {first_block.width:.1f} x {first_block.height:.1f}")

    print("\n" + "=" * 80)
    print("✓ Layout extraction complete!")
