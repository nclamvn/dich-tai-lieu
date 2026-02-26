"""
Scene Architect Agent

Breaks down the analyzed story into a scene-by-scene blueprint
with timing, locations, and emotional beats.
"""

import json
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult
from ..models import (
    StoryAnalysis, Scene, SceneHeading, Language
)
from ..prompts.scene_architect import (
    SYSTEM_PROMPT,
    SCENE_BREAKDOWN_PROMPT,
    SCENE_BREAKDOWN_PROMPT_VI,
)

logger = logging.getLogger(__name__)


class SceneArchitectAgent(BaseAgent):
    """Agent for breaking down stories into scene blueprints"""

    name = "SceneArchitect"
    description = "Creates scene-by-scene breakdown from story analysis"

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Create scene breakdown from story analysis.

        Args:
            input_data: {
                "story_analysis": StoryAnalysis,
                "target_runtime": int,  # Optional, minutes
            }

        Returns:
            AgentResult with list of Scene objects
        """
        self.log_start("Creating scene breakdown")

        try:
            analysis: StoryAnalysis = input_data.get("story_analysis")
            target_runtime = input_data.get(
                "target_runtime",
                analysis.estimated_runtime_minutes if analysis else 90
            )

            if not analysis:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No story analysis provided"
                )

            # Target pages (1 page ~ 1 minute)
            target_pages = target_runtime

            # Select prompt based on language
            if analysis.language == Language.VIETNAMESE:
                prompt = SCENE_BREAKDOWN_PROMPT_VI.format(
                    story_analysis_json=json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False),
                    target_runtime=target_runtime,
                    target_pages=target_pages,
                )
            else:
                prompt = SCENE_BREAKDOWN_PROMPT.format(
                    story_analysis_json=json.dumps(analysis.to_dict(), indent=2),
                    language=analysis.language.value,
                    target_runtime=target_runtime,
                    target_pages=target_pages,
                )

            # Call LLM
            response, tokens = await self.call_llm(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=10000,
            )

            # Parse response
            breakdown_data = self._parse_response(response)

            if not breakdown_data:
                return AgentResult(
                    success=False,
                    data=None,
                    error="Failed to parse scene breakdown response"
                )

            # Convert to Scene objects
            scenes = self._create_scenes(breakdown_data, analysis.language)

            self.log_complete(
                f"Created {len(scenes)} scenes, "
                f"~{sum(s.page_count for s in scenes):.1f} pages"
            )

            return AgentResult(
                success=True,
                data={
                    "scenes": scenes,
                    "sequences": breakdown_data.get("sequences", []),
                    "total_pages": breakdown_data.get("total_estimated_pages", len(scenes)),
                    "total_runtime": breakdown_data.get("total_estimated_runtime_minutes", target_runtime),
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

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            response = response.strip()

            # Remove markdown code blocks
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

    def _create_scenes(self, data: Dict, language: Language) -> List[Scene]:
        """Create Scene objects from parsed data"""
        scenes = []

        for scene_data in data.get("scenes", []):
            heading_data = scene_data.get("heading", {})

            # Handle Vietnamese headings
            int_ext = heading_data.get("int_ext", "INT")
            if int_ext in ["NỘI", "NỘI CẢNH", "TRONG NHÀ"]:
                int_ext = "INT"
            elif int_ext in ["NGOẠI", "NGOẠI CẢNH", "NGOÀI TRỜI"]:
                int_ext = "EXT"

            time = heading_data.get("time", "DAY")
            if time in ["NGÀY", "BAN NGÀY"]:
                time = "DAY"
            elif time in ["ĐÊM", "BAN ĐÊM", "TỐI"]:
                time = "NIGHT"
            elif time in ["LIÊN TỤC", "TIẾP"]:
                time = "CONTINUOUS"

            heading = SceneHeading(
                int_ext=int_ext.upper(),
                location=heading_data.get("location", "UNKNOWN LOCATION"),
                time=time.upper(),
            )

            scene = Scene(
                scene_number=scene_data.get("scene_number", len(scenes) + 1),
                heading=heading,
                summary=scene_data.get("summary", ""),
                characters_present=scene_data.get("characters_present", []),
                emotional_beat=scene_data.get("emotional_beat", ""),
                purpose=scene_data.get("purpose", ""),
                estimated_duration_seconds=scene_data.get("estimated_duration_seconds", 60),
                page_count=scene_data.get("page_count", 1.0),
                visual_notes=scene_data.get("visual_notes"),
                mood=scene_data.get("mood"),
                transition_out=scene_data.get("transition_out", ""),
                key_props=scene_data.get("key_props", []),
                atmosphere=scene_data.get("atmosphere", ""),
            )

            scenes.append(scene)

        return scenes

    def _estimate_cost(self, tokens: int) -> float:
        """Estimate API cost based on tokens"""
        return tokens * 0.00001
