"""
PDF Image Embedder - AI Publisher Pro

Embed images into PDF documents using ReportLab.
Supports auto-sizing, captions, and inline positioning.

Usage:
    embedder = PdfImageEmbedder()

    # Embed single image
    embedder.embed_image(canvas, image_block, x, y)

    # Create PDF with images
    create_pdf_with_images(image_blocks, "output.pdf")
"""

import io
from pathlib import Path
from typing import Optional, List, Union, Tuple

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch, cm, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Image, Paragraph, Spacer,
        PageBreak, KeepTogether
    )
    from reportlab.pdfgen import canvas as pdf_canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .models import ImageBlock


class PdfImageEmbedder:
    """
    Embed images into PDF documents using ReportLab.

    Features:
    - Auto-resize to fit page width (max 80% by default)
    - Maintain aspect ratio
    - Add captions below images
    - Center alignment
    - Batch embedding with Platypus flowables
    """

    # Default page dimensions (Letter size)
    DEFAULT_PAGE_SIZE = letter  # (612, 792) points
    DEFAULT_PAGE_WIDTH = 8.5 * inch
    DEFAULT_PAGE_HEIGHT = 11 * inch
    DEFAULT_MARGIN = 1 * inch
    DEFAULT_CONTENT_WIDTH = 6.5 * inch  # Usable width

    def __init__(
        self,
        max_width_ratio: float = 0.8,
        page_size: Tuple[float, float] = None,
        margin: float = None,
        center_images: bool = True
    ):
        """
        Initialize embedder.

        Args:
            max_width_ratio: Max width as ratio of content area (0.0-1.0)
            page_size: Page size tuple (width, height) in points
            margin: Page margin in points
            center_images: Whether to center images by default
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF embedding. "
                "Install with: pip install reportlab"
            )

        self.max_width_ratio = max_width_ratio
        self.page_size = page_size or self.DEFAULT_PAGE_SIZE
        self.margin = margin if margin is not None else self.DEFAULT_MARGIN
        self.center_images = center_images
        self._figure_counter = 0

        # Calculate content width
        self.content_width = self.page_size[0] - (2 * self.margin)

        # Setup styles
        self._setup_styles()

    def _setup_styles(self):
        """Setup paragraph styles for captions"""
        self.styles = getSampleStyleSheet()

        # Caption style
        self.caption_style = ParagraphStyle(
            'ImageCaption',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=6,
            fontName='Times-Italic'
        )

    def create_image_flowable(
        self,
        image_block: ImageBlock,
        width: Optional[float] = None,
        height: Optional[float] = None
    ) -> Image:
        """
        Create a ReportLab Image flowable from ImageBlock.

        Args:
            image_block: ImageBlock with image data
            width: Override width in points (None = auto-calculate)
            height: Override height in points (None = auto from aspect ratio)

        Returns:
            ReportLab Image object
        """
        # Create image stream
        image_stream = io.BytesIO(image_block.image_data)

        # Calculate dimensions
        if width is None:
            width = self._calculate_width(image_block)

        if height is None and image_block.keep_aspect_ratio:
            # Calculate height from aspect ratio
            if image_block.aspect_ratio > 0:
                height = width / image_block.aspect_ratio
            else:
                height = width  # Square fallback

        # Create ReportLab Image
        img = Image(image_stream, width=width, height=height)

        return img

    def create_image_with_caption(
        self,
        image_block: ImageBlock,
        caption: Optional[str] = None,
        auto_number: bool = True,
        width: Optional[float] = None
    ) -> List:
        """
        Create image flowable with caption.

        Args:
            image_block: ImageBlock with image data
            caption: Caption text (uses image_block.caption if None)
            auto_number: Add "Hình X:" prefix
            width: Override width in points

        Returns:
            List of flowables [Image, Paragraph] wrapped in KeepTogether
        """
        # Create image
        img = self.create_image_flowable(image_block, width)

        # Determine caption text
        caption_text = caption or image_block.caption or ""

        # Add figure number if requested
        if auto_number and caption_text:
            self._figure_counter += 1
            caption_text = f"<i>Hình {self._figure_counter}: {caption_text}</i>"
        elif auto_number and not caption_text:
            self._figure_counter += 1
            caption_text = f"<i>Hình {self._figure_counter}</i>"
        else:
            caption_text = f"<i>{caption_text}</i>" if caption_text else ""

        # Create caption paragraph
        flowables = [img]
        if caption_text:
            caption_para = Paragraph(caption_text, self.caption_style)
            flowables.append(caption_para)

        # Wrap in KeepTogether to prevent page breaks between image and caption
        return [KeepTogether(flowables)]

    def create_image_list(
        self,
        image_blocks: List[ImageBlock],
        with_captions: bool = True,
        add_spacing: bool = True
    ) -> List:
        """
        Create list of flowables for multiple images.

        Args:
            image_blocks: List of ImageBlock objects
            with_captions: Include captions for each image
            add_spacing: Add spacer between images

        Returns:
            List of flowables
        """
        flowables = []

        for i, image_block in enumerate(image_blocks):
            if with_captions:
                img_flowables = self.create_image_with_caption(image_block)
                flowables.extend(img_flowables)
            else:
                img = self.create_image_flowable(image_block)
                flowables.append(img)

            # Add spacing between images
            if add_spacing and i < len(image_blocks) - 1:
                flowables.append(Spacer(1, 12))

        return flowables

    def embed_on_canvas(
        self,
        canvas: "pdf_canvas.Canvas",
        image_block: ImageBlock,
        x: float,
        y: float,
        width: Optional[float] = None,
        height: Optional[float] = None
    ):
        """
        Embed image directly on a canvas at specific position.

        Args:
            canvas: ReportLab Canvas object
            image_block: ImageBlock with image data
            x: X position in points
            y: Y position in points
            width: Width in points (None = auto)
            height: Height in points (None = auto from aspect ratio)
        """
        # Create image stream
        image_stream = io.BytesIO(image_block.image_data)

        # Calculate dimensions
        if width is None:
            width = self._calculate_width(image_block)

        if height is None and image_block.keep_aspect_ratio:
            if image_block.aspect_ratio > 0:
                height = width / image_block.aspect_ratio
            else:
                height = width

        # Draw image on canvas
        canvas.drawImage(
            image_stream,
            x, y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask='auto'
        )

    def _calculate_width(self, image_block: ImageBlock) -> float:
        """
        Calculate optimal width for image in points.

        Args:
            image_block: ImageBlock with dimensions

        Returns:
            Width in points
        """
        # Max width based on content area and ratio
        max_width = self.content_width * self.max_width_ratio

        # Use image's specified max width if smaller
        max_width_points = image_block.max_width_inches * inch
        if max_width_points < max_width:
            max_width = max_width_points

        # Calculate width based on original dimensions
        if image_block.width_px > 0:
            # Assume 96 DPI for screen images, convert to points (72 DPI)
            original_width_points = (image_block.width_px / 96.0) * inch

            # Use smaller of original or max
            width = min(original_width_points, max_width)
        else:
            width = max_width

        return width

    def reset_counter(self):
        """Reset the figure counter (call at start of new document)"""
        self._figure_counter = 0

    def set_figure_counter(self, value: int):
        """Set the figure counter to a specific value"""
        self._figure_counter = value


def create_pdf_with_images(
    image_blocks: List[ImageBlock],
    output_path: Union[str, Path],
    title: Optional[str] = None,
    with_captions: bool = True,
    page_size: Tuple[float, float] = None
) -> Path:
    """
    Create a new PDF document with embedded images.

    Args:
        image_blocks: List of ImageBlock objects
        output_path: Output file path
        title: Optional document title
        with_captions: Include captions
        page_size: Page size (default: letter)

    Returns:
        Path to created document

    Example:
        from core.image_embedding import extract_images, create_pdf_with_images
        images = extract_images("source.pdf")
        create_pdf_with_images(images, "output.pdf", title="Extracted Images")
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF creation")

    output_path = Path(output_path)
    page_size = page_size or letter

    # Create document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=page_size,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch
    )

    # Build flowables
    flowables = []
    styles = getSampleStyleSheet()

    # Add title if provided
    if title:
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=24
        )
        flowables.append(Paragraph(title, title_style))
        flowables.append(Spacer(1, 12))

    # Create embedder and add images
    embedder = PdfImageEmbedder(page_size=page_size)
    image_flowables = embedder.create_image_list(
        image_blocks,
        with_captions=with_captions
    )
    flowables.extend(image_flowables)

    # Build PDF
    doc.build(flowables)

    return output_path


def add_images_to_pdf_flowables(
    image_blocks: List[ImageBlock],
    with_captions: bool = True,
    max_width_ratio: float = 0.8
) -> List:
    """
    Create flowables from images for use in existing PDF generation.

    Args:
        image_blocks: List of ImageBlock objects
        with_captions: Include captions
        max_width_ratio: Max width as ratio of content area

    Returns:
        List of ReportLab flowables

    Example:
        # In your existing PDF generation code:
        from core.image_embedding import add_images_to_pdf_flowables

        flowables = []
        flowables.append(Paragraph("Chapter 1", styles['Heading1']))
        flowables.append(Paragraph("Some text...", styles['Normal']))

        # Add images
        image_flowables = add_images_to_pdf_flowables(images)
        flowables.extend(image_flowables)

        doc.build(flowables)
    """
    embedder = PdfImageEmbedder(max_width_ratio=max_width_ratio)
    return embedder.create_image_list(image_blocks, with_captions=with_captions)
