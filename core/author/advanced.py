"""
Advanced Author Engine Features (Phase 4.4)

Provides:
- Memory-aware content generation
- Variation quality scoring and ranking
- Consistency validation
- Export utilities (character glossary, timeline export)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class ScoredVariation:
    """A variation with quality/consistency scores"""
    text: str
    style: str
    word_count: int

    # Quality scores
    consistency_score: float = 0.0  # 0-1: Memory consistency
    coherence_score: float = 0.0     # 0-1: Logical flow
    style_score: float = 0.0          # 0-1: Style matching
    overall_score: float = 0.0        # Combined score

    # Consistency issues (if any)
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []

        # Calculate overall score (weighted average)
        self.overall_score = (
            self.consistency_score * 0.4 +
            self.coherence_score * 0.3 +
            self.style_score * 0.3
        )


class VariationScorer:
    """
    Scores and ranks variations based on:
    - Memory consistency (character attributes, plot continuity)
    - Coherence (logical flow, grammar)
    - Style matching
    """

    def __init__(self, project=None):
        """
        Initialize scorer

        Args:
            project: AuthorProject with memory (optional)
        """
        self.project = project

    def score_variation(
        self,
        text: str,
        style: str,
        chapter: Optional[int] = None
    ) -> ScoredVariation:
        """
        Score a single variation

        Args:
            text: Variation text
            style: Target style
            chapter: Current chapter (for memory context)

        Returns:
            ScoredVariation with all scores
        """
        word_count = len(text.split())
        issues = []

        # Score consistency with memory
        consistency_score = self._score_consistency(text, chapter, issues)

        # Score coherence
        coherence_score = self._score_coherence(text)

        # Score style matching
        style_score = self._score_style(text, style)

        return ScoredVariation(
            text=text,
            style=style,
            word_count=word_count,
            consistency_score=consistency_score,
            coherence_score=coherence_score,
            style_score=style_score,
            issues=issues
        )

    def rank_variations(
        self,
        variations: List[Dict],
        chapter: Optional[int] = None
    ) -> List[ScoredVariation]:
        """
        Score and rank multiple variations

        Args:
            variations: List of variation dicts {"text": str, "style": str}
            chapter: Current chapter

        Returns:
            List of ScoredVariation, sorted by score (best first)
        """
        scored = []

        for var in variations:
            scored_var = self.score_variation(
                text=var["text"],
                style=var.get("style", "neutral"),
                chapter=chapter
            )
            scored.append(scored_var)

        # Sort by overall score (descending)
        scored.sort(key=lambda v: v.overall_score, reverse=True)

        return scored

    def _score_consistency(
        self,
        text: str,
        chapter: Optional[int],
        issues: List[str]
    ) -> float:
        """
        Score consistency with project memory

        Checks:
        - Character name consistency
        - Attribute consistency
        - Timeline coherence

        Returns:
            Score 0-1 (1 = perfect consistency)
        """
        if not self.project or not self.project.memory:
            return 1.0  # No memory to check against

        score = 1.0
        memory = self.project.memory

        # Check character mentions
        characters = memory.list_characters(chapter)

        for char in characters:
            # Check if character mentioned
            if char.name.lower() in text.lower():
                # Check attribute consistency
                for attr, values in char.mentioned_attributes.items():
                    if len(values) > 1:
                        # Multiple values exist - check which is used
                        for value in values:
                            if value.lower() in text.lower():
                                # Using one of the conflicting values
                                score -= 0.1
                                issues.append(
                                    f"Using '{value}' for {char.name}'s {attr} "
                                    f"(conflicts with {[v for v in values if v != value]})"
                                )
                                break

        return max(0.0, score)

    def _score_coherence(self, text: str) -> float:
        """
        Score logical coherence and grammar

        Simple heuristics:
        - Sentence structure
        - Word repetition
        - Length appropriateness

        Returns:
            Score 0-1
        """
        score = 1.0

        # Check for very short text
        if len(text) < 50:
            score -= 0.3

        # Check for excessive repetition
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.5:  # Too much repetition
                score -= 0.2

        # Check for incomplete sentences (very basic)
        sentences = text.split('.')
        if sentences and len(sentences[-1].strip()) < 5:
            score -= 0.1

        return max(0.0, score)

    def _score_style(self, text: str, target_style: str) -> float:
        """
        Score style matching

        Basic heuristics based on target style

        Returns:
            Score 0-1
        """
        score = 0.7  # Base score
        text_lower = text.lower()

        # Style-specific indicators
        if target_style == "formal":
            # Formal: Longer sentences, precise vocabulary
            avg_sentence_len = len(text.split()) / max(1, text.count('.'))
            if avg_sentence_len > 15:
                score += 0.2
            if any(word in text_lower for word in ["furthermore", "consequently", "therefore"]):
                score += 0.1

        elif target_style == "casual":
            # Casual: Contractions, shorter sentences
            if "'" in text:  # Contractions
                score += 0.15
            avg_sentence_len = len(text.split()) / max(1, text.count('.'))
            if avg_sentence_len < 15:
                score += 0.15

        elif target_style == "narrative":
            # Narrative: Descriptive language, varied sentence structure
            descriptive_words = ["vivid", "gently", "suddenly", "quietly", "beautiful"]
            if any(word in text_lower for word in descriptive_words):
                score += 0.2

        elif target_style == "academic":
            # Academic: Citations style, analytical language
            academic_words = ["analysis", "theory", "research", "evidence", "demonstrates"]
            if any(word in text_lower for word in academic_words):
                score += 0.2

        return min(1.0, score)


class MemoryContextBuilder:
    """
    Builds memory-enriched context for content generation

    Retrieves relevant information from project memory to enhance prompts
    """

    def __init__(self, project):
        """
        Initialize context builder

        Args:
            project: AuthorProject with memory
        """
        self.project = project

    def build_context_for_chapter(
        self,
        chapter: int,
        focus: Optional[str] = None
    ) -> str:
        """
        Build comprehensive context for writing a chapter

        Args:
            chapter: Chapter number being written
            focus: Optional focus (character name, theme, etc.)

        Returns:
            Formatted context string to add to prompts
        """
        if not self.project or not self.project.memory:
            return ""

        context_parts = []
        memory = self.project.memory

        # Active characters
        chars = memory.list_characters(chapter)
        if chars:
            char_info = []
            for char in chars[:5]:  # Top 5 active
                traits_str = ", ".join(char.traits) if char.traits else "none specified"
                char_info.append(f"- {char.name} ({char.role}): {char.description} [Traits: {traits_str}]")

            if char_info:
                context_parts.append("**Active Characters:**\n" + "\n".join(char_info))

        # Recent timeline
        timeline_summary = memory.get_timeline_summary(chapter - 1)
        if timeline_summary and timeline_summary != "No significant events recorded yet.":
            context_parts.append(f"**Recent Events:**\n{timeline_summary}")

        # Active plot points
        active_plots = memory.list_active_plot_points()
        if active_plots:
            plot_info = []
            for plot in active_plots[:3]:  # Top 3
                plot_info.append(f"- {plot.type.title()}: {plot.description}")

            if plot_info:
                context_parts.append("**Active Plot Threads:**\n" + "\n".join(plot_info))

        # Vector memory context (if available)
        if self.project.vector_memory and focus:
            results = self.project.vector_memory.search(focus, n_results=3)
            if results:
                vector_context = []
                for text, score, metadata in results:
                    ch = metadata.get('chapter', '?')
                    vector_context.append(f"- Ch.{ch}: {text[:150]}...")

                if vector_context:
                    context_parts.append("**Relevant Past Context:**\n" + "\n".join(vector_context))

        return "\n\n".join(context_parts) if context_parts else ""


class ExportUtilities:
    """
    Export utilities for Author Mode projects

    Generates:
    - Character glossary
    - Timeline document
    - Plot summary
    - World building guide
    """

    def __init__(self, project):
        """
        Initialize export utilities

        Args:
            project: AuthorProject with memory
        """
        self.project = project

    def generate_character_glossary(self, format: str = "markdown") -> str:
        """
        Generate character glossary

        Args:
            format: Output format ("markdown", "txt", "html")

        Returns:
            Formatted character glossary
        """
        if not self.project or not self.project.memory:
            return "No character data available."

        characters = self.project.memory.list_characters()

        if not characters:
            return "No characters recorded."

        # Sort by first appearance
        characters.sort(key=lambda c: c.first_appearance_chapter or 999)

        if format == "markdown":
            lines = ["# Character Glossary\n"]

            for char in characters:
                lines.append(f"## {char.name}")

                if char.aliases:
                    lines.append(f"**Aliases:** {', '.join(char.aliases)}")

                if char.role:
                    lines.append(f"**Role:** {char.role}")

                if char.description:
                    lines.append(f"\n{char.description}")

                if char.traits:
                    lines.append(f"\n**Traits:** {', '.join(char.traits)}")

                if char.relationships:
                    lines.append("\n**Relationships:**")
                    for name, rel in char.relationships.items():
                        lines.append(f"- {name}: {rel}")

                lines.append(f"\n**First Appearance:** Chapter {char.first_appearance_chapter or 'Unknown'}")
                lines.append("")

            return "\n".join(lines)

        else:  # Plain text
            lines = ["CHARACTER GLOSSARY\n" + "=" * 50 + "\n"]

            for char in characters:
                lines.append(f"{char.name}")
                lines.append("-" * len(char.name))

                if char.description:
                    lines.append(char.description)

                if char.traits:
                    lines.append(f"Traits: {', '.join(char.traits)}")

                lines.append(f"First appears: Chapter {char.first_appearance_chapter or 'Unknown'}")
                lines.append("")

            return "\n".join(lines)

    def generate_timeline_document(self, format: str = "markdown") -> str:
        """
        Generate timeline document

        Args:
            format: Output format

        Returns:
            Formatted timeline
        """
        if not self.project or not self.project.memory:
            return "No timeline data available."

        events = self.project.memory.get_events()

        if not events:
            return "No events recorded."

        if format == "markdown":
            lines = ["# Project Timeline\n"]

            current_chapter = None
            for event in events:
                if event.chapter != current_chapter:
                    current_chapter = event.chapter
                    lines.append(f"\n## Chapter {current_chapter}\n")

                lines.append(f"**{event.description}**")

                if event.participants:
                    lines.append(f"- Participants: {', '.join(event.participants)}")

                if event.location:
                    lines.append(f"- Location: {event.location}")

                lines.append("")

            return "\n".join(lines)

        else:
            lines = ["PROJECT TIMELINE\n" + "=" * 50 + "\n"]

            for event in events:
                lines.append(f"Chapter {event.chapter}: {event.description}")

            return "\n".join(lines)

    def generate_plot_summary(self, format: str = "markdown") -> str:
        """
        Generate plot summary document

        Args:
            format: Output format

        Returns:
            Formatted plot summary
        """
        if not self.project or not self.project.memory:
            return "No plot data available."

        plot_points = list(self.project.memory.plot_points.values())

        if not plot_points:
            return "No plot points recorded."

        # Separate by status
        active = [p for p in plot_points if p.status == "active"]
        resolved = [p for p in plot_points if p.status == "resolved"]

        if format == "markdown":
            lines = ["# Plot Summary\n"]

            if active:
                lines.append("## Active Plot Threads\n")
                for plot in active:
                    lines.append(f"### {plot.type.title()}: {plot.description}")
                    lines.append(f"Introduced: Chapter {plot.first_introduced_chapter}\n")

            if resolved:
                lines.append("\n## Resolved Plot Threads\n")
                for plot in resolved:
                    lines.append(f"### {plot.type.title()}: {plot.description}")
                    lines.append(f"Chapters {plot.first_introduced_chapter}-{plot.resolution_chapter}\n")

            return "\n".join(lines)

        else:
            lines = ["PLOT SUMMARY\n" + "=" * 50 + "\n"]

            if active:
                lines.append("ACTIVE THREADS:")
                for plot in active:
                    lines.append(f"- {plot.description} (Ch.{plot.first_introduced_chapter})")
                lines.append("")

            if resolved:
                lines.append("RESOLVED THREADS:")
                for plot in resolved:
                    lines.append(f"- {plot.description} (Ch.{plot.first_introduced_chapter}-{plot.resolution_chapter})")

            return "\n".join(lines)
