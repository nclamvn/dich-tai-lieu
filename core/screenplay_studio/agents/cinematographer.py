"""
Cinematographer Agent

Designs professional shot lists for each scene:
- Shot types and compositions
- Camera angles and movements
- Lens selections
- Lighting notes
- Scene coverage
"""

import json
import logging
from typing import Dict, Any

from .base_agent import BaseAgent, AgentResult
from ..models import (
    Scene, Shot, ShotList, ShotType,
    CameraMovement, CameraAngle, Language,
    DialogueBlock, ActionBlock,
)
from ..prompts.cinematographer import (
    SYSTEM_PROMPT,
    SHOT_LIST_PROMPT,
    SHOT_LIST_PROMPT_VI,
)

logger = logging.getLogger(__name__)


class CinematographerAgent(BaseAgent):
    """Agent for designing shot lists"""

    name = "Cinematographer"
    description = "Designs professional shot lists for scenes"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Create shot list for a scene.

        Args:
            input_data: {
                "scene": Scene,
                "genre": str,
                "tone": str,
                "reference_films": List[str],
                "language": Language,
            }
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            genre = input_data.get("genre", "Drama")
            tone = input_data.get("tone", "neutral")
            reference_films = input_data.get("reference_films", [])
            language = input_data.get("language", Language.ENGLISH)

            if not scene:
                return AgentResult(
                    success=False, data=None, error="No scene provided"
                )

            scene_content = self._build_scene_content(scene)

            template = SHOT_LIST_PROMPT_VI if language == Language.VIETNAMESE else SHOT_LIST_PROMPT
            prompt = template.format(
                scene_number=scene.scene_number,
                scene_heading=str(scene.heading),
                scene_summary=scene.summary,
                emotional_beat=scene.emotional_beat,
                mood=scene.mood or "neutral",
                characters_present=", ".join(scene.characters_present),
                scene_content=scene_content[:3000],
                genre=genre,
                tone=tone,
                reference_films=", ".join(reference_films) or "None specified",
            )

            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=4000,
            )

            shot_data = self._parse_response(response)

            if not shot_data:
                return AgentResult(
                    success=False, data=None,
                    error="Failed to parse shot list response"
                )

            shot_list = self._create_shot_list(scene.scene_number, shot_data)

            self.log_complete(f"{len(shot_list.shots)} shots designed")

            return AgentResult(
                success=True,
                data=shot_list,
                tokens_used=tokens,
                cost_usd=tokens * 0.00001,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    def _build_scene_content(self, scene: Scene) -> str:
        """Build scene content from elements"""
        lines = [str(scene.heading), ""]

        for element in scene.elements:
            if isinstance(element, ActionBlock):
                lines.append(element.text)
            elif isinstance(element, DialogueBlock):
                lines.append(f"{element.character}: {element.dialogue}")
            lines.append("")

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None

    def _create_shot_list(self, scene_number: int, data: Dict) -> ShotList:
        """Create ShotList from parsed data"""
        shots = []

        for shot_data in data.get("shots", []):
            shot_type = self._map_shot_type(
                shot_data.get("shot_type", "medium")
            )

            camera = shot_data.get("camera", {})
            angle = self._map_angle(camera.get("angle", "eye_level"))
            movement = self._map_movement(camera.get("movement", "static"))

            lighting = shot_data.get("lighting", {})
            lighting_notes = (
                f"{lighting.get('type', 'natural')}, "
                f"{lighting.get('mood', 'neutral')}, "
                f"{lighting.get('direction', 'front')}"
            )

            shot = Shot(
                shot_number=shot_data.get("shot_number", f"{scene_number}A"),
                shot_type=shot_type,
                description=shot_data.get("description", ""),
                camera_angle=angle,
                camera_movement=movement,
                lens=camera.get("lens", "50mm"),
                duration_seconds=shot_data.get("duration_seconds", 3),
                lighting_notes=lighting_notes,
                color_notes=shot_data.get("composition_notes", ""),
                audio_notes=shot_data.get("audio_notes", ""),
            )
            shots.append(shot)

        return ShotList(
            scene_number=scene_number,
            shots=shots,
            visual_style=data.get("visual_approach", ""),
        )

    def _map_shot_type(self, type_str: str) -> ShotType:
        mapping = {
            "extreme_wide": ShotType.EXTREME_WIDE,
            "wide": ShotType.WIDE,
            "full": ShotType.FULL,
            "medium_wide": ShotType.MEDIUM_WIDE,
            "medium": ShotType.MEDIUM,
            "medium_close": ShotType.MEDIUM_CLOSE,
            "close_up": ShotType.CLOSE_UP,
            "closeup": ShotType.CLOSE_UP,
            "extreme_close_up": ShotType.EXTREME_CLOSE_UP,
            "pov": ShotType.POV,
            "over_shoulder": ShotType.OVER_SHOULDER,
            "two_shot": ShotType.TWO_SHOT,
            "insert": ShotType.INSERT,
        }
        return mapping.get(type_str.lower(), ShotType.MEDIUM)

    def _map_angle(self, angle_str: str) -> CameraAngle:
        mapping = {
            "eye_level": CameraAngle.EYE_LEVEL,
            "high": CameraAngle.HIGH,
            "low": CameraAngle.LOW,
            "dutch": CameraAngle.DUTCH,
            "birds_eye": CameraAngle.BIRDS_EYE,
            "worms_eye": CameraAngle.WORMS_EYE,
        }
        return mapping.get(angle_str.lower(), CameraAngle.EYE_LEVEL)

    def _map_movement(self, movement_str: str) -> CameraMovement:
        mapping = {
            "static": CameraMovement.STATIC,
            "pan_left": CameraMovement.PAN_LEFT,
            "pan_right": CameraMovement.PAN_RIGHT,
            "tilt_up": CameraMovement.TILT_UP,
            "tilt_down": CameraMovement.TILT_DOWN,
            "dolly_in": CameraMovement.DOLLY_IN,
            "dolly_out": CameraMovement.DOLLY_OUT,
            "tracking": CameraMovement.TRACKING,
            "crane_up": CameraMovement.CRANE_UP,
            "crane_down": CameraMovement.CRANE_DOWN,
            "handheld": CameraMovement.HANDHELD,
            "steadicam": CameraMovement.STEADICAM,
            "zoom_in": CameraMovement.ZOOM_IN,
            "zoom_out": CameraMovement.ZOOM_OUT,
        }
        return mapping.get(movement_str.lower(), CameraMovement.STATIC)
