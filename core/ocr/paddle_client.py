#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR Client - Local OCR Implementation
Implements OcrClient protocol using PaddleOCR for free, offline OCR.
"""

import io
import logging
import re
from typing import Optional, Dict, List, Tuple
from PIL import Image
import numpy as np

from .base import OcrClient, OcrError, OcrConnectionError, OcrInvalidInputError

logger = logging.getLogger(__name__)


def _is_garbage_text(text: str, special_char_threshold: float = 0.5) -> bool:
    """
    Check if text is likely garbage from OCR reading illustrations.

    Filters out text that is primarily special characters, which typically comes from
    OCR attempting to read decorative elements, borders, or illustrations.

    Args:
        text: Text to check
        special_char_threshold: Fraction of special chars to consider garbage (default 0.5)

    Returns:
        True if text appears to be garbage (skip it), False otherwise

    Examples:
        >>> _is_garbage_text("#$%&#'!('!)")
        True
        >>> _is_garbage_text("Chapter 1")
        False
        >>> _is_garbage_text("$$$ ### @@@")
        True
        >>> _is_garbage_text("See equation (1.5)")
        False
    """
    if not text or len(text.strip()) < 2:
        return True

    # Count alphanumeric vs special characters
    alphanumeric = sum(1 for c in text if c.isalnum() or c.isspace())
    total = len(text)

    # If less than threshold% alphanumeric, consider it garbage
    alphanumeric_ratio = alphanumeric / total if total > 0 else 0

    return alphanumeric_ratio < (1 - special_char_threshold)


class PaddleOcrClient(OcrClient):
    """
    PaddleOCR-based OCR client for local, offline text recognition.

    Features:
    - Fully local (no API calls)
    - Free and open source
    - Multi-language support
    - Text detection + recognition + classification
    - Returns bbox coordinates for layout preservation

    Installation:
        pip install paddleocr paddlepaddle opencv-python-headless

    Usage:
        client = PaddleOcrClient(lang='en')
        text = client.extract(image_bytes)
        structured = client.extract_structured(image_bytes)
    """

    def __init__(
        self,
        lang: str = 'en',
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        det_model_dir: Optional[str] = None,
        rec_model_dir: Optional[str] = None,
        cls_model_dir: Optional[str] = None
    ):
        """
        Initialize PaddleOCR client.

        Args:
            lang: Language code ('en', 'ch', 'japan', 'korean', etc.)
            use_angle_cls: Enable text angle classification (deprecated in 3.x)
            use_gpu: Use GPU acceleration (deprecated in 3.x - auto-detects)
            det_model_dir: Custom text detection model path (deprecated)
            rec_model_dir: Custom text recognition model path (deprecated)
            cls_model_dir: Custom angle classification model path (deprecated)

        Raises:
            OcrError: If PaddleOCR is not installed
        """
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu

        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise OcrError(
                "PaddleOCR is not installed. Install it with:\n"
                "  pip install paddleocr paddlepaddle opencv-python-headless\n"
                "Or install with OCR extras:\n"
                "  pip install -e .[ocr]"
            ) from e

        try:
            # Initialize PaddleOCR 3.x
            # First run will download models (~100-200MB)
            logger.info(f"Initializing PaddleOCR 3.x with lang='{lang}'")

            # PaddleOCR 3.x simplified API - only lang is needed
            self.ocr = PaddleOCR(lang=lang)

            logger.info("PaddleOCR initialized successfully")

        except Exception as e:
            raise OcrConnectionError(f"Failed to initialize PaddleOCR: {str(e)}") from e

    def extract(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> str:
        """
        Extract text from image (simple interface).

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode (ignored for PaddleOCR - always uses document mode)
            language: Language hint (ignored - uses lang from init)

        Returns:
            Extracted text as string

        Raises:
            OcrInvalidInputError: If image is invalid
            OcrError: If OCR fails
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert to numpy array (PaddleOCR expects numpy arrays)
            img_array = np.array(image)

            # Run OCR - PaddleOCR 3.x uses predict() method
            result = self.ocr.predict(img_array)

            # Extract text from result
            # PaddleOCR 3.x returns list of OCRResult objects
            if not result or len(result) == 0:
                return ""

            ocr_result = result[0]

            # Get texts and scores from new API
            rec_texts = ocr_result.get('rec_texts', [])
            rec_scores = ocr_result.get('rec_scores', [])
            rec_polys = ocr_result.get('rec_polys', [])

            if not rec_texts:
                return ""

            # Phase 4.3: OCR Quality Filtering & Paragraph Detection
            text_lines = []
            prev_y_center = None
            avg_line_height = None
            confidence_threshold = 0.5

            for i, text in enumerate(rec_texts):
                conf = rec_scores[i] if i < len(rec_scores) else 1.0

                # Filter 1: Confidence threshold
                if conf < confidence_threshold:
                    logger.debug(f"Skipping low-confidence OCR: {text[:30]}... (conf={conf:.2f})")
                    continue

                # Filter 2: Skip garbage text
                if _is_garbage_text(text):
                    logger.debug(f"Skipping garbage text: {text[:30]}...")
                    continue

                # Paragraph break detection using bounding box
                if i < len(rec_polys):
                    bbox_points = rec_polys[i]
                    y_coords = [p[1] for p in bbox_points]
                    y_center = sum(y_coords) / len(y_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    line_height = y_max - y_min

                    if avg_line_height is None:
                        avg_line_height = line_height
                    else:
                        avg_line_height = (avg_line_height + line_height) / 2

                    if prev_y_center is not None and avg_line_height is not None:
                        vertical_gap = y_center - prev_y_center
                        if vertical_gap > avg_line_height * 1.5:
                            text_lines.append("")
                            logger.debug(f"Paragraph break detected")

                    prev_y_center = y_center

                text_lines.append(text)

            return "\n".join(text_lines)

        except Exception as e:
            if "image" in str(e).lower() or "PIL" in str(e):
                raise OcrInvalidInputError(f"Invalid image data: {str(e)}") from e
            else:
                raise OcrError(f"OCR extraction failed: {str(e)}") from e

    def extract_structured(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> Dict:
        """
        Extract structured text data with bounding boxes and confidence scores.

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode (ignored for PaddleOCR)
            language: Language hint (ignored - uses lang from init)

        Returns:
            Dictionary with:
                - text: Full extracted text
                - confidence: Average confidence score (0.0-1.0)
                - blocks: List of text blocks with bbox and confidence
                - metadata: Additional OCR info

        Raises:
            OcrInvalidInputError: If image is invalid
            OcrError: If OCR fails
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Get image dimensions
            img_width, img_height = image.size

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert to numpy array
            img_array = np.array(image)

            # Run OCR - PaddleOCR 3.x uses predict() method
            result = self.ocr.predict(img_array)

            # Parse result - PaddleOCR 3.x returns list of OCRResult objects
            if not result or len(result) == 0:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "blocks": [],
                    "metadata": {
                        "engine": "paddleocr",
                        "lang": self.lang,
                        "image_width": img_width,
                        "image_height": img_height
                    }
                }

            ocr_result = result[0]

            # Get texts, scores and polys from new API
            rec_texts = ocr_result.get('rec_texts', [])
            rec_scores = ocr_result.get('rec_scores', [])
            rec_polys = ocr_result.get('rec_polys', [])

            # Extract blocks
            blocks = []
            text_lines = []
            confidences = []

            for i, text in enumerate(rec_texts):
                confidence = rec_scores[i] if i < len(rec_scores) else 1.0

                # Get bbox if available
                bbox = (0, 0, 1, 1)  # Default normalized bbox
                bbox_raw = None

                if i < len(rec_polys):
                    bbox_points = rec_polys[i]
                    # Convert bbox points to (x0, y0, x1, y1) format
                    x_coords = [p[0] for p in bbox_points]
                    y_coords = [p[1] for p in bbox_points]

                    x0, y0 = min(x_coords), min(y_coords)
                    x1, y1 = max(x_coords), max(y_coords)

                    # Normalize coordinates to 0-1 range
                    bbox = (
                        x0 / img_width,
                        y0 / img_height,
                        x1 / img_width,
                        y1 / img_height
                    )
                    bbox_raw = bbox_points.tolist() if hasattr(bbox_points, 'tolist') else list(bbox_points)

                blocks.append({
                    "text": text,
                    "bbox": bbox,
                    "confidence": float(confidence),
                    "bbox_raw": bbox_raw
                })

                text_lines.append(text)
                confidences.append(confidence)

            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": "\n".join(text_lines),
                "confidence": float(avg_confidence),
                "blocks": blocks,
                "metadata": {
                    "engine": "paddleocr",
                    "lang": self.lang,
                    "image_width": img_width,
                    "image_height": img_height,
                    "total_blocks": len(blocks)
                }
            }

        except Exception as e:
            if "image" in str(e).lower() or "PIL" in str(e):
                raise OcrInvalidInputError(f"Invalid image data: {str(e)}") from e
            else:
                raise OcrError(f"Structured OCR extraction failed: {str(e)}") from e

    def health_check(self) -> bool:
        """
        Check if OCR service is available.

        Returns:
            True if PaddleOCR is initialized and working
        """
        try:
            # Create a small test image (1x1 white pixel)
            test_img = Image.new('RGB', (100, 100), color='white')
            img_bytes = io.BytesIO()
            test_img.save(img_bytes, format='PNG')

            # Try to run OCR
            self.extract(img_bytes.getvalue())
            return True
        except Exception as e:
            logger.error(f"PaddleOCR health check failed: {str(e)}")
            return False
