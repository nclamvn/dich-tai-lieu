"""
Content merging utilities.
"""

from typing import List
from ..models import BookBlueprint, Section


def merge_sections(sections: List[Section], separator: str = "\n\n") -> str:
    """Merge multiple sections into a single content string."""
    contents = []
    for section in sections:
        if section.content:
            contents.append(section.content)
    return separator.join(contents)


def merge_chapter_content(blueprint: BookBlueprint, chapter_id: str) -> str:
    """Merge all sections of a chapter into a single string."""
    chapter = blueprint.get_chapter(chapter_id)
    if not chapter:
        return ""

    parts = []
    if chapter.introduction:
        parts.append(chapter.introduction)

    for section in chapter.sections:
        if section.content:
            parts.append(f"## {section.title}\n\n{section.content}")

    if chapter.summary:
        parts.append(f"## Summary\n\n{chapter.summary}")

    return "\n\n".join(parts)


def merge_full_book(blueprint: BookBlueprint) -> str:
    """Merge entire book into a single string."""
    parts = []

    parts.append(f"# {blueprint.title}\n")
    if blueprint.subtitle:
        parts.append(f"*{blueprint.subtitle}*\n")

    if blueprint.front_matter.preface:
        parts.append(f"## Preface\n\n{blueprint.front_matter.preface}")

    for part in blueprint.parts:
        parts.append(f"\n# Part {part.number}: {part.title}\n")
        if part.introduction:
            parts.append(part.introduction)

        for chapter in part.chapters:
            parts.append(f"\n## Chapter {chapter.number}: {chapter.title}\n")
            if chapter.introduction:
                parts.append(chapter.introduction)

            for section in chapter.sections:
                parts.append(f"\n### {section.title}\n")
                if section.content:
                    parts.append(section.content)

    if blueprint.back_matter.conclusion:
        parts.append(f"\n# Conclusion\n\n{blueprint.back_matter.conclusion}")

    return "\n\n".join(parts)
