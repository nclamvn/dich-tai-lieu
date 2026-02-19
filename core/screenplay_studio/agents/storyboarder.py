"""
Storyboarder Agent

Generates storyboard images for each shot using AI image generation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .base_agent import BaseAgent, AgentResult
from ..models import Shot, ShotList, Scene
from ..providers.dalle_provider import DallEProvider

logger = logging.getLogger(__name__)


class StoryboarderAgent(BaseAgent):
    """Agent for generating storyboard images"""

    name = "Storyboarder"
    description = "Generates storyboard images for shots"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_provider = DallEProvider()

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Generate storyboard images for a shot list.

        Args:
            input_data: {
                "scene": Scene,
                "shot_list": ShotList,
                "visual_guide": Dict,
                "output_dir": str,
            }
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            shot_list: ShotList = input_data.get("shot_list")
            visual_guide: Dict = input_data.get("visual_guide", {})
            output_dir: str = input_data.get("output_dir", "outputs/storyboard")

            if not scene or not shot_list:
                return AgentResult(
                    success=False, data=None,
                    error="Scene and shot list required"
                )

            scene_dir = Path(output_dir) / f"scene_{scene.scene_number:03d}"
            scene_dir.mkdir(parents=True, exist_ok=True)

            generated_images = []
            total_cost = 0.0

            for shot in shot_list.shots:
                prompt = self._build_image_prompt(
                    shot=shot, scene=scene, visual_guide=visual_guide,
                )

                result = await self.image_provider.generate_image(
                    prompt=prompt,
                    negative_prompt="blurry, low quality, text, watermark, logo",
                    style="cinematic",
                    aspect_ratio="16:9",
                    quality="standard",
                )

                if result.success and result.metadata.get("b64_image"):
                    image_path = str(scene_dir / f"{shot.shot_number}.png")
                    self.image_provider.save_image(
                        result.metadata["b64_image"], image_path
                    )

                    generated_images.append({
                        "shot_number": shot.shot_number,
                        "image_path": image_path,
                        "prompt": prompt,
                    })

                    shot.storyboard_image = image_path
                    total_cost += result.cost_usd
                else:
                    logger.warning(
                        f"Failed to generate image for shot {shot.shot_number}: "
                        f"{result.error}"
                    )

            self.log_complete(f"{len(generated_images)} images generated")

            return AgentResult(
                success=True,
                data={
                    "images": generated_images,
                    "scene_number": scene.scene_number,
                    "total_images": len(generated_images),
                },
                tokens_used=0,
                cost_usd=total_cost,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    def _build_image_prompt(
        self, shot: Shot, scene: Scene, visual_guide: Dict,
    ) -> str:
        """Build detailed image prompt for a shot"""
        prompt_parts = [shot.description]

        shot_type_desc = {
            "extreme_wide": "extreme wide shot, establishing shot",
            "wide": "wide shot showing full environment",
            "medium": "medium shot from waist up",
            "close_up": "close-up shot of face",
            "extreme_close_up": "extreme close-up, detail shot",
            "pov": "point of view shot, first person perspective",
            "over_shoulder": "over the shoulder shot, showing conversation",
            "two_shot": "two-shot, two people in frame",
        }
        desc = shot_type_desc.get(shot.shot_type.value, "")
        if desc:
            prompt_parts.append(desc)

        angle_desc = {
            "eye_level": "eye level camera angle",
            "high": "high angle looking down",
            "low": "low angle looking up",
            "dutch": "dutch angle, tilted frame",
            "birds_eye": "bird's eye view, overhead shot",
        }
        desc = angle_desc.get(shot.camera_angle.value, "")
        if desc:
            prompt_parts.append(desc)

        if visual_guide:
            color_palette = visual_guide.get("color_palette", {})
            if color_palette:
                temp = color_palette.get("overall_temperature", "neutral")
                prompt_parts.append(f"{temp} color temperature")

            lighting = visual_guide.get("lighting_design", {})
            if lighting:
                mood = lighting.get("mood_lighting", "")
                if mood:
                    prompt_parts.append(mood)

        if shot.lighting_notes:
            prompt_parts.append(shot.lighting_notes)

        prompt_parts.append(f"Scene: {scene.heading.location}")
        prompt_parts.append(f"Time: {scene.heading.time}")

        return ", ".join([p for p in prompt_parts if p])

    async def generate_single_image(
        self, shot: Shot, prompt: str, output_path: str,
    ) -> Optional[str]:
        """Generate a single storyboard image"""
        result = await self.image_provider.generate_image(
            prompt=prompt, style="cinematic", aspect_ratio="16:9",
        )

        if result.success and result.metadata.get("b64_image"):
            self.image_provider.save_image(
                result.metadata["b64_image"], output_path
            )
            return output_path

        return None
