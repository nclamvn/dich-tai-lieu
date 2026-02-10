"""
Enricher Agent

Adds professional elements to content.
Uses parallel execution for speed (concurrency=5).
"""

import asyncio

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, SectionStatus
from ..prompts.enricher_prompts import ENRICHER_SYSTEM_PROMPT, ENRICHER_PROMPT

CONCURRENCY = 5


class EnricherAgent(BaseAgent[BookBlueprint, BookBlueprint]):
    """
    Agent 6: Enricher

    Adds professional elements:
    - Expert quotes with attribution
    - Statistics and data points
    - Cross-references between chapters
    - Callout boxes for key concepts
    - Chapter summaries
    - Key takeaways
    """

    @property
    def name(self) -> str:
        return "Enricher"

    @property
    def description(self) -> str:
        return "Add professional elements like quotes, statistics, and cross-references"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> BookBlueprint:
        blueprint = input_data

        context.report_progress("Enriching content with professional elements...", 0)

        total_chapters = blueprint.total_chapters
        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 0

        async def enrich_chapter(chapter):
            nonlocal completed
            async with sem:
                if not chapter.introduction:
                    chapter.introduction = await self._generate_chapter_intro(
                        chapter=chapter,
                        blueprint=blueprint,
                    )

                if not chapter.summary:
                    chapter.summary = await self._generate_chapter_summary(
                        chapter=chapter,
                        blueprint=blueprint,
                    )

                if not chapter.key_takeaways:
                    chapter.key_takeaways = await self._generate_takeaways(
                        chapter=chapter,
                        blueprint=blueprint,
                    )

                for section in chapter.sections:
                    if section.status != SectionStatus.COMPLETE:
                        section.status = SectionStatus.ENRICHING
                        await self._enrich_section(section, chapter, blueprint)
                        section.update_word_count()
                        section.status = SectionStatus.WRITTEN

                completed += 1
                pct = (completed / total_chapters) * 100
                context.report_progress(f"Enriched {completed}/{total_chapters}: Chapter {chapter.number}", pct)

        await asyncio.gather(*[enrich_chapter(ch) for ch in blueprint.all_chapters])

        context.report_progress("Enrichment complete", 100)

        return blueprint

    async def _generate_chapter_intro(self, chapter, blueprint) -> str:
        """Generate chapter introduction"""

        section_titles = [s.title for s in chapter.sections]

        prompt = f"""Write a compelling chapter introduction (150-200 words) for:

Book: {blueprint.title}
Chapter {chapter.number}: {chapter.title}

This chapter covers:
{chr(10).join(f'- {t}' for t in section_titles)}

The introduction should:
- Hook the reader
- Preview what they'll learn
- Connect to the book's overall theme
- Be engaging and professional

Write only the introduction text, no meta-commentary."""

        response = await self.call_ai(prompt, temperature=0.7)
        return response.strip()

    async def _generate_chapter_summary(self, chapter, blueprint) -> str:
        """Generate chapter summary"""

        section_previews = []
        for section in chapter.sections:
            if section.content:
                words = section.content.split()[:50]
                section_previews.append(f"{section.title}: {' '.join(words)}...")

        prompt = f"""Write a chapter summary (100-150 words) for:

Chapter {chapter.number}: {chapter.title}

Section content previews:
{chr(10).join(section_previews)}

The summary should:
- Recap key points covered
- Reinforce main takeaways
- Transition to what's next

Write only the summary text."""

        response = await self.call_ai(prompt, temperature=0.6)
        return response.strip()

    async def _generate_takeaways(self, chapter, blueprint) -> list:
        """Generate key takeaways"""

        prompt = f"""List 3-5 key takeaways for Chapter {chapter.number}: {chapter.title}

Based on sections:
{chr(10).join(f'- {s.title}' for s in chapter.sections)}

Format as a simple list, one takeaway per line.
Each takeaway should be actionable and memorable (10-20 words each)."""

        response = await self.call_ai(prompt, temperature=0.6)

        takeaways = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("\u2022") or line.startswith("*"):
                takeaways.append(line[1:].strip())
            elif line.startswith(tuple("12345")):
                takeaways.append(line.split(".", 1)[-1].strip())
            elif len(line) > 10 and len(line) < 200:
                takeaways.append(line)

        return takeaways[:5]

    async def _enrich_section(self, section, chapter, blueprint):
        """Add enrichments to a section"""

        if section.word_count.actual < 500:
            return

        prompt = ENRICHER_PROMPT.format(
            section_title=section.title,
            section_content=section.content,
            chapter_title=chapter.title,
            book_title=blueprint.title,
        )

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=ENRICHER_SYSTEM_PROMPT,
            temperature=0.7,
        )

        enriched = response.strip()

        if self.count_words(enriched) >= section.word_count.actual:
            section.content = enriched
