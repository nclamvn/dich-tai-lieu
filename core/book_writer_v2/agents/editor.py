"""
Editor Agent

Polishes content for publication quality.
Uses parallel execution for speed (concurrency=5).
"""

import asyncio

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, Section, Chapter, SectionStatus
from ..prompts.editor_prompts import EDITOR_SYSTEM_PROMPT, EDITOR_PROMPT

CONCURRENCY = 5


class EditorAgent(BaseAgent[BookBlueprint, BookBlueprint]):
    """
    Agent 7: Editor

    Polishes content:
    - Grammar and spelling
    - Sentence flow
    - Remove repetition
    - Consistent terminology
    - Cross-references
    - Overall coherence
    """

    @property
    def name(self) -> str:
        return "Editor"

    @property
    def description(self) -> str:
        return "Polish content for grammar, flow, and consistency"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> BookBlueprint:
        blueprint = input_data

        context.report_progress("Editing content...", 0)

        all_sections = blueprint.all_sections
        total_sections = len(all_sections)

        # Pre-compute prev/next context for each section (read-only)
        section_contexts = []
        for idx, section in enumerate(all_sections):
            chapter = blueprint.get_chapter(section.chapter_id)
            prev_section = all_sections[idx - 1] if idx > 0 else None
            next_section = all_sections[idx + 1] if idx < total_sections - 1 else None
            section_contexts.append((section, chapter, prev_section, next_section))

        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 0

        async def edit_one(section, chapter, prev_section, next_section):
            nonlocal completed
            async with sem:
                section.status = SectionStatus.EDITING

                await self._edit_section(
                    section=section,
                    chapter=chapter,
                    prev_section=prev_section,
                    next_section=next_section,
                )

                section.update_word_count()
                section.status = SectionStatus.COMPLETE

                completed += 1
                pct = (completed / total_sections) * 100
                context.report_progress(f"Edited {completed}/{total_sections}: {section.title}", pct)

        await asyncio.gather(*[
            edit_one(s, ch, prev, nxt) for s, ch, prev, nxt in section_contexts
        ])

        # Edit chapter intros and summaries in parallel
        async def edit_chapter_texts(chapter):
            async with sem:
                if chapter.introduction:
                    chapter.introduction = await self._edit_text(
                        chapter.introduction,
                        context_desc="chapter introduction"
                    )
                if chapter.summary:
                    chapter.summary = await self._edit_text(
                        chapter.summary,
                        context_desc="chapter summary"
                    )

        await asyncio.gather(*[edit_chapter_texts(ch) for ch in blueprint.all_chapters])

        context.report_progress("Editing complete", 100)

        return blueprint

    async def _edit_section(
        self,
        section: Section,
        chapter: Chapter,
        prev_section: Section = None,
        next_section: Section = None,
    ):
        """Edit a single section"""

        prev_ending = ""
        if prev_section and prev_section.content:
            words = prev_section.content.split()
            prev_ending = " ".join(words[-50:])

        next_beginning = ""
        if next_section and next_section.content:
            words = next_section.content.split()
            next_beginning = " ".join(words[:50])

        prompt = EDITOR_PROMPT.format(
            section_title=section.title,
            section_content=section.content,
            chapter_title=chapter.title if chapter else "",
            prev_section_ending=prev_ending or "N/A (first section)",
            next_section_beginning=next_beginning or "N/A (last section)",
        )

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=EDITOR_SYSTEM_PROMPT,
            temperature=self.config.temperature_editing,
        )

        edited = response.strip()

        original_words = self.count_words(section.content)
        edited_words = self.count_words(edited)

        if edited_words >= original_words * 0.9:
            section.content = edited
        else:
            self.logger.warning(
                f"Editing removed too much content from {section.id}. "
                f"Original: {original_words}, Edited: {edited_words}"
            )

    async def _edit_text(self, text: str, context_desc: str) -> str:
        """Edit a piece of text"""

        prompt = f"""Edit this {context_desc} for grammar, clarity, and flow.
Make minimal changes - preserve the meaning and length.

Text:
{text}

Return only the edited text, no commentary."""

        response = await self.call_ai(
            prompt=prompt,
            temperature=self.config.temperature_editing,
        )

        return response.strip()
