"""
DALL-E Provider for Storyboard Images

Uses OpenAI's DALL-E 3 for high-quality storyboard images.
"""

import os
import logging
import base64
from pathlib import Path
from typing import Optional

from .base_provider import BaseImageProvider, GenerationResult

logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class DallEProvider(BaseImageProvider):
    """DALL-E 3 provider for storyboard images"""

    name = "DALL-E 3"
    cost_per_image = 0.04  # Standard quality
    max_resolution = "1792x1024"
    supported_styles = ["cinematic", "natural", "vivid"]

    API_URL = "https://api.openai.com/v1/images/generations"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"))
        if not self.api_key:
            logger.debug("DALL-E: No API key provided")

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        quality: str = "standard",
    ) -> GenerationResult:
        """Generate storyboard image."""
        if not self.api_key:
            return GenerationResult(
                success=False,
                error="No API key configured"
            )

        if not HAS_AIOHTTP:
            return GenerationResult(
                success=False,
                error="aiohttp not installed"
            )

        try:
            # Map aspect ratio to DALL-E sizes
            size_map = {
                "16:9": "1792x1024",
                "1:1": "1024x1024",
                "9:16": "1024x1792",
            }
            size = size_map.get(aspect_ratio, "1792x1024")

            # Enhance prompt for cinematic storyboard
            enhanced_prompt = self._enhance_prompt(prompt, negative_prompt, style)

            # Map style
            dalle_style = "vivid" if style in ["vivid", "cinematic"] else "natural"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "dall-e-3",
                "prompt": enhanced_prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "style": dalle_style,
                "response_format": "b64_json",
            }

            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return GenerationResult(
                            success=False,
                            error=f"DALL-E API error: {response.status} - {error_text}"
                        )

                    data = await response.json()

            # Extract image data
            image_data = data["data"][0]
            b64_image = image_data["b64_json"]
            revised_prompt = image_data.get("revised_prompt", prompt)

            # Calculate cost
            cost = 0.04 if quality == "standard" else 0.08

            return GenerationResult(
                success=True,
                cost_usd=cost,
                metadata={
                    "b64_image": b64_image,
                    "revised_prompt": revised_prompt,
                    "model": "dall-e-3",
                    "size": size,
                    "quality": quality,
                }
            )

        except Exception as e:
            logger.error(f"DALL-E generation error: {e}")
            return GenerationResult(
                success=False,
                error=str(e)
            )

    async def check_status(self, generation_id: str) -> GenerationResult:
        """DALL-E is synchronous, no status check needed"""
        return GenerationResult(success=True)

    def _enhance_prompt(self, prompt: str, negative_prompt: str, style: str) -> str:
        """Enhance prompt for cinematic storyboard quality"""
        enhancements = [
            "cinematic film still",
            "professional cinematography",
            "movie scene",
            "dramatic lighting",
            "high production value",
        ]

        enhanced = f"{prompt}. {', '.join(enhancements)}"

        if negative_prompt:
            enhanced += f". Avoid: {negative_prompt}"

        return enhanced

    def save_image(self, b64_data: str, filepath: str) -> str:
        """Save base64 image data to file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        image_bytes = base64.b64decode(b64_data)
        path.write_bytes(image_bytes)

        logger.info(f"Saved image: {filepath}")
        return filepath
