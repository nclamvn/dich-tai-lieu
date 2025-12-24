"""
OCR Pipeline

High-level pipeline for processing scanned/handwritten documents.
Converts PDF pages to images and processes with OCR.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from io import BytesIO

from .base import OcrClient, OcrError

from config.logging_config import get_logger
logger = get_logger(__name__)



@dataclass
class OcrPage:
    """OCR result for a single page"""
    page_num: int
    text: str
    confidence: float
    blocks: List[Dict]
    metadata: Dict


class OcrPipeline:
    """
    OCR Pipeline for document processing

    Features:
    - PDF to image conversion
    - Per-page OCR processing
    - Progress tracking
    - Error recovery

    Example:
        from core.ocr.deepseek_client import DeepseekOcrClient

        ocr_client = DeepseekOcrClient()
        pipeline = OcrPipeline(ocr_client)

        pages = pipeline.process_pdf(Path("scanned.pdf"))

        for page in pages:
            logger.info(f"Page {page.page_num + 1}: {len(page.text)} chars")
    """

    def __init__(
        self,
        ocr_client: OcrClient,
        dpi: int = 300,  # Image resolution for OCR
        image_format: str = "PNG",
        language: Optional[str] = None
    ):
        """
        Initialize OCR pipeline

        Args:
            ocr_client: OCR client instance
            dpi: DPI for PDF-to-image conversion (higher = better quality)
            image_format: Image format for OCR ("PNG", "JPEG")
            language: Default language hint for OCR
        """
        self.ocr_client = ocr_client
        self.dpi = dpi
        self.image_format = image_format
        self.language = language

    def process_pdf(
        self,
        pdf_path: Path,
        page_range: Optional[tuple] = None,
        mode: str = "document"
    ) -> List[OcrPage]:
        """
        Process entire PDF with OCR

        Args:
            pdf_path: Path to PDF file
            page_range: Optional (start, end) page range (0-indexed)
            mode: OCR mode ("document", "handwriting")

        Returns:
            List of OcrPage results

        Raises:
            FileNotFoundError: If PDF doesn't exist
            OcrError: If OCR processing fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}")

        # Determine page range
        total_pages = doc.page_count
        start_page, end_page = page_range if page_range else (0, total_pages)
        start_page = max(0, start_page)
        end_page = min(total_pages, end_page)

        logger.info(f"Processing {end_page - start_page} pages with OCR (DPI: {self.dpi})...")

        ocr_pages = []

        for page_num in range(start_page, end_page):
            try:
                logger.debug(f"Processing page {page_num + 1}/{total_pages}...")

                # Convert page to image
                image_bytes = self._page_to_image(doc[page_num])

                # Process with OCR
                ocr_result = self.ocr_client.extract_structured(
                    image_bytes=image_bytes,
                    mode=mode,
                    language=self.language
                )

                # Create OcrPage
                ocr_page = OcrPage(
                    page_num=page_num,
                    text=ocr_result.get("text", ""),
                    confidence=ocr_result.get("confidence", 0.0),
                    blocks=ocr_result.get("blocks", []),
                    metadata=ocr_result.get("metadata", {})
                )

                ocr_pages.append(ocr_page)

                logger.info(f" ({len(ocr_page.text)} chars, {ocr_page.confidence:.1%} confidence)")

            except OcrError as e:
                logger.info(f"✗ OCR failed: {e}")
                # Create empty page on error
                ocr_pages.append(OcrPage(
                    page_num=page_num,
                    text="",
                    confidence=0.0,
                    blocks=[],
                    metadata={"error": str(e)}
                ))

        doc.close()

        return ocr_pages

    def process_image(
        self,
        image_path: Path,
        mode: str = "document"
    ) -> OcrPage:
        """
        Process single image file with OCR

        Args:
            image_path: Path to image file
            mode: OCR mode

        Returns:
            OcrPage result
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        ocr_result = self.ocr_client.extract_structured(
            image_bytes=image_bytes,
            mode=mode,
            language=self.language
        )

        return OcrPage(
            page_num=0,
            text=ocr_result.get("text", ""),
            confidence=ocr_result.get("confidence", 0.0),
            blocks=ocr_result.get("blocks", []),
            metadata=ocr_result.get("metadata", {})
        )

    def _page_to_image(self, page: fitz.Page) -> bytes:
        """
        Convert PDF page to image bytes

        Args:
            page: PyMuPDF page object

        Returns:
            Image bytes (PNG or JPEG)
        """
        # Render page to pixmap
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale matrix
        pix = page.get_pixmap(matrix=mat)

        # Convert to bytes
        if self.image_format.upper() == "PNG":
            image_bytes = pix.tobytes("png")
        elif self.image_format.upper() == "JPEG":
            image_bytes = pix.tobytes("jpeg")
        else:
            raise ValueError(f"Unsupported image format: {self.image_format}")

        return image_bytes

    def merge_pages_to_text(self, ocr_pages: List[OcrPage]) -> str:
        """
        Merge OCR pages into single text document

        Args:
            ocr_pages: List of OcrPage results

        Returns:
            Combined text with page separators
        """
        text_parts = []

        for page in ocr_pages:
            page_header = f"--- Page {page.page_num + 1} ---"
            text_parts.append(page_header)
            text_parts.append(page.text)
            text_parts.append("")  # Empty line between pages

        return "\n".join(text_parts)

    def get_statistics(self, ocr_pages: List[OcrPage]) -> dict:
        """
        Get OCR statistics

        Args:
            ocr_pages: List of OcrPage results

        Returns:
            Dictionary with statistics
        """
        total_chars = sum(len(p.text) for p in ocr_pages)
        avg_confidence = sum(p.confidence for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0.0

        failed_pages = [p.page_num for p in ocr_pages if p.confidence == 0.0]

        return {
            'total_pages': len(ocr_pages),
            'total_characters': total_chars,
            'avg_confidence': avg_confidence,
            'failed_pages': failed_pages,
            'success_rate': (len(ocr_pages) - len(failed_pages)) / len(ocr_pages) if ocr_pages else 0.0
        }


# Example usage
if __name__ == "__main__":
    import sys
    from .deepseek_client import DeepseekOcrClient

    logger.info("OCR Pipeline - Demo")
    logger.info("=" * 60)

    if len(sys.argv) < 2:
        logger.info("Usage: python pipeline.py <pdf_or_image_path>")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        sys.exit(1)

    # Create OCR client
    ocr_client = DeepseekOcrClient()

    if not ocr_client.health_check():
        logger.warning("OCR client not properly configured!")
        logger.info("Set DEEPSEEK_OCR_ENDPOINT and DEEPSEEK_OCR_API_KEY environment variables.")
        logger.info("Running in demo mode (will fail at actual OCR call)...")

    # Create pipeline
    pipeline = OcrPipeline(ocr_client, dpi=300)

    logger.info(f"Input: {input_path}")

    try:
        # Process based on file type
        if input_path.suffix.lower() == '.pdf':
            ocr_pages = pipeline.process_pdf(input_path)

            # Get statistics
            stats = pipeline.get_statistics(ocr_pages)

            logger.info("Statistics:")
            logger.info(f"  Total pages: {stats['total_pages']}")
            logger.info(f"  Total characters: {stats['total_characters']}")
            logger.info(f"  Avg confidence: {stats['avg_confidence']:.1%}")
            logger.info(f"  Success rate: {stats['success_rate']:.1%}")

            if stats['failed_pages']:
                logger.warning(f"  Failed pages: {stats['failed_pages']}")

            # Show sample
            if ocr_pages:
                logger.info("Sample (first page, first 300 chars):")
                logger.info("-" * 60)
                logger.info(ocr_pages[0].text[:300])
                logger.info("...")

        else:
            # Process as image
            ocr_page = pipeline.process_image(input_path)

            logger.info("Result:")
            logger.info(f"  Text length: {len(ocr_page.text)} chars")
            logger.info(f"  Confidence: {ocr_page.confidence:.1%}")
            logger.info("Extracted text (first 500 chars):")
            logger.info("-" * 60)
            logger.info(ocr_page.text[:500])
            if len(ocr_page.text) > 500:
                logger.info("...")

    except Exception as e:
        logger.exception(f"OCR failed: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("OCR processing complete!")
