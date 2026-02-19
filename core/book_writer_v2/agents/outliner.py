"""
Outliner Agent

Creates detailed outlines for each section.
Uses parallel execution for speed (concurrency=5).
"""

import asyncio
import json

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, Section, OutlinePoint, SectionStatus
from ..prompts.outliner_prompts import OUTLINER_SYSTEM_PROMPT, OUTLINER_PROMPT

CONCURRENCY = 5


class OutlinerAgent(BaseAgent[BookBlueprint, BookBlueprint]):
    """
    Agent 3: Outliner

    Creates detailed outlines for each section including:
    - Main points to cover
    - Word count per point
    - Examples and case studies to include
    - Transitions
    """

    @property
    def name(self) -> str:
        return "Outliner"

    @property
    def description(self) -> str:
        return "Create detailed section outlines with word count breakdowns"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> BookBlueprint:
        blueprint = input_data
        all_sections = blueprint.all_sections
        total_sections = len(all_sections)

        context.report_progress(f"Creating outlines for {total_sections} sections (parallel x{CONCURRENCY})...", 0)

        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 0

        async def outline_one(idx, section):
            nonlocal completed
            async with sem:
                chapter = blueprint.get_chapter(section.chapter_id)
                part_id = chapter.part_id if chapter else "1"
                part = next((p for p in blueprint.parts if p.id == part_id), None)

                prev_section = all_sections[idx - 1] if idx > 0 else None
                next_section = all_sections[idx + 1] if idx < total_sections - 1 else None

                await self._outline_section(
                    section=section,
                    chapter=chapter,
                    part=part,
                    book_title=blueprint.title,
                    prev_section=prev_section,
                    next_section=next_section,
                )

                section.status = SectionStatus.OUTLINED
                completed += 1
                pct = (completed / total_sections) * 100
                context.report_progress(f"Outlined {completed}/{total_sections}: {section.title}", pct)

        await asyncio.gather(*[outline_one(i, s) for i, s in enumerate(all_sections)])

        context.report_progress("All sections outlined", 100)

        return blueprint

    async def _outline_section(
        self,
        section: Section,
        chapter,
        part,
        book_title: str,
        prev_section: Section = None,
        next_section: Section = None,
    ):
        """Create outline for a single section"""

        prompt = OUTLINER_PROMPT.format(
            book_title=book_title,
            part_title=part.title if part else "",
            chapter_title=chapter.title if chapter else "",
            section_title=section.title,
            section_id=section.id,
            target_words=section.word_count.target,
            prev_section_title=prev_section.title if prev_section else "N/A (First section)",
            next_section_title=next_section.title if next_section else "N/A (Last section)",
        )

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=OUTLINER_SYSTEM_PROMPT,
            temperature=0.7,
        )

        outline_points, summary = self._parse_outline(response, section.word_count.target)

        section.outline_points = outline_points
        section.outline_summary = summary

    def _parse_outline(self, response: str, target_words: int) -> tuple:
        """Parse AI response into outline points"""

        outline_points = []
        summary = ""

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())

                summary = data.get("summary", "")

                for idx, point in enumerate(data.get("points", [])):
                    outline_points.append(OutlinePoint(
                        id=f"point_{idx + 1}",
                        content=point.get("content", point.get("point", "")),
                        target_words=point.get("words", target_words // 5),
                        notes=point.get("notes", ""),
                    ))

                return outline_points, summary

        except Exception as e:
            self.logger.warning(f"Failed to parse outline JSON: {e}")

        # Fallback: extract from text
        lines = response.strip().split("\n")
        words_per_point = target_words // 5

        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("\u2022") or line.startswith("*"):
                content = line[1:].strip()
                if len(content) > 10:
                    outline_points.append(OutlinePoint(
                        id=f"point_{len(outline_points) + 1}",
                        content=content,
                        target_words=words_per_point,
                    ))
            elif line.startswith(tuple("123456789")):
                content = line.split(".", 1)[-1].strip() if "." in line else line
                if len(content) > 10:
                    outline_points.append(OutlinePoint(
                        id=f"point_{len(outline_points) + 1}",
                        content=content,
                        target_words=words_per_point,
                    ))

        while len(outline_points) < 3:
            outline_points.append(OutlinePoint(
                id=f"point_{len(outline_points) + 1}",
                content=f"Additional point {len(outline_points) + 1}",
                target_words=words_per_point,
            ))

        return outline_points, summary
