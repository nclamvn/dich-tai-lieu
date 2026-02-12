"""
Dialogue Writer Agent

Converts prose narrative into cinematic dialogue with:
- Distinct character voices
- Subtext and implication
- Natural speech patterns
- Proper parentheticals
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import Scene, DialogueBlock, Character, Language
from ..prompts.dialogue_writer import (
    SYSTEM_PROMPT,
    DIALOGUE_PROMPT,
    DIALOGUE_PROMPT_VI,
)

logger = logging.getLogger(__name__)


class DialogueWriterAgent(BaseAgent):
    """Agent for writing scene dialogue"""

    name = "DialogueWriter"
    description = "Converts prose to cinematic dialogue"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Write dialogue for a scene.

        Args:
            input_data: {
                "scene": Scene,
                "characters": List[Character],
                "source_excerpt": str,
                "language": Language,
            }

        Returns:
            AgentResult with list of DialogueBlock
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            characters: List[Character] = input_data.get("characters", [])
            source_excerpt: str = input_data.get("source_excerpt", "")
            language: Language = input_data.get("language", Language.ENGLISH)

            if not scene:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No scene provided"
                )

            # Build character profiles for prompt
            character_profiles = self._build_character_profiles(
                characters,
                scene.characters_present
            )

            # Select prompt based on language
            if language == Language.VIETNAMESE:
                prompt = DIALOGUE_PROMPT_VI.format(
                    scene_number=scene.scene_number,
                    scene_heading=str(scene.heading),
                    scene_summary=scene.summary,
                    characters_present=", ".join(scene.characters_present),
                    emotional_beat=scene.emotional_beat,
                    scene_purpose=scene.purpose,
                    character_profiles=character_profiles,
                    source_excerpt=source_excerpt[:3000],
                )
            else:
                prompt = DIALOGUE_PROMPT.format(
                    scene_number=scene.scene_number,
                    scene_heading=str(scene.heading),
                    scene_summary=scene.summary,
                    characters_present=", ".join(scene.characters_present),
                    emotional_beat=scene.emotional_beat,
                    scene_purpose=scene.purpose,
                    character_profiles=character_profiles,
                    source_excerpt=source_excerpt[:3000],
                    language=language.value,
                )

            # Call LLM
            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=4000,
            )

            # Parse response
            dialogue_data = self._parse_response(response)

            if not dialogue_data:
                return AgentResult(
                    success=False,
                    data=None,
                    error="Failed to parse dialogue response"
                )

            # Convert to DialogueBlock objects
            dialogue_blocks = self._create_dialogue_blocks(dialogue_data)

            self.log_complete(f"{len(dialogue_blocks)} dialogue blocks")

            return AgentResult(
                success=True,
                data={
                    "dialogue_blocks": dialogue_blocks,
                    "notes": dialogue_data.get("dialogue_notes", ""),
                },
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

    def _build_character_profiles(
        self,
        all_characters: List[Character],
        present_names: List[str]
    ) -> str:
        """Build character profile text for prompt"""
        profiles = []

        for char in all_characters:
            if char.name in present_names:
                profile = (
                    f"\n{char.name.upper()}:\n"
                    f"- Role: {char.role}\n"
                    f"- Description: {char.description}\n"
                    f"- Traits: {', '.join(char.traits)}\n"
                    f"- Arc: {char.arc}\n"
                )
                profiles.append(profile)

        return "\n".join(profiles) if profiles else "No character profiles available"

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

    def _create_dialogue_blocks(self, data: Dict) -> List[DialogueBlock]:
        """Create DialogueBlock objects from parsed data"""
        blocks = []

        for block_data in data.get("dialogue_blocks", []):
            block = DialogueBlock(
                character=block_data.get("character", "UNKNOWN"),
                dialogue=block_data.get("dialogue", ""),
                parenthetical=block_data.get("parenthetical"),
            )
            blocks.append(block)

        return blocks

    def _estimate_cost(self, tokens: int) -> float:
        return tokens * 0.00001
