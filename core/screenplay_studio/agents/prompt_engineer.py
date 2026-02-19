"""
Prompt Engineer Agent

Converts shots and visual guides into optimized AI video prompts.
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import Shot, ShotList, VideoPrompt, VideoProvider
from ..prompts.prompt_engineer import (
    SYSTEM_PROMPT,
    VIDEO_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class PromptEngineerAgent(BaseAgent):
    """Agent for creating optimized AI video prompts"""

    name = "PromptEngineer"
    description = "Creates optimized AI video prompts from shots"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Create video prompts for shots.

        Args:
            input_data: {
                "shot_list": ShotList,
                "visual_guide": Dict,
                "characters": List,
                "provider": VideoProvider,
            }
        """
        self.log_start("Creating video prompts")

        try:
            shot_list: ShotList = input_data.get("shot_list")
            visual_guide: Dict = input_data.get("visual_guide", {})
            characters: List = input_data.get("characters", [])
            provider: VideoProvider = input_data.get("provider", VideoProvider.RUNWAY)

            if not shot_list:
                return AgentResult(
                    success=False, data=None, error="Shot list required"
                )

            video_prompts = []
            total_tokens = 0

            visual_summary = self._build_visual_summary(visual_guide)
            char_visuals = self._build_character_visuals(characters)

            for shot in shot_list.shots:
                prompt_result = await self._create_shot_prompt(
                    shot=shot,
                    visual_summary=visual_summary,
                    char_visuals=char_visuals,
                    provider=provider,
                )

                if prompt_result["success"]:
                    video_prompts.append(prompt_result["prompt"])
                    total_tokens += prompt_result.get("tokens", 0)

            self.log_complete(f"{len(video_prompts)} prompts created")

            return AgentResult(
                success=True,
                data=video_prompts,
                tokens_used=total_tokens,
                cost_usd=total_tokens * 0.00001,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    async def _create_shot_prompt(
        self,
        shot: Shot,
        visual_summary: str,
        char_visuals: str,
        provider: VideoProvider,
    ) -> Dict:
        """Create optimized prompt for a single shot"""
        try:
            prompt = VIDEO_PROMPT_TEMPLATE.format(
                shot_number=shot.shot_number,
                shot_type=shot.shot_type.value,
                shot_description=shot.description,
                camera_angle=shot.camera_angle.value,
                camera_movement=shot.camera_movement.value,
                duration=shot.duration_seconds,
                lighting_notes=shot.lighting_notes,
                visual_guide_summary=visual_summary,
                character_visuals=char_visuals,
                provider=provider.value,
            )

            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=1500,
            )

            prompt_data = self._parse_response(response)

            if not prompt_data:
                return {
                    "success": True,
                    "prompt": self._create_fallback_prompt(shot, provider),
                    "tokens": 0,
                }

            # Extract scene number from shot_number (e.g., "1A" -> 1)
            scene_num = 1
            for ch in shot.shot_number:
                if ch.isdigit():
                    scene_num = int(ch)
                    break

            video_prompt = VideoPrompt(
                shot_id=shot.shot_number,
                scene_number=scene_num,
                prompt=prompt_data.get("prompt", shot.description),
                negative_prompt=prompt_data.get("negative_prompt", "blurry, low quality"),
                duration_seconds=shot.duration_seconds,
                aspect_ratio=prompt_data.get("technical_settings", {}).get("aspect_ratio", "16:9"),
                style="cinematic",
                camera_motion=prompt_data.get("camera_motion", shot.camera_movement.value),
                quality_preset="standard",
                provider=provider,
                provider_params=prompt_data.get("provider_specific", {}).get(provider.value, {}),
            )

            shot.ai_prompt = video_prompt.prompt

            return {
                "success": True,
                "prompt": video_prompt,
                "tokens": tokens,
            }

        except Exception as e:
            logger.error(f"Error creating prompt for shot {shot.shot_number}: {e}")
            return {
                "success": True,
                "prompt": self._create_fallback_prompt(shot, provider),
                "tokens": 0,
            }

    def _create_fallback_prompt(self, shot: Shot, provider: VideoProvider) -> VideoPrompt:
        """Create a simple fallback prompt"""
        prompt_text = (
            f"{shot.description}. "
            f"{shot.shot_type.value} shot, {shot.camera_angle.value} angle, "
            f"cinematic, professional cinematography, film quality"
        )

        return VideoPrompt(
            shot_id=shot.shot_number,
            scene_number=1,
            prompt=prompt_text,
            negative_prompt="blurry, low quality, text, watermark",
            duration_seconds=shot.duration_seconds,
            aspect_ratio="16:9",
            style="cinematic",
            camera_motion=shot.camera_movement.value,
            quality_preset="standard",
            provider=provider,
        )

    def _build_visual_summary(self, visual_guide: Dict) -> str:
        if not visual_guide:
            return "No visual guide available"

        parts = []
        color = visual_guide.get("color_palette", {})
        if color:
            parts.append(f"Color: {color.get('overall_temperature', 'neutral')} temperature")

        lighting = visual_guide.get("lighting_design", {})
        if lighting:
            parts.append(f"Lighting: {lighting.get('mood_lighting', 'natural')}")

        atmosphere = visual_guide.get("atmosphere", {})
        if atmosphere:
            weather = atmosphere.get("weather", "")
            if weather:
                parts.append(f"Weather: {weather}")

        return ". ".join(parts) if parts else "Cinematic style"

    def _build_character_visuals(self, characters: List) -> str:
        if not characters:
            return "No specific character descriptions"

        descriptions = []
        for char in characters[:3]:
            if hasattr(char, 'visual_description') and char.visual_description:
                descriptions.append(f"{char.name}: {char.visual_description}")
            elif hasattr(char, 'description'):
                descriptions.append(f"{char.name}: {char.description}")

        return "\n".join(descriptions) if descriptions else "No specific character descriptions"

    def _parse_response(self, response: str) -> Dict:
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return None
