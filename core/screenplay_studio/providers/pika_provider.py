"""
Pika Labs Provider for Video Generation

Budget-friendly option for AI video generation.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from .base_provider import BaseVideoProvider, GenerationResult

logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class PikaProvider(BaseVideoProvider):
    """Pika Labs provider"""

    name = "Pika Labs"
    cost_per_second = 0.02
    max_duration_seconds = 4
    supported_resolutions = ["1280x720", "1920x1080"]
    supported_aspect_ratios = ["16:9", "9:16", "1:1"]

    API_BASE = "https://api.pika.art/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("PIKA_API_KEY"))
        if not self.api_key:
            logger.debug("Pika: No API key provided")

    async def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 3,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
        camera_motion: str = "static",
        quality: str = "standard",
    ) -> GenerationResult:
        """Generate video with Pika Labs."""
        if not self.api_key:
            return GenerationResult(
                success=False,
                error="No API key configured"
            )

        if not HAS_AIOHTTP:
            return GenerationResult(success=False, error="aiohttp not installed")

        try:
            duration = min(duration_seconds, self.max_duration_seconds)
            enhanced_prompt = self._enhance_prompt(prompt, style, camera_motion)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "prompt": enhanced_prompt,
                "negative_prompt": negative_prompt,
                "options": {
                    "aspectRatio": aspect_ratio,
                    "frameRate": 24,
                    "camera": self._map_camera_motion(camera_motion),
                },
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.API_BASE}/generate",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return GenerationResult(
                            success=False,
                            error=f"Pika API error: {response.status} - {error_text}"
                        )

                    data = await response.json()

            generation_id = data.get("id")

            return GenerationResult(
                success=True,
                duration_seconds=duration,
                cost_usd=duration * self.cost_per_second,
                metadata={
                    "generation_id": generation_id,
                    "status": "processing",
                    "prompt": enhanced_prompt,
                }
            )

        except Exception as e:
            logger.error(f"Pika generation error: {e}")
            return GenerationResult(success=False, error=str(e))

    async def check_status(self, generation_id: str) -> GenerationResult:
        """Poll for generation status"""
        if not self.api_key or not HAS_AIOHTTP:
            return GenerationResult(success=False, error="Not configured")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.API_BASE}/generations/{generation_id}",
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        return GenerationResult(
                            success=False,
                            error=f"Status check failed: {response.status}"
                        )

                    data = await response.json()

            status = data.get("status")

            if status == "completed":
                return GenerationResult(
                    success=True,
                    url=data.get("video", {}).get("url"),
                    metadata={
                        "generation_id": generation_id,
                        "status": "completed",
                    }
                )
            elif status == "failed":
                return GenerationResult(
                    success=False,
                    error=data.get("error", "Generation failed"),
                )
            else:
                return GenerationResult(
                    success=True,
                    metadata={
                        "generation_id": generation_id,
                        "status": "processing",
                    }
                )

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return GenerationResult(success=False, error=str(e))

    async def download_video(
        self,
        generation_id: str,
        output_path: str,
    ) -> GenerationResult:
        """Download completed video"""
        if not HAS_AIOHTTP:
            return GenerationResult(success=False, error="aiohttp not installed")

        try:
            status_result = await self.check_status(generation_id)

            if not status_result.success or not status_result.url:
                return GenerationResult(
                    success=False,
                    error="Video not ready"
                )

            async with aiohttp.ClientSession() as session:
                async with session.get(status_result.url) as response:
                    if response.status != 200:
                        return GenerationResult(
                            success=False,
                            error=f"Download failed: {response.status}"
                        )

                    video_data = await response.read()

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(video_data)

            return GenerationResult(
                success=True,
                file_path=output_path,
            )

        except Exception as e:
            logger.error(f"Download error: {e}")
            return GenerationResult(success=False, error=str(e))

    def _enhance_prompt(self, prompt: str, style: str, camera_motion: str) -> str:
        """Enhance prompt for Pika"""
        style_map = {
            "cinematic": "cinematic, film quality, professional",
            "anime": "anime style, animation",
            "realistic": "photorealistic, natural",
        }
        style_text = style_map.get(style, style_map["cinematic"])

        return f"{prompt}, {style_text}"

    def _map_camera_motion(self, motion: str) -> dict:
        """Map camera motion to Pika camera settings"""
        motion_map = {
            "static": {"zoom": 0, "pan": 0, "tilt": 0, "rotate": 0},
            "zoom_in": {"zoom": 1, "pan": 0, "tilt": 0, "rotate": 0},
            "zoom_out": {"zoom": -1, "pan": 0, "tilt": 0, "rotate": 0},
            "pan_left": {"zoom": 0, "pan": -1, "tilt": 0, "rotate": 0},
            "pan_right": {"zoom": 0, "pan": 1, "tilt": 0, "rotate": 0},
            "tilt_up": {"zoom": 0, "pan": 0, "tilt": 1, "rotate": 0},
            "tilt_down": {"zoom": 0, "pan": 0, "tilt": -1, "rotate": 0},
        }
        return motion_map.get(motion, motion_map["static"])
