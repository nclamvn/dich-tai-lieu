"""
Analyst Agent

Analyzes the book topic and creates a comprehensive analysis.
"""

from typing import Dict, Any
import json

from .base import BaseAgent, AgentContext
from ..models import AnalysisResult
from ..prompts.analyst_prompts import ANALYST_SYSTEM_PROMPT, ANALYST_PROMPT


class AnalystAgent(BaseAgent[Dict[str, Any], AnalysisResult]):
    """
    Agent 1: Analyst

    Analyzes the book topic to understand:
    - Target audience
    - Key themes and messages
    - Competitive landscape
    - Recommended structure
    - Tone and style
    """

    @property
    def name(self) -> str:
        return "Analyst"

    @property
    def description(self) -> str:
        return "Analyze book topic, audience, and create comprehensive book analysis"

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: AgentContext
    ) -> AnalysisResult:
        context.report_progress("Analyzing book topic...", 0)

        title = input_data.get("title", "")
        description = input_data.get("description", "")
        target_pages = input_data.get("target_pages", 300)
        genre = input_data.get("genre", "non-fiction")
        audience = input_data.get("audience", "")

        prompt = ANALYST_PROMPT.format(
            title=title,
            description=description,
            target_pages=target_pages,
            genre=genre,
            audience=audience or "General readers interested in this topic",
        )

        context.report_progress("Calling AI for analysis...", 20)

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=ANALYST_SYSTEM_PROMPT,
            temperature=0.7,
        )

        context.report_progress("Parsing analysis result...", 80)

        result = self._parse_response(response)

        context.report_progress("Analysis complete", 100)

        return result

    def _parse_response(self, response: str) -> AnalysisResult:
        """Parse AI response into AnalysisResult"""

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            data = json.loads(json_str.strip())

            return AnalysisResult(
                topic_summary=data.get("topic_summary", ""),
                target_audience=data.get("target_audience", ""),
                audience_profile=data.get("audience_profile", {}),
                key_themes=data.get("key_themes", []),
                key_messages=data.get("key_messages", []),
                unique_value=data.get("unique_value", ""),
                competitive_landscape=data.get("competitive_landscape", []),
                recommended_structure=data.get("recommended_structure", {}),
                tone_and_style=data.get("tone_and_style", ""),
                content_warnings=data.get("content_warnings", []),
                research_notes=data.get("research_notes", ""),
            )

        except (json.JSONDecodeError, IndexError, KeyError) as e:
            self.logger.warning(f"Failed to parse JSON, using text extraction: {e}")

            return AnalysisResult(
                topic_summary=self._extract_section(response, "topic_summary", "summary"),
                target_audience=self._extract_section(response, "target_audience", "audience"),
                audience_profile={},
                key_themes=self._extract_list(response, "key_themes", "themes"),
                key_messages=self._extract_list(response, "key_messages", "messages"),
                unique_value=self._extract_section(response, "unique_value", "value"),
                competitive_landscape=[],
                recommended_structure={},
                tone_and_style=self._extract_section(response, "tone", "style"),
                content_warnings=[],
                research_notes="",
            )

    def _extract_section(self, text: str, *keywords: str) -> str:
        """Extract a section from text by keywords"""
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                start = text_lower.find(keyword)
                end = text.find("\n\n", start)
                if end == -1:
                    end = start + 500
                return text[start:end].strip()
        return ""

    def _extract_list(self, text: str, *keywords: str) -> list:
        """Extract a list from text by keywords"""
        section = self._extract_section(text, *keywords)
        if not section:
            return []

        lines = section.split("\n")
        items = []
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("\u2022") or line.startswith("*"):
                items.append(line[1:].strip())
            elif line and len(line) > 10:
                items.append(line)

        return items[:10]
