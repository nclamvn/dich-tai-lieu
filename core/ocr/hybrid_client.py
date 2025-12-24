#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid OCR Client - Intelligent Multi-Engine OCR Routing
Coordinates between PaddleOCR (local) and MathPix (formula-specialized) for optimal results.
"""

import io
import logging
from typing import Optional, Dict, List
from PIL import Image
import numpy as np

from .base import OcrClient, OcrError, OcrQuotaError
from .paddle_client import PaddleOcrClient
from .mathpix_client import MathPixOcrClient

logger = logging.getLogger(__name__)


class HybridOcrClient(OcrClient):
    """
    Hybrid OCR client that intelligently routes regions to appropriate OCR engines.

    Strategy:
    1. Use PaddleOCR for initial text detection (finds all text regions)
    2. Classify regions as TEXT or FORMULA using heuristics
    3. Route TEXT regions → PaddleOCR recognition
    4. Route FORMULA regions → MathPix (if available, otherwise PaddleOCR)
    5. Merge results preserving layout order

    Fallback Behavior:
    - If MathPix unavailable → PaddleOCR for all regions
    - If PaddleOCR fails → raise error (required component)
    - If MathPix quota exceeded → PaddleOCR for formulas

    Usage:
        # With MathPix
        client = HybridOcrClient(
            mathpix_app_id="...",
            mathpix_app_key="..."
        )

        # PaddleOCR only
        client = HybridOcrClient()

        result = client.extract_structured(image_bytes)
    """

    def __init__(
        self,
        paddle_lang: str = 'en',
        mathpix_app_id: Optional[str] = None,
        mathpix_app_key: Optional[str] = None,
        formula_detection_threshold: float = 0.5,
        use_mathpix: bool = True
    ):
        """
        Initialize hybrid OCR client.

        Args:
            paddle_lang: Language for PaddleOCR ('en', 'ch', etc.)
            mathpix_app_id: MathPix App ID (optional)
            mathpix_app_key: MathPix App Key (optional)
            formula_detection_threshold: Confidence threshold for formula detection
            use_mathpix: Whether to use MathPix for formulas (if available)

        Raises:
            OcrError: If PaddleOCR initialization fails
        """
        self.formula_threshold = formula_detection_threshold
        self.use_mathpix = use_mathpix

        # Initialize PaddleOCR (required)
        try:
            self.paddle_client = PaddleOcrClient(lang=paddle_lang)
            logger.info("PaddleOCR initialized for hybrid OCR")
        except Exception as e:
            raise OcrError(f"Failed to initialize PaddleOCR: {str(e)}") from e

        # Initialize MathPix (optional)
        self.mathpix_client = None
        if use_mathpix and (mathpix_app_id or mathpix_app_key):
            try:
                self.mathpix_client = MathPixOcrClient(
                    app_id=mathpix_app_id,
                    app_key=mathpix_app_key
                )
                logger.info("MathPix initialized for hybrid OCR")
            except Exception as e:
                logger.warning(f"MathPix initialization failed, using PaddleOCR only: {str(e)}")
                self.mathpix_client = None

    def extract(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> str:
        """
        Extract text from image using hybrid OCR.

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode ("document" or "handwriting")
            language: Language hint (optional)

        Returns:
            Extracted text as string

        Raises:
            OcrError: If OCR fails
        """
        structured = self.extract_structured(image_bytes, mode, language)
        return structured.get("text", "")

    def extract_structured(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> Dict:
        """
        Extract structured text with intelligent routing.

        Process:
        1. PaddleOCR detects all text regions
        2. Classify each region (text vs formula)
        3. Route formulas to MathPix if available
        4. Merge results in reading order

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode
            language: Language hint

        Returns:
            Dictionary with merged OCR results

        Raises:
            OcrError: If OCR fails
        """
        try:
            # Step 1: Use PaddleOCR for initial detection + recognition
            logger.debug("Running PaddleOCR for text detection...")
            paddle_result = self.paddle_client.extract_structured(
                image_bytes, mode, language
            )

            if not paddle_result.get("blocks"):
                # No text detected
                return paddle_result

            # Step 2: Classify blocks and route to appropriate engine
            blocks = paddle_result["blocks"]
            final_blocks = []

            for i, block in enumerate(blocks):
                block_text = block.get("text", "")

                # Detect if block contains formula
                is_formula = self._is_formula_block(block_text, block)

                if is_formula and self.mathpix_client:
                    # Route to MathPix
                    logger.debug(f"Block {i} classified as FORMULA, routing to MathPix...")

                    try:
                        # Extract region from image
                        region_bytes = self._extract_region(
                            image_bytes,
                            block["bbox"]
                        )

                        # OCR with MathPix
                        mathpix_result = self.mathpix_client.extract_structured(
                            region_bytes, mode, language
                        )

                        # Update block with MathPix result
                        block["text"] = mathpix_result.get("text", block_text)
                        block["confidence"] = mathpix_result.get("confidence", block["confidence"])
                        block["engine"] = "mathpix"
                        block["latex"] = mathpix_result.get("text")  # LaTeX format

                    except OcrQuotaError:
                        logger.warning(f"MathPix quota exceeded for block {i}, using PaddleOCR result")
                        block["engine"] = "paddleocr"
                        block["mathpix_error"] = "quota_exceeded"

                    except Exception as e:
                        logger.warning(f"MathPix failed for block {i}: {str(e)}, using PaddleOCR result")
                        block["engine"] = "paddleocr"
                        block["mathpix_error"] = str(e)

                else:
                    # Use PaddleOCR result
                    block["engine"] = "paddleocr"

                final_blocks.append(block)

            # Step 3: Aggregate results
            all_text = "\n".join(b["text"] for b in final_blocks if b.get("text"))
            avg_confidence = sum(b["confidence"] for b in final_blocks) / len(final_blocks)

            # Count engine usage
            paddle_count = sum(1 for b in final_blocks if b["engine"] == "paddleocr")
            mathpix_count = sum(1 for b in final_blocks if b["engine"] == "mathpix")

            return {
                "text": all_text,
                "confidence": float(avg_confidence),
                "blocks": final_blocks,
                "metadata": {
                    "engine": "hybrid",
                    "paddle_blocks": paddle_count,
                    "mathpix_blocks": mathpix_count,
                    "total_blocks": len(final_blocks),
                    "mode": mode,
                    **paddle_result.get("metadata", {})
                }
            }

        except Exception as e:
            raise OcrError(f"Hybrid OCR failed: {str(e)}") from e

    def _is_formula_block(self, text: str, block: Dict) -> bool:
        r"""
        Detect if a text block contains mathematical formulas.

        Heuristics:
        - Contains LaTeX delimiters: $ $$ \( \) \[ \]
        - Contains math symbols: ∫ ∑ √ ∞ ≈ ≠ ≤ ≥ α β γ
        - Contains LaTeX commands: \frac \sum \int \sqrt
        - High density of special characters

        Args:
            text: Block text
            block: Block metadata

        Returns:
            True if block likely contains formulas
        """
        if not text:
            return False

        # Check for LaTeX delimiters
        latex_delimiters = ['$$', '$', '\\(', '\\)', '\\[', '\\]']
        if any(delim in text for delim in latex_delimiters):
            return True

        # Check for LaTeX commands
        latex_commands = [
            '\\frac', '\\sum', '\\int', '\\sqrt', '\\lim',
            '\\partial', '\\nabla', '\\infty', '\\alpha', '\\beta',
            '\\gamma', '\\delta', '\\theta', '\\lambda'
        ]
        if any(cmd in text for cmd in latex_commands):
            return True

        # Check for mathematical symbols
        math_symbols = [
            '∫', '∑', '∏', '√', '∞', '∂', '∇',
            '≈', '≠', '≤', '≥', '±', '×', '÷',
            '∈', '∉', '⊂', '⊃', '∀', '∃',
            '→', '↔', '⇒', '⇔',
            'α', 'β', 'γ', 'δ', 'θ', 'λ', 'μ', 'π', 'σ'
        ]
        symbol_count = sum(text.count(symbol) for symbol in math_symbols)

        if symbol_count > 3:  # More than 3 math symbols
            return True

        # Check special character density
        special_chars = set('+-*/=<>()[]{}^_∫∑∏√∞∂∇≈≠≤≥±×÷')
        special_count = sum(1 for c in text if c in special_chars)
        special_ratio = special_count / len(text) if len(text) > 0 else 0

        if special_ratio > 0.3:  # >30% special characters
            return True

        return False

    def _extract_region(self, image_bytes: bytes, bbox: tuple) -> bytes:
        """
        Extract a region from an image based on normalized bbox coordinates.

        Args:
            image_bytes: Full image as bytes
            bbox: Normalized bounding box (x0, y0, x1, y1) in range [0, 1]

        Returns:
            Cropped region as bytes

        Raises:
            OcrError: If region extraction fails
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size

            # Convert normalized coords to pixel coords
            x0, y0, x1, y1 = bbox
            pixel_box = (
                int(x0 * width),
                int(y0 * height),
                int(x1 * width),
                int(y1 * height)
            )

            # Crop region
            region = image.crop(pixel_box)

            # Convert to bytes
            output = io.BytesIO()
            region.save(output, format='PNG')
            return output.getvalue()

        except Exception as e:
            raise OcrError(f"Failed to extract image region: {str(e)}") from e

    def health_check(self) -> bool:
        """
        Check if OCR services are available.

        Returns:
            True if at least PaddleOCR is working
        """
        try:
            # PaddleOCR health check (required)
            if not self.paddle_client.health_check():
                logger.error("PaddleOCR health check failed")
                return False

            # MathPix health check (optional)
            if self.mathpix_client:
                if not self.mathpix_client.health_check():
                    logger.warning("MathPix health check failed, but PaddleOCR is available")

            return True

        except Exception as e:
            logger.error(f"Hybrid OCR health check failed: {str(e)}")
            return False
