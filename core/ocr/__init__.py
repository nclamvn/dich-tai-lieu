"""
OCR (Optical Character Recognition) Module - Hybrid System

Provides intelligent OCR capabilities for scanned/handwritten documents:
- Abstract OCR client interface
- PaddleOCR client (local, free)
- MathPix client (formula-specialized, optional)
- Hybrid OCR router (combines both intelligently)
- Smart PDF detector (auto-detects native vs scanned)
- High-level OCR pipeline for PDFs and images

Example usage:

    # Hybrid OCR (PaddleOCR + MathPix)
    from core.ocr import HybridOcrClient, OcrPipeline

    client = HybridOcrClient(
        mathpix_app_id="...",
        mathpix_app_key="..."
    )
    pipeline = OcrPipeline(client, dpi=300)
    ocr_pages = pipeline.process_pdf("scanned.pdf")

    # PaddleOCR only (no API key needed)
    from core.ocr import PaddleOcrClient, OcrPipeline

    client = PaddleOcrClient(lang='en')
    pipeline = OcrPipeline(client, dpi=300)
    ocr_pages = pipeline.process_pdf("scanned.pdf")

    # Smart detection
    from core.ocr import SmartDetector

    detector = SmartDetector()
    result = detector.detect_pdf_type("document.pdf")
    if result.ocr_needed:
        logger.info(f"OCR recommended: {result.recommendation}")
"""

from .base import (
    OcrClient,
    OcrError,
    OcrConnectionError,
    OcrQuotaError,
    OcrInvalidInputError
)

# Try to import OCR clients (may fail if optional dependencies not installed)
try:
    from .paddle_client import PaddleOcrClient
    _has_paddle = True
except ImportError:
    PaddleOcrClient = None
    _has_paddle = False

try:
    from .mathpix_client import MathPixOcrClient
    _has_mathpix = True
except ImportError:
    MathPixOcrClient = None
    _has_mathpix = False

try:
    from .hybrid_client import HybridOcrClient
    _has_hybrid = _has_paddle  # Hybrid requires PaddleOCR
except ImportError:
    HybridOcrClient = None
    _has_hybrid = False

from .smart_detector import SmartDetector, PDFType, OCRMode, DetectionResult
from .pipeline import OcrPipeline, OcrPage

from config.logging_config import get_logger
logger = get_logger(__name__)


# Legacy import for backward compatibility (will be removed in future)
try:
    from .deepseek_client import DeepseekOcrClient
    _has_deepseek = True
except ImportError:
    DeepseekOcrClient = None
    _has_deepseek = False


__all__ = [
    # Base interface and exceptions
    'OcrClient',
    'OcrError',
    'OcrConnectionError',
    'OcrQuotaError',
    'OcrInvalidInputError',

    # OCR Clients (may be None if dependencies not installed)
    'PaddleOcrClient',
    'MathPixOcrClient',
    'HybridOcrClient',

    # Smart Detection
    'SmartDetector',
    'PDFType',
    'OCRMode',
    'DetectionResult',

    # Pipeline
    'OcrPipeline',
    'OcrPage',

    # Legacy (deprecated)
    'DeepseekOcrClient',
]

__version__ = '2.0.0'
