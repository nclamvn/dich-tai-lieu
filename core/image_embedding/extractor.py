"""
Image Extractor - AI Publisher Pro

Extract images from PDF documents using PyMuPDF (fitz).
Supports PNG, JPEG, and other common formats.

Usage:
    extractor = ImageExtractor()
    images = extractor.extract_from_pdf("document.pdf")

    for img in images:
        print(f"Found image: {img.width_px}x{img.height_px} on page {img.source_page}")
"""

import io
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .models import ImageBlock, ImageFormat, ImagePosition


@dataclass
class ExtractionConfig:
    """Configuration for image extraction"""
    # Minimum dimensions (skip tiny images like icons)
    min_width: int = 50  # pixels
    min_height: int = 50  # pixels

    # Maximum dimensions (resize if larger)
    max_width: int = 2000  # pixels
    max_height: int = 2000  # pixels

    # Output format
    output_format: ImageFormat = ImageFormat.PNG
    jpeg_quality: int = 85  # For JPEG output

    # Filtering
    skip_duplicates: bool = True  # Skip duplicate images
    skip_masks: bool = True  # Skip mask/alpha images

    # Page range (None = all pages)
    start_page: Optional[int] = None  # 1-indexed
    end_page: Optional[int] = None  # 1-indexed (inclusive)


class ImageExtractor:
    """
    Extract images from PDF documents.

    Uses PyMuPDF for extraction with optional Pillow for processing.
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize extractor.

        Args:
            config: Extraction configuration. Uses defaults if not provided.
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF (fitz) is required for image extraction. "
                "Install with: pip install pymupdf"
            )

        self.config = config or ExtractionConfig()
        self._seen_hashes: set = set()  # For duplicate detection

    def extract_from_pdf(
        self,
        pdf_path: Union[str, Path],
        pages: Optional[List[int]] = None
    ) -> List[ImageBlock]:
        """
        Extract all images from a PDF file.

        Args:
            pdf_path: Path to PDF file
            pages: Specific pages to extract from (1-indexed). None = all pages.

        Returns:
            List of ImageBlock objects with extracted images
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self._seen_hashes.clear()  # Reset for new document
        images: List[ImageBlock] = []

        doc = fitz.open(pdf_path)
        try:
            # Determine page range
            total_pages = len(doc)
            if pages:
                page_indices = [p - 1 for p in pages if 0 < p <= total_pages]
            else:
                start = (self.config.start_page or 1) - 1
                end = self.config.end_page or total_pages
                page_indices = list(range(start, min(end, total_pages)))

            # Extract from each page
            for page_idx in page_indices:
                page = doc[page_idx]
                page_images = self._extract_from_page(page, page_idx + 1)
                images.extend(page_images)

        finally:
            doc.close()

        return images

    def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        pages: Optional[List[int]] = None
    ) -> List[ImageBlock]:
        """
        Extract images from PDF bytes (in-memory).

        Args:
            pdf_bytes: PDF file content as bytes
            pages: Specific pages to extract from (1-indexed)

        Returns:
            List of ImageBlock objects
        """
        self._seen_hashes.clear()
        images: List[ImageBlock] = []

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            total_pages = len(doc)
            if pages:
                page_indices = [p - 1 for p in pages if 0 < p <= total_pages]
            else:
                start = (self.config.start_page or 1) - 1
                end = self.config.end_page or total_pages
                page_indices = list(range(start, min(end, total_pages)))

            for page_idx in page_indices:
                page = doc[page_idx]
                page_images = self._extract_from_page(page, page_idx + 1)
                images.extend(page_images)

        finally:
            doc.close()

        return images

    def _extract_from_page(
        self,
        page: "fitz.Page",
        page_number: int
    ) -> List[ImageBlock]:
        """
        Extract images from a single page.

        Args:
            page: PyMuPDF page object
            page_number: 1-indexed page number

        Returns:
            List of ImageBlock objects from this page
        """
        images: List[ImageBlock] = []
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        # Get all images on this page
        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            try:
                image_block = self._process_image(
                    page.parent,  # Document reference
                    img_info,
                    page_number,
                    img_index,
                    page_width,
                    page_height,
                    page
                )
                if image_block:
                    images.append(image_block)

            except Exception as e:
                # Log but continue with other images
                print(f"Warning: Failed to extract image {img_index} on page {page_number}: {e}")
                continue

        return images

    def _process_image(
        self,
        doc: "fitz.Document",
        img_info: tuple,
        page_number: int,
        img_index: int,
        page_width: float,
        page_height: float,
        page: "fitz.Page"
    ) -> Optional[ImageBlock]:
        """
        Process a single image from the PDF.

        Args:
            doc: PyMuPDF document
            img_info: Image info tuple from get_images()
            page_number: Page number (1-indexed)
            img_index: Index of image on page
            page_width: Page width in points
            page_height: Page height in points
            page: Page object for position lookup

        Returns:
            ImageBlock or None if image should be skipped
        """
        xref = img_info[0]  # Image reference number

        # Extract image
        base_image = doc.extract_image(xref)
        if not base_image:
            return None

        image_bytes = base_image["image"]
        image_ext = base_image.get("ext", "png")
        width = base_image.get("width", 0)
        height = base_image.get("height", 0)

        # Skip masks if configured
        if self.config.skip_masks and base_image.get("cs-name") == "Indexed":
            # Could be a mask, check alpha
            if base_image.get("alpha", 0) > 0:
                return None

        # Skip small images
        if width < self.config.min_width or height < self.config.min_height:
            return None

        # Check for duplicates
        if self.config.skip_duplicates:
            img_hash = hashlib.md5(image_bytes).hexdigest()
            if img_hash in self._seen_hashes:
                return None
            self._seen_hashes.add(img_hash)

        # Get image position on page
        position = self._get_image_position(
            page, xref, page_number, page_width, page_height
        )

        # Convert format if needed
        final_bytes, final_format, final_width, final_height = self._process_image_data(
            image_bytes, image_ext, width, height
        )

        # Generate unique ID
        image_id = f"img_p{page_number}_{img_index}_{xref}"

        return ImageBlock(
            image_data=final_bytes,
            format=final_format,
            width_px=final_width,
            height_px=final_height,
            position=position,
            image_id=image_id,
            source_page=page_number,
            source_index=img_index,
            metadata={
                "xref": xref,
                "original_ext": image_ext,
                "original_width": width,
                "original_height": height,
                "colorspace": base_image.get("cs-name", "unknown"),
            }
        )

    def _get_image_position(
        self,
        page: "fitz.Page",
        xref: int,
        page_number: int,
        page_width: float,
        page_height: float
    ) -> ImagePosition:
        """
        Get the position of an image on the page.

        Args:
            page: PyMuPDF page object
            xref: Image xref number
            page_number: Page number
            page_width: Page width in points
            page_height: Page height in points

        Returns:
            ImagePosition object
        """
        # Try to find image rect on page
        x, y, w, h = 0.0, 0.0, 0.0, 0.0

        try:
            # Get all image instances on page
            for img in page.get_images():
                if img[0] == xref:
                    # Found our image, now get its bbox
                    img_rects = page.get_image_rects(img)
                    if img_rects:
                        rect = img_rects[0]  # First occurrence
                        x = rect.x0
                        y = rect.y0
                        w = rect.width
                        h = rect.height
                        break
        except Exception as e:
            logger.debug("Image position lookup failed, using defaults: %s", e)

        # Calculate relative position
        x_ratio = x / page_width if page_width > 0 else 0.0
        y_ratio = y / page_height if page_height > 0 else 0.0

        return ImagePosition(
            page=page_number,
            x=x,
            y=y,
            width=w,
            height=h,
            x_ratio=x_ratio,
            y_ratio=y_ratio,
        )

    def _process_image_data(
        self,
        image_bytes: bytes,
        original_ext: str,
        width: int,
        height: int
    ) -> Tuple[bytes, ImageFormat, int, int]:
        """
        Process image data: convert format, resize if needed.

        Args:
            image_bytes: Original image bytes
            original_ext: Original file extension
            width: Original width
            height: Original height

        Returns:
            Tuple of (processed_bytes, format, width, height)
        """
        # If Pillow not available, return as-is
        if not PILLOW_AVAILABLE:
            fmt = ImageFormat.from_extension(original_ext)
            return image_bytes, fmt, width, height

        try:
            # Open with Pillow
            img = Image.open(io.BytesIO(image_bytes))

            # Convert RGBA to RGB for JPEG
            if self.config.output_format == ImageFormat.JPEG:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

            # Resize if too large
            if width > self.config.max_width or height > self.config.max_height:
                img.thumbnail(
                    (self.config.max_width, self.config.max_height),
                    Image.Resampling.LANCZOS
                )
                width, height = img.size

            # Save to bytes
            output = io.BytesIO()
            if self.config.output_format == ImageFormat.JPEG:
                img.save(output, format="JPEG", quality=self.config.jpeg_quality)
            elif self.config.output_format == ImageFormat.PNG:
                img.save(output, format="PNG", optimize=True)
            else:
                # Default to PNG
                img.save(output, format="PNG")

            return output.getvalue(), self.config.output_format, width, height

        except Exception:
            # Pillow processing failed, return original
            fmt = ImageFormat.from_extension(original_ext)
            return image_bytes, fmt, width, height

    def get_image_count(self, pdf_path: Union[str, Path]) -> Dict[int, int]:
        """
        Get count of images per page without extracting.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict mapping page number (1-indexed) to image count
        """
        pdf_path = Path(pdf_path)
        counts: Dict[int, int] = {}

        doc = fitz.open(pdf_path)
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                image_list = page.get_images()
                counts[page_idx + 1] = len(image_list)
        finally:
            doc.close()

        return counts

    def get_total_image_count(self, pdf_path: Union[str, Path]) -> int:
        """
        Get total number of images in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Total image count
        """
        counts = self.get_image_count(pdf_path)
        return sum(counts.values())


# Convenience function
def extract_images(
    pdf_path: Union[str, Path],
    min_size: int = 50,
    output_format: str = "png",
    pages: Optional[List[int]] = None
) -> List[ImageBlock]:
    """
    Quick function to extract images from a PDF.

    Args:
        pdf_path: Path to PDF file
        min_size: Minimum width/height in pixels (default 50)
        output_format: Output format - "png" or "jpeg" (default "png")
        pages: Specific pages to extract from (1-indexed), None = all

    Returns:
        List of ImageBlock objects

    Example:
        images = extract_images("document.pdf")
        for img in images:
            print(f"Found: {img.width_px}x{img.height_px} on page {img.source_page}")
    """
    config = ExtractionConfig(
        min_width=min_size,
        min_height=min_size,
        output_format=ImageFormat.from_extension(output_format),
    )
    extractor = ImageExtractor(config)
    return extractor.extract_from_pdf(pdf_path, pages)
