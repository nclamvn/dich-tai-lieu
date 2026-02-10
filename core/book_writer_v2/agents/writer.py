"""
Writer Agent

Writes content for each section based on outlines.
Uses parallel execution for speed (concurrency=5).
"""

import asyncio
from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, SectionStatus
from ..prompts.writer_prompts import WRITER_SYSTEM_PROMPT, WRITER_PROMPT

CONCURRENCY = 5


class WriterAgent(BaseAgent[BookBlueprint, BookBlueprint]):
    """
    Agent 4: Writer

    Writes content section by section (parallel):
    - Follows outline points exactly
    - Meets word count targets
    - Maintains consistent style
    - Creates smooth transitions
    """

    @property
    def name(self) -> str:
        return "Writer"

    @property
    def description(self) -> str:
        return "Write section content following outlines and word count targets"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> BookBlueprint:
        blueprint = input_data
        total_sections = blueprint.total_sections

        # Collect sections that need writing
        sections_to_write = []
        for section in blueprint.all_sections:
            if section.status not in [SectionStatus.COMPLETE, SectionStatus.WRITTEN]:
                sections_to_write.append(section)

        context.report_progress(f"Writing {len(sections_to_write)} sections (parallel x{CONCURRENCY})...", 0)

        # Semaphore for concurrency control
        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 0

        async def write_one(section):
            nonlocal completed
            async with sem:
                section.status = SectionStatus.WRITING

                chapter = blueprint.get_chapter(section.chapter_id)
                part = next(
                    (p for p in blueprint.parts if p.id == chapter.part_id), None
                ) if chapter else None

                await self._write_section(
                    section=section,
                    chapter=chapter,
                    part=part,
                    book_title=blueprint.title,
                )

                section.update_word_count()

                if section.word_count.needs_expansion:
                    section.status = SectionStatus.NEEDS_EXPANSION
                else:
                    section.status = SectionStatus.WRITTEN

                completed += 1
                pct = (completed / len(sections_to_write)) * 100
                context.report_progress(
                    f"Written {completed}/{len(sections_to_write)}: {section.title}",
                    pct,
                )

        # Launch all tasks with semaphore-controlled concurrency
        await asyncio.gather(*[write_one(s) for s in sections_to_write])

        context.report_progress("All sections written", 100)

        return blueprint

    async def _write_section(
        self,
        section,
        chapter,
        part,
        book_title: str,
    ):
        """Write content for a single section"""

        outline_text = "\n".join([
            f"- {point.content} (Target: ~{point.target_words} words)"
            for point in section.outline_points
        ])

        prompt = WRITER_PROMPT.format(
            book_title=book_title,
            part_title=part.title if part else "",
            chapter_title=chapter.title if chapter else "",
            section_title=section.title,
            section_id=section.id,
            target_words=section.word_count.target,
            min_words=int(section.word_count.target * 0.95),
            outline=outline_text or "Write comprehensive content for this section",
            outline_summary=section.outline_summary or "",
            prev_content="",
        )

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=WRITER_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=self.config.temperature,
        )

        content = self._clean_content(response)

        section.content = content

    def _clean_content(self, response: str) -> str:
        """Clean AI response to get pure content"""

        content = response.strip()

        prefixes_to_remove = [
            "Here's the content for",
            "Here is the content for",
            "Below is the content",
            "Here is the section",
            "Content for section",
            "Section content:",
            "---",
        ]

        for prefix in prefixes_to_remove:
            if content.lower().startswith(prefix.lower()):
                content = content[len(prefix):].strip()

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return content.strip()
