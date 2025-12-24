"""
Author Engine Core Logic (Phase 4.1 MVP)

Provides co-writing and ghostwriting capabilities using prompt-based style control.
No corpus learning (Phase 4.2 skipped per user request).
"""

import asyncio
import re
from typing import List, Optional, Dict
from pathlib import Path

from .models import AuthorProject, Variation, AuthorConfig
from .prompts import (
    CO_WRITE_PROMPT,
    CO_WRITE_VARIATION_PROMPT,
    REWRITE_PROMPT,
    REWRITE_DEFAULT_IMPROVEMENTS,
    EXPAND_PROMPT,
    CHAPTER_FROM_OUTLINE_PROMPT,
    BRAINSTORM_PROMPT,
    CRITIQUE_PROMPT,
    get_style_instruction,
    format_extra_variations,
    format_extra_ideas,
)


class AuthorEngine:
    """
    Core authoring engine providing:
    - Co-write mode: Propose next paragraphs with variations
    - Rewrite mode: Improve existing text
    - Expand mode: Develop brief ideas into full content
    - Chapter generation: Create full chapters from outlines
    - Brainstorming: Generate creative ideas
    - Critique: Provide constructive feedback

    Uses prompt-based style control instead of corpus learning.
    """

    def __init__(
        self,
        llm_provider=None,
        config: Optional[AuthorConfig] = None,
        data_path: Path = None
    ):
        """
        Initialize Author Engine

        Args:
            llm_provider: LLM provider instance (e.g., OpenAI client)
            config: Author configuration
            data_path: Base path for storing author projects
        """
        self.llm_provider = llm_provider
        self.config = config or AuthorConfig()
        self.data_path = data_path or Path("data/authors")
        self.data_path.mkdir(parents=True, exist_ok=True)

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Call LLM provider with prompt

        Args:
            prompt: Formatted prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # If no provider, return placeholder (for testing)
        if self.llm_provider is None:
            return "[LLM Response Placeholder - No provider configured]"

        # Call OpenAI-style API
        if hasattr(self.llm_provider, 'chat'):
            response = await asyncio.to_thread(
                self.llm_provider.chat.completions.create,
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=tokens,
            )
            return response.choices[0].message.content.strip()

        # Call Anthropic-style API
        elif hasattr(self.llm_provider, 'messages'):
            response = await asyncio.to_thread(
                self.llm_provider.messages.create,
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=tokens,
            )
            return response.content[0].text.strip()

        raise ValueError("Unsupported LLM provider")

    # ==========================================================================
    # CO-WRITING MODE
    # ==========================================================================

    async def propose_next_paragraph(
        self,
        context: str,
        instruction: str = "Continue writing naturally",
        style: str = None,
        target_length: int = 150,
        n_variations: int = 1,
        custom_style_instruction: str = None
    ) -> List[Variation]:
        """
        Generate next paragraph(s) to continue the manuscript

        Args:
            context: Previous content for context
            instruction: User instruction for what to write
            style: Style preset name (e.g., "formal", "casual")
            target_length: Target word count for paragraph
            n_variations: Number of variations to generate
            custom_style_instruction: Optional custom style override

        Returns:
            List of Variation objects
        """
        style = style or self.config.default_style
        style_instruction = get_style_instruction(style, custom_style_instruction)

        if n_variations == 1:
            # Single variation
            prompt = CO_WRITE_PROMPT.format(
                context=context,
                style_instruction=style_instruction,
                instruction=instruction,
                target_length=target_length
            )

            text = await self._call_llm(prompt)
            return [Variation(text=text, style=style)]

        else:
            # Multiple variations
            prompt = CO_WRITE_VARIATION_PROMPT.format(
                context=context,
                style_instruction=style_instruction,
                instruction=instruction,
                target_length=target_length,
                n_variations=n_variations,
                extra_variations=format_extra_variations(n_variations)
            )

            response = await self._call_llm(prompt)
            return self._parse_variations(response, style)

    def _parse_variations(self, response: str, style: str) -> List[Variation]:
        """Parse multiple variations from LLM response"""
        variations = []

        # Split by VARIATION markers
        pattern = r'VARIATION ([A-Z]):\s*\n(.*?)(?=\nVARIATION [A-Z]:|\Z)'
        matches = re.findall(pattern, response, re.DOTALL)

        for letter, text in matches:
            text = text.strip()
            if text:
                variations.append(Variation(text=text, style=style))

        # Fallback: if parsing fails, return whole response as single variation
        if not variations:
            variations.append(Variation(text=response.strip(), style=style))

        return variations

    # ==========================================================================
    # REWRITING MODE
    # ==========================================================================

    async def rewrite_paragraph(
        self,
        text: str,
        improvements: Optional[List[str]] = None,
        style: str = None,
        custom_style_instruction: str = None
    ) -> str:
        """
        Rewrite text with improvements

        Args:
            text: Original text to rewrite
            improvements: List of improvement instructions
            style: Style preset name
            custom_style_instruction: Optional custom style override

        Returns:
            Rewritten text
        """
        style = style or self.config.default_style
        style_instruction = get_style_instruction(style, custom_style_instruction)

        if improvements is None:
            improvements_text = REWRITE_DEFAULT_IMPROVEMENTS
        else:
            improvements_text = "\n".join(f"- {imp}" for imp in improvements)

        prompt = REWRITE_PROMPT.format(
            original_text=text,
            style_instruction=style_instruction,
            improvements=improvements_text
        )

        return await self._call_llm(prompt)

    # ==========================================================================
    # EXPANSION MODE
    # ==========================================================================

    async def expand_idea(
        self,
        idea: str,
        target_length: int = 500,
        style: str = None,
        context: str = "",
        content_type: str = "paragraph",
        custom_style_instruction: str = None
    ) -> str:
        """
        Expand brief idea into full content

        Args:
            idea: Brief idea or outline to expand
            target_length: Target word count
            style: Style preset name
            context: Additional context (optional)
            content_type: Type of content (paragraph, section, etc.)
            custom_style_instruction: Optional custom style override

        Returns:
            Expanded content
        """
        style = style or self.config.default_style
        style_instruction = get_style_instruction(style, custom_style_instruction)

        prompt = EXPAND_PROMPT.format(
            idea=idea,
            style_instruction=style_instruction,
            target_length=target_length,
            context=context,
            content_type=content_type
        )

        return await self._call_llm(
            prompt,
            max_tokens=min(target_length * 2, 4000)  # Generous token limit
        )

    # ==========================================================================
    # CHAPTER GENERATION MODE
    # ==========================================================================

    async def generate_chapter(
        self,
        book_title: str,
        genre: str,
        chapter_outline: str,
        previous_summary: str = "",
        style: str = None,
        target_length: int = 3000,
        custom_style_instruction: str = None
    ) -> str:
        """
        Generate full chapter from outline

        Args:
            book_title: Title of the book
            genre: Book genre
            chapter_outline: Outline for this chapter
            previous_summary: Summary of previous chapters
            style: Style preset name
            target_length: Target word count for chapter
            custom_style_instruction: Optional custom style override

        Returns:
            Complete chapter text
        """
        style = style or self.config.default_style
        style_instruction = get_style_instruction(style, custom_style_instruction)

        prompt = CHAPTER_FROM_OUTLINE_PROMPT.format(
            book_title=book_title,
            genre=genre,
            style_instruction=style_instruction,
            previous_summary=previous_summary,
            chapter_outline=chapter_outline,
            target_length=target_length
        )

        return await self._call_llm(
            prompt,
            max_tokens=min(target_length * 2, 8000)  # Very generous for chapters
        )

    # ==========================================================================
    # BRAINSTORMING MODE
    # ==========================================================================

    async def brainstorm_ideas(
        self,
        focus: str,
        context: str = "",
        style: str = None,
        n_ideas: int = 5,
        custom_style_instruction: str = None
    ) -> List[str]:
        """
        Generate creative ideas for development

        Args:
            focus: What to brainstorm about
            context: Project context
            style: Style/genre preset
            n_ideas: Number of ideas to generate
            custom_style_instruction: Optional custom style override

        Returns:
            List of idea texts
        """
        style = style or self.config.default_style
        style_instruction = get_style_instruction(style, custom_style_instruction)

        prompt = BRAINSTORM_PROMPT.format(
            context=context,
            focus=focus,
            style_instruction=style_instruction,
            n_ideas=n_ideas,
            extra_ideas=format_extra_ideas(n_ideas)
        )

        response = await self._call_llm(prompt)
        return self._parse_ideas(response)

    def _parse_ideas(self, response: str) -> List[str]:
        """Parse multiple ideas from LLM response"""
        ideas = []

        # Split by IDEA markers
        pattern = r'IDEA (\d+):\s*\n(.*?)(?=\nIDEA \d+:|\Z)'
        matches = re.findall(pattern, response, re.DOTALL)

        for num, text in matches:
            text = text.strip()
            if text:
                ideas.append(text)

        # Fallback: if parsing fails, return whole response as single idea
        if not ideas:
            ideas.append(response.strip())

        return ideas

    # ==========================================================================
    # CRITIQUE/FEEDBACK MODE
    # ==========================================================================

    async def critique_text(
        self,
        text: str,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """
        Provide constructive feedback on text

        Args:
            text: Text to critique
            focus_areas: Specific areas to focus on (optional)

        Returns:
            Critique and feedback
        """
        if focus_areas is None:
            focus_text = "Overall quality, clarity, and effectiveness"
        else:
            focus_text = "\n".join(f"- {area}" for area in focus_areas)

        prompt = CRITIQUE_PROMPT.format(
            text=text,
            focus_areas=focus_text
        )

        return await self._call_llm(prompt, temperature=0.5)  # Lower temp for analysis

    # ==========================================================================
    # PROJECT MANAGEMENT
    # ==========================================================================

    def create_project(
        self,
        author_id: str,
        title: str,
        description: str,
        genre: str,
        style: str = "neutral",
        target_word_count: int = 50000
    ) -> AuthorProject:
        """Create new author project (Phase 4.3: with memory support)"""
        import uuid

        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        project = AuthorProject(
            project_id=project_id,
            author_id=author_id,
            title=title,
            description=description,
            genre=genre,
            style=style,
            target_word_count=target_word_count
        )

        # Phase 4.3: Initialize memory
        project.initialize_memory(self.data_path)

        project.save(self.data_path)
        return project

    def load_project(self, author_id: str, project_id: str) -> Optional[AuthorProject]:
        """Load existing project (Phase 4.3: with memory support)"""
        project = AuthorProject.load(self.data_path, author_id, project_id)

        # Phase 4.3: Initialize memory
        if project:
            project.initialize_memory(self.data_path)

        return project

    def list_projects(self, author_id: str) -> List[Dict[str, str]]:
        """List all projects for an author"""
        author_dir = self.data_path / author_id

        if not author_dir.exists():
            return []

        projects = []
        for project_dir in author_dir.iterdir():
            if project_dir.is_dir() and (project_dir / "metadata.json").exists():
                project = AuthorProject.load(self.data_path, author_id, project_dir.name)
                if project:
                    projects.append({
                        "project_id": project.project_id,
                        "title": project.title,
                        "status": project.status,
                        "word_count": project.current_word_count,
                        "completion": f"{project.completion_percentage():.1f}%"
                    })

        return projects
