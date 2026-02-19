"""
Visual Designer Agent

Creates visual style guides for scenes:
- Color palettes
- Lighting design
- Location aesthetics
- Character visuals
- Atmosphere details
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import Scene, ShotList, Character, Language
from ..prompts.visual_designer import (
    SYSTEM_PROMPT,
    VISUAL_GUIDE_PROMPT,
)

logger = logging.getLogger(__name__)


class VisualDesignerAgent(BaseAgent):
    """Agent for creating visual style guides"""

    name = "VisualDesigner"
    description = "Creates visual style guides for scenes"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Create visual guide for a scene.

        Args:
            input_data: {
                "scene": Scene,
                "shot_list": ShotList,
                "characters": List[Character],
                "genre": str,
                "tone": str,
                "time_period": str,
                "reference_films": List[str],
                "language": Language,
            }
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            shot_list: ShotList = input_data.get("shot_list")
            characters: List[Character] = input_data.get("characters", [])
            genre = input_data.get("genre", "Drama")
            tone = input_data.get("tone", "neutral")
            time_period = input_data.get("time_period", "contemporary")
            reference_films = input_data.get("reference_films", [])

            if not scene:
                return AgentResult(
                    success=False, data=None, error="No scene provided"
                )

            char_descriptions = self._build_character_descriptions(
                characters, scene.characters_present
            )
            shot_summary = self._build_shot_summary(shot_list)
            location_type = self._extract_location_type(scene.heading.location)
            time_of_day = scene.heading.time

            prompt = VISUAL_GUIDE_PROMPT.format(
                scene_number=scene.scene_number,
                scene_heading=str(scene.heading),
                scene_summary=scene.summary,
                emotional_beat=scene.emotional_beat,
                mood=scene.mood or "neutral",
                time_of_day=time_of_day,
                location_type=location_type,
                character_descriptions=char_descriptions,
                shot_list_summary=shot_summary,
                genre=genre,
                tone=tone,
                time_period=time_period,
                reference_films=", ".join(reference_films) or "None specified",
            )

            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=3000,
            )

            visual_guide = self._parse_response(response)

            if not visual_guide:
                return AgentResult(
                    success=False, data=None,
                    error="Failed to parse visual guide response"
                )

            self.log_complete("Visual guide created")

            return AgentResult(
                success=True,
                data=visual_guide,
                tokens_used=tokens,
                cost_usd=tokens * 0.00001,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    def _build_character_descriptions(
        self, characters: List[Character], present_names: List[str]
    ) -> str:
        descriptions = []
        for char in characters:
            if char.name in present_names:
                desc = f"- {char.name}: {char.visual_description or char.description}"
                if char.age_range:
                    desc += f" ({char.age_range})"
                descriptions.append(desc)
        return "\n".join(descriptions) if descriptions else "No character descriptions available"

    def _build_shot_summary(self, shot_list: ShotList) -> str:
        if not shot_list or not shot_list.shots:
            return "No shot list available"

        summaries = []
        for shot in shot_list.shots[:5]:
            summaries.append(
                f"- {shot.shot_number}: {shot.shot_type.value} - {shot.description[:50]}"
            )
        if len(shot_list.shots) > 5:
            summaries.append(f"- ... and {len(shot_list.shots) - 5} more shots")

        return "\n".join(summaries)

    def _extract_location_type(self, location: str) -> str:
        location_lower = location.lower()

        if any(x in location_lower for x in ["house", "home", "apartment", "bedroom", "kitchen", "living"]):
            return "residential"
        elif any(x in location_lower for x in ["office", "meeting", "conference", "corporate"]):
            return "corporate/office"
        elif any(x in location_lower for x in ["street", "road", "alley", "sidewalk"]):
            return "street/urban"
        elif any(x in location_lower for x in ["cafe", "restaurant", "bar", "coffee"]):
            return "dining/social"
        elif any(x in location_lower for x in ["hospital", "clinic", "doctor"]):
            return "medical"
        elif any(x in location_lower for x in ["park", "garden", "forest", "beach", "river"]):
            return "nature/outdoor"
        elif any(x in location_lower for x in ["temple", "pagoda", "church"]):
            return "religious"
        else:
            return "general"

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
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
