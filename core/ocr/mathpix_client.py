#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathPix Client - Specialized OCR for Mathematical Formulas
Implements OcrClient protocol using MathPix API for high-accuracy formula recognition.
"""

import io
import time
import base64
import logging
from typing import Optional, Dict
import os

from .base import OcrClient, OcrError, OcrConnectionError, OcrQuotaError, OcrInvalidInputError

logger = logging.getLogger(__name__)


class MathPixOcrClient(OcrClient):
    """
    MathPix-based OCR client for mathematical formula recognition.

    Features:
    - Specialized for LaTeX formula recognition
    - High accuracy for complex mathematical notation
    - Supports handwritten formulas
    - Returns LaTeX format
    - Flexible API key configuration (env var or per-request)

    API Documentation: https://docs.mathpix.com/

    Configuration:
        Environment variables (server-level default):
            MATHPIX_APP_ID=your_app_id
            MATHPIX_APP_KEY=your_app_key

        Or per-request (Web UI):
            client = MathPixOcrClient(app_id="...", app_key="...")

    Usage:
        # Using env vars
        client = MathPixOcrClient()

        # Using explicit keys
        client = MathPixOcrClient(app_id="...", app_key="...")

        latex = client.extract(image_bytes)
    """

    API_ENDPOINT = "https://api.mathpix.com/v3/text"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize MathPix OCR client.

        Args:
            app_id: MathPix App ID (or from MATHPIX_APP_ID env var)
            app_key: MathPix App Key (or from MATHPIX_APP_KEY env var)
            timeout: Request timeout in seconds
            max_retries: Max retry attempts on failure

        Raises:
            OcrError: If API credentials are not provided
        """
        # Get API credentials from args or environment
        self.app_id = app_id or os.getenv('MATHPIX_APP_ID')
        self.app_key = app_key or os.getenv('MATHPIX_APP_KEY')

        if not self.app_id or not self.app_key:
            raise OcrError(
                "MathPix API credentials not found. Provide them via:\n"
                "  1. Environment variables: MATHPIX_APP_ID, MATHPIX_APP_KEY\n"
                "  2. Constructor: MathPixOcrClient(app_id='...', app_key='...')\n"
                "\nGet credentials from: https://mathpix.com/ocr"
            )

        self.timeout = timeout
        self.max_retries = max_retries

        # Check if httpx is available
        try:
            import httpx
            self.httpx = httpx
        except ImportError:
            raise OcrError(
                "httpx is not installed. Install it with:\n"
                "  pip install httpx"
            )

        logger.info("MathPix OCR client initialized")

    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode('utf-8')

    def extract(
        self,
        image_bytes: bytes,
        mode: str = "document",
        language: Optional[str] = None
    ) -> str:
        """
        Extract LaTeX text from image containing formulas.

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode ("document" or "handwriting")
            language: Language hint (optional)

        Returns:
            Extracted LaTeX text

        Raises:
            OcrQuotaError: If API quota exceeded
            OcrConnectionError: If API is unreachable
            OcrInvalidInputError: If image is invalid
            OcrError: For other API errors
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
        Extract structured LaTeX data with confidence scores.

        Args:
            image_bytes: Image data as bytes
            mode: OCR mode ("document" or "handwriting")
            language: Language hint (optional)

        Returns:
            Dictionary with:
                - text: Extracted LaTeX text
                - confidence: Confidence score (0.0-1.0)
                - blocks: List of formula blocks
                - metadata: API response metadata

        Raises:
            OcrQuotaError: If API quota exceeded
            OcrConnectionError: If API is unreachable
            OcrInvalidInputError: If image is invalid
            OcrError: For other API errors
        """
        # Encode image
        image_b64 = self._encode_image(image_bytes)

        # Prepare request payload
        payload = {
            "src": f"data:image/png;base64,{image_b64}",
            "formats": ["text", "data", "latex_styled"],
            "data_options": {
                "include_asciimath": True,
                "include_latex": True
            }
        }

        # Add metadata options
        if mode == "handwriting":
            payload["ocr"] = ["handwriting"]

        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "Content-Type": "application/json"
        }

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                with self.httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.API_ENDPOINT,
                        json=payload,
                        headers=headers
                    )

                    # Handle response
                    if response.status_code == 200:
                        return self._parse_response(response.json())

                    elif response.status_code == 429:
                        # Rate limit exceeded
                        raise OcrQuotaError(
                            "MathPix API rate limit exceeded. "
                            "Please wait or upgrade your plan."
                        )

                    elif response.status_code in [400, 422]:
                        # Invalid input
                        error_msg = response.json().get("error", "Invalid image")
                        raise OcrInvalidInputError(f"MathPix API error: {error_msg}")

                    elif response.status_code in [401, 403]:
                        # Authentication error
                        raise OcrError(
                            "MathPix API authentication failed. "
                            "Check your APP_ID and APP_KEY."
                        )

                    else:
                        # Other error
                        error_msg = response.json().get("error", f"HTTP {response.status_code}")
                        raise OcrError(f"MathPix API error: {error_msg}")

            except self.httpx.ConnectError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"MathPix connection failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise OcrConnectionError(
                        f"Failed to connect to MathPix API after {self.max_retries} attempts"
                    ) from e

            except (OcrQuotaError, OcrInvalidInputError, OcrError):
                # Don't retry these errors
                raise

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"MathPix request failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise OcrError(f"MathPix OCR failed: {str(e)}") from e

        raise OcrError("Max retries exceeded")

    def _parse_response(self, response_data: Dict) -> Dict:
        """
        Parse MathPix API response into standardized format.

        Args:
            response_data: Raw API response

        Returns:
            Standardized OCR result dictionary
        """
        # Extract text (prefer LaTeX format)
        text = response_data.get("latex_styled", "")
        if not text:
            text = response_data.get("text", "")

        # Extract confidence
        confidence = response_data.get("confidence", 0.0)

        # Extract blocks from data field
        blocks = []
        data = response_data.get("data", [])

        for item in data:
            if item.get("type") == "asciimath" or item.get("type") == "latex":
                block = {
                    "text": item.get("value", ""),
                    "bbox": (0, 0, 1, 1),  # MathPix doesn't return bbox, use full image
                    "confidence": confidence,
                    "type": item.get("type")
                }
                blocks.append(block)

        # Build metadata
        metadata = {
            "engine": "mathpix",
            "request_id": response_data.get("request_id"),
            "is_handwritten": response_data.get("is_handwritten", False),
            "is_printed": response_data.get("is_printed", True),
            "auto_rotate_confidence": response_data.get("auto_rotate_confidence"),
            "auto_rotate_degrees": response_data.get("auto_rotate_degrees")
        }

        return {
            "text": text,
            "confidence": float(confidence),
            "blocks": blocks,
            "metadata": metadata
        }

    def health_check(self) -> bool:
        """
        Check if MathPix API is accessible.

        Returns:
            True if API is reachable and credentials are valid
        """
        try:
            # Create a minimal test request
            test_payload = {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "formats": ["text"]
            }

            headers = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-Type": "application/json"
            }

            with self.httpx.Client(timeout=10) as client:
                response = client.post(
                    self.API_ENDPOINT,
                    json=test_payload,
                    headers=headers
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"MathPix health check failed: {str(e)}")
            return False
