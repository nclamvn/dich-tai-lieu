"""
Screenplay Studio Agents

Multi-agent pipeline for screenplay generation:

Phase 1 - Analysis:
1. Story Analyst - Analyze source material
2. Scene Architect - Create scene breakdown

Phase 2 - Screenplay:
3. Dialogue Writer - Write dialogue
4. Action Writer - Write action/descriptions
5. Vietnamese Adapter - Cultural adaptation
6. Screenplay Formatter - Assemble final screenplay

Phase 3 - Pre-Visualization:
7. Cinematographer - Design shot lists
8. Visual Designer - Create style guides
9. Storyboarder - Generate storyboard images

Phase 4 - Video Rendering:
10. Prompt Engineer - Create AI video prompts
11. Video Renderer - Generate videos via APIs
12. Video Editor - Stitch and edit videos
"""

from .base_agent import BaseAgent, AgentResult

# Phase 1
from .story_analyst import StoryAnalystAgent
from .scene_architect import SceneArchitectAgent

# Phase 2
from .dialogue_writer import DialogueWriterAgent
from .action_writer import ActionWriterAgent
from .vietnamese_adapter import VietnameseAdapterAgent
from .screenplay_formatter import ScreenplayFormatterAgent

# Phase 3
from .cinematographer import CinematographerAgent
from .visual_designer import VisualDesignerAgent
from .storyboarder import StoryboarderAgent

# Phase 4
from .prompt_engineer import PromptEngineerAgent
from .video_renderer import VideoRendererAgent
from .video_editor import VideoEditorAgent

__all__ = [
    # Base
    "BaseAgent",
    "AgentResult",

    # Phase 1 - Analysis
    "StoryAnalystAgent",
    "SceneArchitectAgent",

    # Phase 2 - Screenplay
    "DialogueWriterAgent",
    "ActionWriterAgent",
    "VietnameseAdapterAgent",
    "ScreenplayFormatterAgent",

    # Phase 3 - Pre-Visualization
    "CinematographerAgent",
    "VisualDesignerAgent",
    "StoryboarderAgent",

    # Phase 4 - Video Rendering
    "PromptEngineerAgent",
    "VideoRendererAgent",
    "VideoEditorAgent",
]
