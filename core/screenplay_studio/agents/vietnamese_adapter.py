"""
Vietnamese Adapter Agent

Adapts screenplay content for Vietnamese cultural context:
- Honorifics and pronouns
- Cultural references
- Location names
- Regional dialects
- Historical accuracy
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import Scene, Character, Language
from ..prompts.vietnamese_adapter import (
    SYSTEM_PROMPT,
    ADAPTATION_PROMPT,
)

logger = logging.getLogger(__name__)


class VietnameseAdapterAgent(BaseAgent):
    """Agent for Vietnamese cultural adaptation"""

    name = "VietnameseAdapter"
    description = "Adapts content for Vietnamese cultural context"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Adapt scene content for Vietnamese culture.

        Args:
            input_data: {
                "scene": Scene,
                "characters": List[Character],
                "scene_content": str,
                "setting": str,
                "time_period": str,
                "region": str,  # "north", "central", "south"
            }

        Returns:
            AgentResult with adaptation recommendations
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            characters: List[Character] = input_data.get("characters", [])
            scene_content: str = input_data.get("scene_content", "")
            setting: str = input_data.get("setting", "")
            time_period: str = input_data.get("time_period", "contemporary")
            region: str = input_data.get("region", "south")

            if not scene:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No scene provided"
                )

            # Build character info
            character_info = self._build_character_info(characters, scene.characters_present)

            prompt = ADAPTATION_PROMPT.format(
                scene_number=scene.scene_number,
                setting=setting or scene.heading.location,
                time_period=time_period,
                region=region,
                character_info=character_info,
                current_scene_content=scene_content[:4000],
            )

            # Call LLM
            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=4000,
            )

            # Parse response
            adaptation_data = self._parse_response(response)

            if not adaptation_data:
                return AgentResult(
                    success=False,
                    data=None,
                    error="Failed to parse adaptation response"
                )

            self.log_complete(
                f"{len(adaptation_data.get('dialogue_adaptations', []))} dialogue adaptations"
            )

            return AgentResult(
                success=True,
                data=adaptation_data,
                tokens_used=tokens,
                cost_usd=self._estimate_cost(tokens)
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(
                success=False,
                data=None,
                error=str(e)
            )

    def _build_character_info(
        self,
        characters: List[Character],
        present_names: List[str]
    ) -> str:
        """Build character info for adaptation"""
        info_lines = []

        for char in characters:
            if char.name in present_names:
                relationships = ", ".join([
                    f"{k}: {v}" for k, v in char.relationships.items()
                ])
                info_lines.append(
                    f"- {char.name}: {char.role}, {char.age_range or 'unknown age'}, "
                    f"Quan he: {relationships or 'none specified'}"
                )

        return "\n".join(info_lines) if info_lines else "Khong co thong tin nhan vat"

    def _parse_response(self, response: str) -> Dict[str, Any]:
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
            self.logger.error(f"JSON parse error: {e}")
            return None

    def _estimate_cost(self, tokens: int) -> float:
        return tokens * 0.00001


def get_vietnamese_honorific(
    speaker_age: str,
    listener_age: str,
    relationship: str,
    formality: str = "normal"
) -> Dict[str, str]:
    """
    Helper function to determine appropriate Vietnamese honorifics.

    Returns dict with 'speaker_pronoun' and 'listener_pronoun'.
    """
    def parse_age(age_str: str) -> int:
        if not age_str:
            return 30
        age_str = age_str.lower()
        if "child" in age_str or "kid" in age_str:
            return 10
        if "teen" in age_str:
            return 16
        if "20" in age_str:
            return 25
        if "30" in age_str:
            return 35
        if "40" in age_str:
            return 45
        if "50" in age_str or "elder" in age_str:
            return 55
        if "60" in age_str or "old" in age_str:
            return 65
        return 30

    speaker = parse_age(speaker_age)
    listener = parse_age(listener_age)

    # Family relationships
    family_map = {
        "parent": ("con", "bo" if "father" in relationship.lower() else "me"),
        "child": ("bo" if "father" in relationship.lower() else "me", "con"),
        "grandparent": ("chau", "ong" if "grandfather" in relationship.lower() else "ba"),
        "grandchild": ("ong" if "grandfather" in relationship.lower() else "ba", "chau"),
        "sibling_older": ("em", "anh" if speaker < listener else "chi"),
        "sibling_younger": ("anh" if listener < speaker else "chi", "em"),
        "spouse": ("anh" if speaker > listener else "em", "em" if speaker > listener else "anh"),
    }

    for key, (s_pron, l_pron) in family_map.items():
        if key in relationship.lower():
            return {"speaker_pronoun": s_pron, "listener_pronoun": l_pron}

    # Non-family (based on age difference)
    age_diff = speaker - listener

    if formality == "formal":
        return {"speaker_pronoun": "toi", "listener_pronoun": "ong" if listener > 40 else "anh/chi"}

    if age_diff > 10:
        return {"speaker_pronoun": "toi", "listener_pronoun": "em"}
    elif age_diff < -10:
        return {"speaker_pronoun": "em", "listener_pronoun": "anh" if listener < 50 else "chu/co"}
    else:
        return {"speaker_pronoun": "toi", "listener_pronoun": "ban"}
