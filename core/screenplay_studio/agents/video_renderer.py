"""
Video Renderer Agent

Orchestrates video generation across multiple providers.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent, AgentResult
from ..models import VideoPrompt, VideoClip, VideoProvider
from ..providers.runway_provider import RunwayProvider
from ..providers.veo_provider import VeoProvider
from ..providers.pika_provider import PikaProvider

logger = logging.getLogger(__name__)


class VideoRendererAgent(BaseAgent):
    """Agent for rendering AI-generated videos"""

    name = "VideoRenderer"
    description = "Generates video clips from prompts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.providers = {
            VideoProvider.RUNWAY: RunwayProvider(),
            VideoProvider.VEO: VeoProvider(),
            VideoProvider.PIKA: PikaProvider(),
        }

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Generate videos for all prompts.

        Args:
            input_data: {
                "prompts": List[VideoPrompt],
                "output_dir": str,
                "provider": VideoProvider,
                "max_concurrent": int,
            }
        """
        self.log_start("Starting video generation")

        try:
            prompts: List[VideoPrompt] = input_data.get("prompts", [])
            output_dir: str = input_data.get("output_dir", "outputs/video")
            provider: VideoProvider = input_data.get("provider", VideoProvider.RUNWAY)
            max_concurrent: int = input_data.get("max_concurrent", 3)

            if not prompts:
                return AgentResult(
                    success=False, data=None, error="No prompts provided"
                )

            video_provider = self.providers.get(provider)
            if not video_provider:
                return AgentResult(
                    success=False, data=None,
                    error=f"Unknown provider: {provider}"
                )

            Path(output_dir).mkdir(parents=True, exist_ok=True)

            video_clips = []
            total_cost = 0.0

            for i in range(0, len(prompts), max_concurrent):
                batch = prompts[i:i + max_concurrent]

                tasks = [
                    self._generate_single_video(
                        prompt=p, provider=video_provider,
                        output_dir=output_dir,
                    )
                    for p in batch
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Generation error: {result}")
                    elif result and result.get("clip"):
                        video_clips.append(result["clip"])
                        total_cost += result.get("cost", 0)

            self.log_complete(f"{len(video_clips)} videos generated")

            return AgentResult(
                success=True,
                data={
                    "clips": video_clips,
                    "total_count": len(video_clips),
                    "provider": provider.value,
                },
                tokens_used=0,
                cost_usd=total_cost,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    async def _generate_single_video(
        self, prompt: VideoPrompt, provider, output_dir: str,
    ) -> Optional[Dict]:
        """Generate a single video clip"""
        try:
            gen_result = await provider.generate_video(
                prompt=prompt.prompt,
                negative_prompt=prompt.negative_prompt,
                duration_seconds=prompt.duration_seconds,
                aspect_ratio=prompt.aspect_ratio,
                style=prompt.style,
                camera_motion=prompt.camera_motion,
                quality=prompt.quality_preset,
            )

            if not gen_result.success:
                logger.error(f"Generation failed for {prompt.shot_id}: {gen_result.error}")
                return None

            generation_id = gen_result.metadata.get("generation_id")

            if not generation_id:
                logger.error(f"No generation ID for {prompt.shot_id}")
                return None

            if hasattr(provider, 'wait_for_completion'):
                completion_result = await provider.wait_for_completion(
                    generation_id, timeout_seconds=300,
                )

                if not completion_result.success:
                    logger.error(f"Generation timeout for {prompt.shot_id}")
                    return None

            output_path = f"{output_dir}/{prompt.shot_id}.mp4"
            download_result = await provider.download_video(
                generation_id, output_path,
            )

            if not download_result.success:
                logger.error(f"Download failed for {prompt.shot_id}: {download_result.error}")
                return None

            clip = VideoClip(
                shot_id=prompt.shot_id,
                provider=prompt.provider,
                file_path=output_path,
                duration_seconds=prompt.duration_seconds,
                prompt_used=prompt.prompt,
                cost_usd=gen_result.cost_usd,
                is_selected=True,
            )

            return {"clip": clip, "cost": gen_result.cost_usd}

        except Exception as e:
            logger.error(f"Error generating video for {prompt.shot_id}: {e}")
            return None

    async def generate_single(
        self, prompt: VideoPrompt, output_path: str,
    ) -> Optional[VideoClip]:
        """Generate a single video (convenience method)"""
        provider = self.providers.get(prompt.provider)
        if not provider:
            return None

        result = await self._generate_single_video(
            prompt=prompt, provider=provider,
            output_dir=str(Path(output_path).parent),
        )

        return result.get("clip") if result else None
