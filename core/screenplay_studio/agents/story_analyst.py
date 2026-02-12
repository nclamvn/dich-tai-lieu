"""
Story Analyst Agent

Analyzes source material (novel, short story) and extracts:
- Story structure
- Characters
- Themes
- Key dramatic moments
- Screenplay adaptation recommendations
"""

import json
import logging
from typing import Dict, Any

from .base_agent import BaseAgent, AgentResult
from ..models import StoryAnalysis, Character, Language
from ..prompts.story_analyst import (
    SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    ANALYSIS_PROMPT_VI,
)

logger = logging.getLogger(__name__)


class StoryAnalystAgent(BaseAgent):
    """Agent for analyzing stories for screenplay adaptation"""

    name = "StoryAnalyst"
    description = "Analyzes source material for screenplay adaptation"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Analyze a story for screenplay adaptation.

        Args:
            input_data: {
                "source_text": str,  # The story/novel text
                "language": str,     # "en" or "vi"
                "title": str,        # Optional title hint
            }

        Returns:
            AgentResult with StoryAnalysis
        """
        self.log_start(f"Analyzing {len(input_data.get('source_text', ''))} chars")

        try:
            source_text = input_data.get("source_text", "")
            language = Language(input_data.get("language", "en"))

            if not source_text:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No source text provided"
                )

            # Truncate very long texts (keep first 50k chars for analysis)
            max_chars = 50000
            if len(source_text) > max_chars:
                source_text = source_text[:max_chars] + "\n\n[... text truncated for analysis ...]"
                self.logger.warning(f"Source text truncated to {max_chars} chars")

            # Select prompt based on language
            if language == Language.VIETNAMESE:
                prompt = ANALYSIS_PROMPT_VI.format(source_text=source_text)
            else:
                prompt = ANALYSIS_PROMPT.format(
                    source_text=source_text,
                    language=language.value
                )

            # Call LLM
            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.5,  # Lower temp for more consistent analysis
                max_tokens=8000,
            )

            # Parse JSON response
            analysis_data = self._parse_response(response)

            if not analysis_data:
                return AgentResult(
                    success=False,
                    data=None,
                    error="Failed to parse analysis response"
                )

            # Convert to StoryAnalysis model
            analysis = self._create_analysis(analysis_data, language)

            self.log_complete(
                f"Found {len(analysis.characters)} characters, "
                f"{analysis.estimated_scenes} scenes estimated"
            )

            return AgentResult(
                success=True,
                data=analysis,
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

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            return json.loads(response.strip())

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            return None

    def _create_analysis(self, data: Dict, language: Language) -> StoryAnalysis:
        """Create StoryAnalysis from parsed data"""

        # Parse characters
        characters = []
        for char_data in data.get("characters", []):
            characters.append(Character(
                name=char_data.get("name", "Unknown"),
                description=char_data.get("description", ""),
                role=char_data.get("role", "supporting"),
                arc=char_data.get("arc", ""),
                traits=char_data.get("traits", []),
                relationships=char_data.get("relationships", {}),
                visual_description=char_data.get("visual_description"),
                age_range=char_data.get("age_range"),
                gender=char_data.get("gender"),
            ))

        return StoryAnalysis(
            title=data.get("title", "Untitled"),
            logline=data.get("logline", ""),
            synopsis=data.get("synopsis", ""),
            genre=data.get("genre", "Drama"),
            sub_genres=data.get("sub_genres", []),
            tone=data.get("tone", ""),
            themes=data.get("themes", []),
            setting=data.get("setting", ""),
            time_period=data.get("time_period", ""),
            locations=data.get("locations", []),
            structure_type=data.get("structure_type", "three_act"),
            act_breakdown=data.get("act_breakdown", {}),
            characters=characters,
            inciting_incident=data.get("inciting_incident", ""),
            midpoint=data.get("midpoint", ""),
            climax=data.get("climax", ""),
            resolution=data.get("resolution", ""),
            key_scenes=data.get("key_scenes", []),
            estimated_runtime_minutes=data.get("estimated_runtime_minutes", 90),
            estimated_scenes=data.get("estimated_scenes", 25),
            estimated_pages=data.get("estimated_pages", 90),
            language=language,
            cultural_notes=data.get("cultural_notes", []),
        )

    def _estimate_cost(self, tokens: int) -> float:
        """Estimate API cost based on tokens"""
        # Rough estimate: $0.01 per 1K tokens (Claude)
        return tokens * 0.00001
