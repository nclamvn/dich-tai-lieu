"""
Fountain Format Writer/Parser

Fountain is an industry-standard plain text screenplay format.
https://fountain.io/syntax

This module provides:
- FountainWriter: Convert Screenplay model to .fountain format
- FountainParser: Parse .fountain files to Screenplay model
"""

import re
import logging
from typing import List
from pathlib import Path

from ..models import (
    Screenplay, Scene, SceneHeading,
    DialogueBlock, ActionBlock, Language
)

logger = logging.getLogger(__name__)


class FountainWriter:
    """Convert Screenplay to Fountain format"""

    def write(self, screenplay: Screenplay) -> str:
        """Convert Screenplay to Fountain format string"""
        lines = []

        # Title page
        lines.extend(self._write_title_page(screenplay))
        lines.append("")
        lines.append("===")  # Page break
        lines.append("")

        # FADE IN:
        lines.append("FADE IN:")
        lines.append("")

        # Scenes
        total_scenes = len(screenplay.scenes)
        for i, scene in enumerate(screenplay.scenes):
            lines.extend(self._write_scene(scene))
            lines.append("")

            # Transition between scenes
            is_last = (i == total_scenes - 1)
            if is_last:
                lines.append("FADE OUT.")
            else:
                transition = getattr(scene, 'transition_out', '') or "CUT TO"
                if not transition.endswith(":"):
                    transition += ":"
                # Fountain spec: transitions end with TO: and are right-aligned
                lines.append(f"> {transition}")
            lines.append("")

        # End
        lines.append("")
        lines.append("> THE END <")

        return "\n".join(lines)

    def write_to_file(self, screenplay: Screenplay, filepath: str) -> str:
        """Write screenplay to .fountain file"""
        content = self.write(screenplay)

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        logger.info(f"Wrote Fountain file: {filepath}")
        return filepath

    def _write_title_page(self, screenplay: Screenplay) -> List[str]:
        """Write title page metadata"""
        lines = [
            f"Title: {screenplay.title}",
            f"Author: {screenplay.author}",
            f"Draft date: {screenplay.draft_number}",
        ]

        if screenplay.contact_info:
            lines.append(f"Contact: {screenplay.contact_info}")

        if screenplay.copyright_notice:
            lines.append(f"Copyright: {screenplay.copyright_notice}")

        return lines

    def _write_scene(self, scene: Scene) -> List[str]:
        """Write a single scene"""
        lines = []

        # Scene heading (slugline) with scene number per Fountain spec
        heading_str = str(scene.heading).upper()
        if not heading_str.startswith(("INT.", "EXT.", "INT/EXT.", "I/E.")):
            heading_str = f".{heading_str}"
        # Fountain scene numbers: INT. LOCATION - TIME #1#
        heading_str = f"{heading_str} #{scene.scene_number}#"
        lines.append(heading_str)
        lines.append("")

        # Scene elements (action and dialogue interleaved)
        for element in scene.elements:
            if isinstance(element, ActionBlock):
                lines.extend(self._write_action(element))
            elif isinstance(element, DialogueBlock):
                lines.extend(self._write_dialogue(element))
            lines.append("")

        return lines

    def _write_action(self, action: ActionBlock) -> List[str]:
        """Write action block"""
        text = action.text.strip()
        return self._wrap_text(text, max_width=60)

    def _write_dialogue(self, dialogue: DialogueBlock) -> List[str]:
        """Write dialogue block"""
        lines = []

        # Character name (uppercase)
        lines.append(dialogue.character.upper())

        # Parenthetical (if any)
        if dialogue.parenthetical:
            paren = dialogue.parenthetical.strip()
            if not paren.startswith("("):
                paren = f"({paren})"
            if not paren.endswith(")"):
                paren = f"{paren})"
            lines.append(paren)

        # Dialogue text
        lines.append(dialogue.dialogue)

        return lines

    def _wrap_text(self, text: str, max_width: int = 60) -> List[str]:
        """Wrap text to max width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]


class FountainParser:
    """Parse Fountain format to Screenplay model"""

    # Regex patterns for Fountain elements
    SCENE_HEADING = re.compile(
        r'^\.?(?P<int_ext>INT|EXT|INT\.?/EXT|I\.?/E)\.?\s+'
        r'(?P<location>.+?)\s*[-\u2013\u2014]\s*(?P<time>.+)$',
        re.IGNORECASE
    )

    CHARACTER = re.compile(r'^[A-Z][A-Z\s.\-\']+(\s*\(.*\))?$')
    PARENTHETICAL = re.compile(r'^\s*\(.*\)\s*$')
    TRANSITION = re.compile(r'^[A-Z\s]+:$|^>\s*.+$')
    PAGE_BREAK = re.compile(r'^===+$')
    TITLE_PAGE = re.compile(r'^(Title|Author|Draft|Contact|Copyright):\s*(.+)$', re.IGNORECASE)

    def parse(self, content: str) -> Screenplay:
        """Parse Fountain content to Screenplay"""
        lines = content.split('\n')

        # Parse title page
        title = "Untitled"
        author = "Unknown"
        draft = 1

        title_page_end = 0
        for i, line in enumerate(lines):
            match = self.TITLE_PAGE.match(line)
            if match:
                key, value = match.groups()
                key = key.lower()
                if key == "title":
                    title = value.strip()
                elif key == "author":
                    author = value.strip()
                elif key == "draft":
                    try:
                        draft = int(value.strip())
                    except ValueError:
                        pass
                title_page_end = i
            elif self.PAGE_BREAK.match(line):
                title_page_end = i
                break
            elif line.strip() and not match:
                break

        # Parse scenes
        scenes = self._parse_scenes(lines[title_page_end + 1:])

        screenplay = Screenplay(
            title=title,
            author=author,
            language=Language.ENGLISH,
            scenes=scenes,
            draft_number=draft,
        )
        screenplay.calculate_stats()

        return screenplay

    def parse_file(self, filepath: str) -> Screenplay:
        """Parse .fountain file"""
        content = Path(filepath).read_text(encoding="utf-8")
        return self.parse(content)

    def _parse_scenes(self, lines: List[str]) -> List[Scene]:
        """Parse scene content"""
        scenes = []
        current_scene = None
        current_elements = []
        current_character = None

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Scene heading
            heading_match = self.SCENE_HEADING.match(line)
            if heading_match or (line.startswith('.') and len(line) > 1 and not line.startswith('..')):
                # Save previous scene
                if current_scene:
                    current_scene.elements = current_elements
                    scenes.append(current_scene)

                # Parse new scene heading
                if heading_match:
                    int_ext = heading_match.group('int_ext').upper()
                    if '/' in int_ext:
                        int_ext = 'INT/EXT'
                    location = heading_match.group('location')
                    time = heading_match.group('time')
                else:
                    # Forced scene heading with .
                    parts = line[1:].split(' - ')
                    location = parts[0] if parts else line[1:]
                    time = parts[1] if len(parts) > 1 else "DAY"
                    int_ext = "INT" if "INT" in location.upper() else "EXT"

                current_scene = Scene(
                    scene_number=len(scenes) + 1,
                    heading=SceneHeading(
                        int_ext=int_ext,
                        location=location.strip(),
                        time=time.strip().upper(),
                    ),
                )
                current_elements = []
                current_character = None

            # Character name
            elif self.CHARACTER.match(line) and not self.TRANSITION.match(line):
                current_character = line.strip()

            # Parenthetical
            elif self.PARENTHETICAL.match(line) and current_character:
                # Will be attached to next dialogue
                pass

            # Dialogue (after character)
            elif current_character:
                # Check if previous line was parenthetical
                paren = None
                if i > 0:
                    prev = lines[i - 1].strip()
                    if self.PARENTHETICAL.match(prev):
                        paren = prev.strip("() ")

                current_elements.append(DialogueBlock(
                    character=current_character.split('(')[0].strip(),
                    dialogue=line,
                    parenthetical=paren,
                ))
                current_character = None

            # Action (default)
            else:
                if line and not self.TRANSITION.match(line):
                    current_elements.append(ActionBlock(text=line))

            i += 1

        # Save last scene
        if current_scene:
            current_scene.elements = current_elements
            scenes.append(current_scene)

        return scenes
