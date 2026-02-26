"""
Screenplay Formatter Agent

Assembles dialogue and action into a complete, properly
formatted screenplay document.
"""

import logging
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent, AgentResult
from ..models import (
    Screenplay, Scene, SceneHeading,
    DialogueBlock, ActionBlock, Language, StoryAnalysis
)
from ..formats.fountain import FountainWriter
from ..formats.pdf_export import ScreenplayPDFExporter, HAS_REPORTLAB

logger = logging.getLogger(__name__)


class ScreenplayFormatterAgent(BaseAgent):
    """Agent for assembling and formatting screenplays"""

    name = "ScreenplayFormatter"
    description = "Assembles complete formatted screenplay"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fountain_writer = FountainWriter()
        self.pdf_exporter = ScreenplayPDFExporter() if HAS_REPORTLAB else None

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Assemble screenplay from scenes with dialogue and action.

        Args:
            input_data: {
                "title": str,
                "author": str,
                "language": Language,
                "story_analysis": StoryAnalysis,
                "scenes": List[Scene],
            }

        Returns:
            AgentResult with Screenplay object
        """
        self.log_start("Assembling screenplay")

        try:
            title = input_data.get("title", "Untitled")
            author = input_data.get("author", "Unknown")
            language = input_data.get("language", Language.ENGLISH)
            story_analysis: Optional[StoryAnalysis] = input_data.get("story_analysis")
            scenes: List[Scene] = input_data.get("scenes", [])

            if not scenes:
                return AgentResult(
                    success=False,
                    data=None,
                    error="No scenes provided"
                )

            # Build screenplay
            screenplay = Screenplay(
                title=title,
                author=author,
                language=language,
                scenes=scenes,
                genre=story_analysis.genre if story_analysis else "",
                logline=story_analysis.logline if story_analysis else "",
                draft_number=1,
            )

            # Calculate stats
            screenplay.calculate_stats()

            self.log_complete(
                f"{len(scenes)} scenes, {screenplay.total_pages:.1f} pages"
            )

            return AgentResult(
                success=True,
                data=screenplay,
                tokens_used=0,
                cost_usd=0,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(
                success=False,
                data=None,
                error=str(e)
            )

    def assemble_scene(
        self,
        scene: Scene,
        dialogue_blocks: List[DialogueBlock],
        action_blocks: List[Dict],
        is_first: bool = False,
        is_last: bool = False,
    ) -> Scene:
        """
        Assemble a single scene from dialogue and action blocks.

        Args:
            scene: Scene object with metadata
            dialogue_blocks: List of DialogueBlock
            action_blocks: List of action info dicts with placement
            is_first: Whether this is the first scene (prepend FADE IN:)
            is_last: Whether this is the last scene (append FADE OUT.)

        Returns:
            Scene with elements populated
        """
        elements = []

        # FADE IN: for the first scene
        if is_first:
            elements.append(ActionBlock(text="FADE IN:"))

        # Sort action blocks by placement
        opening_actions = [
            ActionBlock(text=a["text"])
            for a in action_blocks
            if a.get("placement") == "before_dialogue" or a.get("type") == "scene_opening"
        ]

        closing_actions = [
            ActionBlock(text=a["text"])
            for a in action_blocks
            if a.get("placement") == "scene_end"
            and a.get("type") != "transition"
        ]

        # Separate transition blocks from action writer
        transition_actions = [
            a for a in action_blocks
            if a.get("type") == "transition"
        ]

        inline_actions = {}
        for a in action_blocks:
            idx = a.get("after_dialogue_index")
            if idx is not None and a.get("type") not in ("scene_opening", "transition") and a.get("placement") != "before_dialogue" and a.get("placement") != "scene_end":
                inline_actions[idx] = ActionBlock(text=a["text"])

        # Opening action
        elements.extend(opening_actions)

        # Interleave dialogue and inline actions
        for i, dialogue in enumerate(dialogue_blocks):
            elements.append(dialogue)
            if i in inline_actions:
                elements.append(inline_actions[i])

        # Closing action
        elements.extend(closing_actions)

        # Add transition at scene end
        if is_last:
            elements.append(ActionBlock(text="FADE OUT."))
        elif transition_actions:
            # Use the transition from action writer
            elements.append(ActionBlock(text=transition_actions[0]["text"]))
        elif scene.transition_out:
            # Use transition from scene architect metadata
            transition = scene.transition_out
            if not transition.endswith(":") and not transition.endswith("."):
                transition += ":"
            elements.append(ActionBlock(text=transition))
        else:
            # Default transition between scenes
            elements.append(ActionBlock(text="CUT TO:"))

        scene.elements = elements
        scene.page_count = self._estimate_page_count(elements)

        return scene

    def _estimate_page_count(self, elements: List) -> float:
        """Estimate page count based on elements"""
        # 1 page = ~56 lines
        # Dialogue block = ~4 lines average
        # Action block = ~2 lines average
        total_lines = 0
        for el in elements:
            if isinstance(el, DialogueBlock):
                total_lines += 3 + len(el.dialogue) // 40
            elif isinstance(el, ActionBlock):
                total_lines += 1 + len(el.text) // 60

        return max(0.5, total_lines / 56)

    def export_fountain(self, screenplay: Screenplay, filepath: str) -> str:
        """Export to Fountain format"""
        return self.fountain_writer.write_to_file(screenplay, filepath)

    def export_pdf(self, screenplay: Screenplay, filepath: str) -> str:
        """Export to PDF format"""
        if not self.pdf_exporter:
            raise ImportError("reportlab required for PDF export")
        return self.pdf_exporter.export(screenplay, filepath)

    def get_fountain_content(self, screenplay: Screenplay) -> str:
        """Get Fountain format as string"""
        return self.fountain_writer.write(screenplay)

    def get_pdf_bytes(self, screenplay: Screenplay) -> bytes:
        """Get PDF as bytes"""
        if not self.pdf_exporter:
            raise ImportError("reportlab required for PDF export")
        return self.pdf_exporter.export_to_bytes(screenplay)
