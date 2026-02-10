"""
Structure building utilities.
"""

from typing import List
from ..models import BookBlueprint


def build_toc(blueprint: BookBlueprint) -> str:
    """Build table of contents string from blueprint."""
    lines = []
    lines.append(f"# {blueprint.title}")
    if blueprint.subtitle:
        lines.append(f"## {blueprint.subtitle}")
    lines.append("")

    for part in blueprint.parts:
        lines.append(f"## Part {part.number}: {part.title}")
        for chapter in part.chapters:
            lines.append(f"  Chapter {chapter.number}: {chapter.title}")
            for section in chapter.sections:
                lines.append(f"    {section.number}. {section.title}")
        lines.append("")

    return "\n".join(lines)


def build_flat_section_list(blueprint: BookBlueprint) -> List[dict]:
    """Build a flat list of all sections with their hierarchy context."""
    result = []
    for part in blueprint.parts:
        for chapter in part.chapters:
            for section in chapter.sections:
                result.append({
                    "section_id": section.id,
                    "section_title": section.title,
                    "chapter_id": chapter.id,
                    "chapter_title": chapter.title,
                    "part_id": part.id,
                    "part_title": part.title,
                    "word_target": section.word_count.target,
                    "word_actual": section.word_count.actual,
                    "status": section.status.value,
                })
    return result
