"""
OCR Client Base Interface

Defines abstract interface for OCR clients.
"""

from typing import Protocol, Optional
from pathlib import Path


class OcrClient(Protocol):
    """
    Abstract OCR client interface

    All OCR implementations should follow this protocol.

    Example implementations:
    - DeepSeek OCR
    - Google Cloud Vision
    - Azure Computer Vision
    - Tesseract OCR
    """

    def extract(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> str:
        """
        Extract text from image

        Args:
            image_bytes: Image data (PNG, JPEG, etc.)
            mode: OCR mode ("document", "handwriting", "scene", etc.)
            language: Target language hint (ISO 639-1 code, e.g., "en", "vi")

        Returns:
            Extracted text

        Raises:
            OcrError: If OCR fails
        """
        ...

    def extract_structured(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> dict:
        """
        Extract structured data from image

        Returns a dictionary with:
        - text: Full extracted text
        - confidence: Overall confidence score (0.0-1.0)
        - blocks: List of text blocks with bounding boxes (optional)
        - metadata: Additional OCR metadata

        Args:
            image_bytes: Image data
            mode: OCR mode
            language: Language hint

        Returns:
            Structured OCR result
        """
        ...


class OcrError(Exception):
    """Base exception for OCR-related errors"""
    pass


class OcrConnectionError(OcrError):
    """OCR service connection error"""
    pass


class OcrQuotaError(OcrError):
    """OCR quota/rate limit exceeded"""
    pass


class OcrInvalidInputError(OcrError):
    """Invalid input image"""
    pass
