"""
Runway Gen-3 Provider for Video Generation

Balanced quality and cost option for AI video generation.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional

from .base_provider import BaseVideoProvider, GenerationResult

logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class RunwayProvider(BaseVideoProvider):
    """Runway Gen-3 Alpha provider"""

    name = "Runway Gen-3"
    cost_per_second = 0.05
    max_duration_seconds = 10
    supported_resolutions = ["1280x720", "1920x1080"]
    supported_aspect_ratios = ["16:9", "9:16", "1:1"]

    API_BASE = "https://api.runwayml.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("RUNWAY_API_KEY"))
        if not self.api_key:
            logger.debug("Runway: No API key provided")

    async def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 5,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
        camera_motion: str = "static",
        quality: str = "standard",
    ) -> GenerationResult:
        """Generate video with Runway Gen-3."""
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
                "X-Runway-Version": "2024-09-13",
            }

            payload = {
                "promptText": enhanced_prompt,
                "model": "gen3a_turbo",
                "duration": duration,
                "ratio": aspect_ratio,
                "watermark": False,
            }

            if negative_prompt:
                payload["negativePrompt"] = negative_prompt

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.API_BASE}/image_to_video",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return GenerationResult(
                            success=False,
                            error=f"Runway API error: {response.status} - {error_text}"
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
            logger.error(f"Runway generation error: {e}")
            return GenerationResult(success=False, error=str(e))

    async def check_status(self, generation_id: str) -> GenerationResult:
        """Poll for generation status"""
        if not self.api_key or not HAS_AIOHTTP:
            return GenerationResult(success=False, error="Not configured")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Runway-Version": "2024-09-13",
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.API_BASE}/tasks/{generation_id}",
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        return GenerationResult(
                            success=False,
                            error=f"Status check failed: {response.status}"
                        )

                    data = await response.json()

            status = data.get("status")

            if status == "SUCCEEDED":
                output = data.get("output", [{}])[0]
                return GenerationResult(
                    success=True,
                    url=output.get("url"),
                    metadata={
                        "generation_id": generation_id,
                        "status": "completed",
                    }
                )
            elif status == "FAILED":
                return GenerationResult(
                    success=False,
                    error=data.get("failure", "Generation failed"),
                )
            else:
                return GenerationResult(
                    success=True,
                    metadata={
                        "generation_id": generation_id,
                        "status": "processing",
                        "progress": data.get("progress", 0),
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

            if not status_result.success:
                return status_result

            if not status_result.url:
                return GenerationResult(
                    success=False,
                    error="Video not ready yet"
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
                metadata={"generation_id": generation_id}
            )

        except Exception as e:
            logger.error(f"Download error: {e}")
            return GenerationResult(success=False, error=str(e))

    async def wait_for_completion(
        self,
        generation_id: str,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
    ) -> GenerationResult:
        """Wait for generation to complete"""
        elapsed = 0

        while elapsed < timeout_seconds:
            result = await self.check_status(generation_id)

            if not result.success:
                return result

            if result.metadata.get("status") == "completed":
                return result

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return GenerationResult(
            success=False,
            error=f"Timeout after {timeout_seconds}s"
        )

    def _enhance_prompt(self, prompt: str, style: str, camera_motion: str) -> str:
        """Enhance prompt for cinematic quality"""
        style_map = {
            "cinematic": "cinematic, film quality, professional cinematography",
            "documentary": "documentary style, handheld camera, natural lighting",
            "dramatic": "dramatic lighting, high contrast, moody atmosphere",
            "bright": "bright, vibrant colors, well-lit scene",
        }
        style_text = style_map.get(style, style_map["cinematic"])

        motion_map = {
            "static": "static camera, locked off shot",
            "pan_left": "slow pan left",
            "pan_right": "slow pan right",
            "dolly_in": "slow dolly in, push in",
            "dolly_out": "slow dolly out, pull out",
            "tracking": "tracking shot, following movement",
            "handheld": "subtle handheld movement",
        }
        motion_text = motion_map.get(camera_motion, "")

        enhanced = f"{prompt}. {style_text}"
        if motion_text:
            enhanced += f". Camera: {motion_text}"

        return enhanced
