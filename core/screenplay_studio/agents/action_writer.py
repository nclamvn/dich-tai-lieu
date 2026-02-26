"""
Action Writer Agent

Writes cinematic action lines (scene descriptions):
- Visual, economical prose
- Present tense, active voice
- Atmosphere and mood
- Character introductions
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import Scene, ActionBlock, DialogueBlock, Language
from ..prompts.action_writer import (
    SYSTEM_PROMPT,
    ACTION_PROMPT,
    ACTION_PROMPT_VI,
)

logger = logging.getLogger(__name__)


class ActionWriterAgent(BaseAgent):
    """Agent for writing scene action/descriptions"""

    name = "ActionWriter"
    description = "Writes cinematic scene descriptions"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Write action lines for a scene.

        Args:
            input_data: {
                "scene": Scene,
                "dialogue_blocks": List[DialogueBlock],
                "source_excerpt": str,
                "language": Language,
            }

        Returns:
            AgentResult with list of ActionBlock and placement info
        """
        self.log_start(f"Scene {input_data.get('scene', {})}")

        try:
            scene: Scene = input_data.get("scene")
            dialogue_blocks: List[DialogueBlock] = input_data.get("dialogue_blocks", [])
            source_excerpt: str = input_data.get("source_excerpt", "")
            language: Language = input_data.get("language", Language.ENGLISH)

            if not scene:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No scene provided"
                )

            # Build dialogue preview for context
            dialogue_preview = self._build_dialogue_preview(dialogue_blocks)

            # Select prompt based on language
            if language == Language.VIETNAMESE:
                prompt = ACTION_PROMPT_VI.format(
                    scene_number=scene.scene_number,
                    scene_heading=str(scene.heading),
                    scene_summary=scene.summary,
                    characters_present=", ".join(scene.characters_present),
                    emotional_beat=scene.emotional_beat,
                    mood=scene.mood or "neutral",
                    visual_notes=scene.visual_notes or "None specified",
                    dialogue_preview=dialogue_preview,
                    source_excerpt=source_excerpt[:2000],
                )
            else:
                prompt = ACTION_PROMPT.format(
                    scene_number=scene.scene_number,
                    scene_heading=str(scene.heading),
                    scene_summary=scene.summary,
                    characters_present=", ".join(scene.characters_present),
                    emotional_beat=scene.emotional_beat,
                    mood=scene.mood or "neutral",
                    visual_notes=scene.visual_notes or "None specified",
                    dialogue_preview=dialogue_preview,
                    source_excerpt=source_excerpt[:2000],
                    language=language.value,
                )

            # Call LLM
            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=6000,
            )

            # Parse response
            action_data = self._parse_response(response)

            if not action_data:
                return AgentResult(
                    success=False,
                    data=None,
                    error="Failed to parse action response"
                )

            # Process action blocks with placement info
            action_blocks = self._create_action_blocks(action_data)

            self.log_complete(f"{len(action_blocks)} action blocks")

            return AgentResult(
                success=True,
                data={
                    "action_blocks": action_blocks,
                    "notes": action_data.get("action_notes", ""),
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

    def _build_dialogue_preview(self, dialogue_blocks: List[DialogueBlock]) -> str:
        """Build dialogue preview for context"""
        if not dialogue_blocks:
            return "No dialogue in this scene"

        preview_lines = []
        for i, block in enumerate(dialogue_blocks[:10]):
            text = block.dialogue[:50]
            preview_lines.append(f'[{i}] {block.character}: "{text}..."')

        return "\n".join(preview_lines)

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

    def _create_action_blocks(self, data: Dict) -> List[Dict]:
        """Create action block info with placement"""
        blocks = []

        for block_data in data.get("action_blocks", []):
            blocks.append({
                "type": block_data.get("type", "action"),
                "text": block_data.get("text", ""),
                "placement": block_data.get("placement"),
                "after_dialogue_index": block_data.get("after_dialogue_index"),
            })

        return blocks

    def _estimate_cost(self, tokens: int) -> float:
        return tokens * 0.00001
