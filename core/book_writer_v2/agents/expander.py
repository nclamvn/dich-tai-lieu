"""
Expander Agent

Expands sections that are below word count targets.
THIS IS THE KEY AGENT FOR ENSURING PAGE COUNT DELIVERY.
Uses parallel execution for speed (concurrency=5).
"""

import asyncio

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, SectionStatus
from ..prompts.expander_prompts import EXPANDER_SYSTEM_PROMPT, EXPANDER_PROMPT

CONCURRENCY = 5


class ExpanderAgent(BaseAgent[BookBlueprint, BookBlueprint]):
    """
    Agent 5: Expander

    THE CRITICAL AGENT FOR PAGE COUNT DELIVERY.

    Expands sections that are below target by:
    - Adding examples and case studies
    - Adding explanations and details
    - Adding statistics and data
    - Adding transitions and context
    - Adding depth and nuance

    Loops until all sections meet targets or max attempts reached.
    """

    @property
    def name(self) -> str:
        return "Expander"

    @property
    def description(self) -> str:
        return "Expand sections below word count targets with quality content"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> BookBlueprint:
        blueprint = input_data

        sections_to_expand = blueprint.get_sections_needing_expansion()

        if not sections_to_expand:
            context.report_progress("No sections need expansion", 100)
            return blueprint

        # Filter out sections that have reached max attempts
        eligible = []
        for section in sections_to_expand:
            if section.expansion_attempts >= self.config.max_expansion_attempts:
                self.logger.warning(
                    f"Section {section.id} reached max expansion attempts"
                )
            else:
                eligible.append(section)

        if not eligible:
            context.report_progress("All sections at max expansion attempts", 100)
            return blueprint

        context.report_progress(
            f"Expanding {len(eligible)} sections below target (parallel x{CONCURRENCY})...", 0
        )

        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 0

        async def expand_one(section):
            nonlocal completed
            async with sem:
                section.status = SectionStatus.EXPANDING
                section.expansion_attempts += 1

                words_needed = section.word_count.remaining
                chapter = blueprint.get_chapter(section.chapter_id)

                await self._expand_section(
                    section=section,
                    chapter=chapter,
                    book_title=blueprint.title,
                    words_needed=words_needed,
                )

                section.update_word_count()

                if section.word_count.is_complete:
                    section.status = SectionStatus.WRITTEN
                elif section.expansion_attempts >= self.config.max_expansion_attempts:
                    self.logger.warning(
                        f"Section {section.id} still at {section.word_count.completion:.0f}% "
                        f"after {section.expansion_attempts} attempts"
                    )
                    section.status = SectionStatus.WRITTEN

                completed += 1
                pct = (completed / len(eligible)) * 100
                context.report_progress(
                    f"Expanded {completed}/{len(eligible)}: {section.title} ({section.word_count.completion:.0f}%)",
                    pct,
                )

        await asyncio.gather(*[expand_one(s) for s in eligible])

        still_short = len([s for s in blueprint.all_sections if s.word_count.needs_expansion])
        if still_short > 0:
            context.report_progress(
                f"Expansion complete. {still_short} sections still below 90%",
                100
            )
        else:
            context.report_progress("All sections expanded to target", 100)

        return blueprint

    async def _expand_section(
        self,
        section,
        chapter,
        book_title: str,
        words_needed: int,
    ):
        """Expand a single section"""

        expansion_strategy = self._determine_strategy(section, words_needed)

        prompt = EXPANDER_PROMPT.format(
            book_title=book_title,
            chapter_title=chapter.title if chapter else "",
            section_title=section.title,
            current_content=section.content,
            current_words=section.word_count.actual,
            target_words=section.word_count.target,
            words_needed=words_needed,
            expansion_strategy=expansion_strategy,
            attempt_number=section.expansion_attempts,
        )

        response = await self.call_ai(
            prompt=prompt,
            system_prompt=EXPANDER_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=self.config.temperature_expansion,
        )

        expanded_content = self._clean_expansion(response)

        new_word_count = self.count_words(expanded_content)
        if new_word_count > section.word_count.actual:
            section.content = expanded_content
        else:
            self.logger.warning(
                f"Expansion didn't add content for {section.id}. "
                f"Old: {section.word_count.actual}, New: {new_word_count}"
            )

    def _determine_strategy(self, section, words_needed: int) -> str:
        """Determine best expansion strategy based on gap"""

        strategies = []

        if words_needed > 500:
            strategies.append(
                "ADD DETAILED EXAMPLE: Include a comprehensive real-world "
                "case study or example (300-400 words)"
            )

        if words_needed > 300:
            strategies.append(
                "ADD EXPLANATION: Break down a complex concept with "
                "step-by-step explanation (200-300 words)"
            )

        if words_needed > 200:
            strategies.append(
                "ADD DATA: Include relevant statistics, research findings, "
                "or expert quotes (100-200 words)"
            )

        if words_needed > 100:
            strategies.append(
                "ADD CONTEXT: Expand on historical background, implications, "
                "or alternative perspectives (100-150 words)"
            )

        strategies.append(
            "ADD TRANSITIONS: Strengthen paragraph connections "
            "and section flow (50-100 words)"
        )

        return "\n".join([f"- {s}" for s in strategies])

    def _clean_expansion(self, response: str) -> str:
        """Clean expanded content"""

        content = response.strip()

        lines = content.split("\n")
        clean_lines = []

        skip_prefixes = [
            "here's the expanded",
            "here is the expanded",
            "expanded content:",
            "revised section:",
            "---",
        ]

        for line in lines:
            line_lower = line.lower().strip()
            if any(line_lower.startswith(p) for p in skip_prefixes):
                continue
            clean_lines.append(line)

        return "\n".join(clean_lines).strip()
