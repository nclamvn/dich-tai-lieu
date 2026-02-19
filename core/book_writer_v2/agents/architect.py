"""
Architect Agent

Creates the complete book blueprint with exact page allocations.
"""

from typing import Dict, Any
import json

from .base import BaseAgent, AgentContext
from ..models import (
    BookBlueprint, Part, Chapter, Section,
    WordCountTarget, AnalysisResult
)
from ..prompts.architect_prompts import ARCHITECT_SYSTEM_PROMPT, ARCHITECT_PROMPT


class ArchitectAgent(BaseAgent[Dict[str, Any], BookBlueprint]):
    """
    Agent 2: Architect

    Creates the book blueprint with:
    - Part/Chapter/Section structure
    - Exact word count allocations
    - Title hierarchy
    """

    @property
    def name(self) -> str:
        return "Architect"

    @property
    def description(self) -> str:
        return "Design book structure with exact page and word allocations"

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: AgentContext
    ) -> BookBlueprint:
        context.report_progress("Designing book structure...", 0)

        title = input_data.get("title", "")
        subtitle = input_data.get("subtitle")
        target_pages = input_data.get("target_pages", 300)
        analysis = input_data.get("analysis")
        genre = input_data.get("genre", "non-fiction")

        structure = self.config.calculate_structure(target_pages)

        context.report_progress("Calculating page allocations...", 20)

        prompt = ARCHITECT_PROMPT.format(
            title=title,
            subtitle=subtitle or "",
            target_pages=target_pages,
            target_words=structure["content_words"],
            num_parts=structure["num_parts"],
            total_chapters=structure["total_chapters"],
            chapters_per_part=structure["chapters_per_part"],
            words_per_chapter=structure["words_per_chapter"],
            sections_per_chapter=self.config.default_sections_per_chapter,
            words_per_section=structure["words_per_section"],
            analysis_summary=self._format_analysis(analysis) if analysis else "",
            genre=genre,
        )

        context.report_progress("Generating book structure...", 40)

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            temperature=0.6,
        )

        context.report_progress("Building blueprint...", 70)

        blueprint = self._build_blueprint(
            response=response,
            title=title,
            subtitle=subtitle,
            target_pages=target_pages,
            structure=structure,
            genre=genre,
        )

        context.report_progress("Validating structure...", 90)

        blueprint = self._validate_and_adjust(blueprint, structure)

        context.report_progress("Blueprint complete", 100)

        return blueprint

    def _format_analysis(self, analysis: AnalysisResult) -> str:
        """Format analysis for prompt"""
        return f"""
Topic: {analysis.topic_summary}
Audience: {analysis.target_audience}
Key Themes: {', '.join(analysis.key_themes[:5])}
Tone: {analysis.tone_and_style}
"""

    def _build_blueprint(
        self,
        response: str,
        title: str,
        subtitle: str,
        target_pages: int,
        structure: dict,
        genre: str,
    ) -> BookBlueprint:
        """Build blueprint from AI response"""

        blueprint = BookBlueprint(
            title=title,
            subtitle=subtitle,
            target_pages=target_pages,
            words_per_page=self.config.words_per_page,
            genre=genre,
        )

        parts_data = self._parse_structure(response, structure)

        words_per_part = structure["content_words"] // structure["num_parts"]

        for part_idx, part_data in enumerate(parts_data):
            part = Part(
                id=str(part_idx + 1),
                number=part_idx + 1,
                title=part_data.get("title", f"Part {part_idx + 1}"),
                word_count=WordCountTarget(words_per_part),
            )

            chapters_data = part_data.get("chapters", [])
            words_per_chapter = words_per_part // max(len(chapters_data), 1)

            for chap_idx, chap_data in enumerate(chapters_data):
                chapter = Chapter(
                    id=f"{part_idx + 1}.{chap_idx + 1}",
                    number=chap_idx + 1,
                    title=chap_data.get("title", f"Chapter {chap_idx + 1}"),
                    part_id=part.id,
                    word_count=WordCountTarget(words_per_chapter),
                )

                sections_data = chap_data.get("sections", [])
                if not sections_data:
                    sections_data = [
                        {"title": f"Section {i+1}"}
                        for i in range(self.config.default_sections_per_chapter)
                    ]

                words_per_section = words_per_chapter // len(sections_data)

                for sec_idx, sec_data in enumerate(sections_data):
                    section = Section(
                        id=f"{chapter.id}.{sec_idx + 1}",
                        number=sec_idx + 1,
                        title=sec_data.get("title", f"Section {sec_idx + 1}"),
                        chapter_id=chapter.id,
                        word_count=WordCountTarget(words_per_section),
                    )
                    chapter.sections.append(section)

                part.chapters.append(chapter)

            blueprint.parts.append(part)

        return blueprint

    def _parse_structure(self, response: str, structure: dict) -> list:
        """Parse AI response to extract structure"""

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                start = response.find("[")
                end = response.rfind("]") + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                else:
                    raise ValueError("No JSON found")

            data = json.loads(json_str.strip())

            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "parts" in data:
                return data["parts"]
            else:
                raise ValueError("Invalid structure format")

        except Exception as e:
            self.logger.warning(f"Failed to parse structure JSON: {e}")
            return self._generate_default_structure(structure)

    def _generate_default_structure(self, structure: dict) -> list:
        """Generate default book structure"""
        parts = []

        part_titles = [
            "Foundations",
            "Core Concepts",
            "Applications",
            "Advanced Topics",
            "Future Directions",
        ]

        for i in range(structure["num_parts"]):
            part = {
                "title": part_titles[i] if i < len(part_titles) else f"Part {i+1}",
                "chapters": []
            }

            for j in range(structure["chapters_per_part"]):
                chapter = {
                    "title": f"Chapter {i * structure['chapters_per_part'] + j + 1}",
                    "sections": [
                        {"title": f"Section {k+1}"}
                        for k in range(self.config.default_sections_per_chapter)
                    ]
                }
                part["chapters"].append(chapter)

            parts.append(part)

        return parts

    def _validate_and_adjust(self, blueprint: BookBlueprint, structure: dict) -> BookBlueprint:
        """Validate blueprint and adjust if needed"""

        total_sections = blueprint.total_sections
        target_sections = structure["total_sections"]

        if total_sections < target_sections * 0.8:
            self.logger.warning(f"Too few sections: {total_sections} < {target_sections}")
            for chapter in blueprint.all_chapters:
                while len(chapter.sections) < self.config.min_sections_per_chapter:
                    new_section = Section(
                        id=f"{chapter.id}.{len(chapter.sections) + 1}",
                        number=len(chapter.sections) + 1,
                        title=f"Additional Section {len(chapter.sections) + 1}",
                        chapter_id=chapter.id,
                        word_count=WordCountTarget(self.config.target_words_per_section),
                    )
                    chapter.sections.append(new_section)

        self._recalculate_word_targets(blueprint, structure)

        return blueprint

    def _recalculate_word_targets(self, blueprint: BookBlueprint, structure: dict):
        """Recalculate word count targets based on actual structure"""

        total_sections = blueprint.total_sections
        if total_sections == 0:
            return

        words_per_section = structure["content_words"] // total_sections

        for section in blueprint.all_sections:
            section.word_count = WordCountTarget(words_per_section)

        for chapter in blueprint.all_chapters:
            chapter.word_count = WordCountTarget(
                sum(s.word_count.target for s in chapter.sections)
            )

        for part in blueprint.parts:
            part.word_count = WordCountTarget(
                sum(c.word_count.target for c in part.chapters)
            )
