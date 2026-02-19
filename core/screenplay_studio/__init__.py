"""
Screenplay Studio - AI-Powered Screenplay Adaptation & Video Generation

This module provides a multi-agent pipeline for:
1. Analyzing stories/novels
2. Generating professional screenplays
3. Creating shot lists and storyboards
4. Rendering AI-generated video scenes
"""

from .models import (
    ProjectTier,
    VideoProvider,
    ProjectStatus,
    Language,
    Character,
    StoryAnalysis,
    Scene,
    SceneHeading,
    DialogueBlock,
    ActionBlock,
    Screenplay,
    Shot,
    ShotList,
    ShotType,
    CameraMovement,
    CameraAngle,
    VideoPrompt,
    VideoClip,
    ScreenplayProject,
)

from .pipeline import ScreenplayPipeline
from .database import ScreenplayRepository
from .cost_calculator import CostCalculator

__all__ = [
    # Enums
    "ProjectTier",
    "VideoProvider",
    "ProjectStatus",
    "Language",
    "ShotType",
    "CameraMovement",
    "CameraAngle",
    # Models
    "Character",
    "StoryAnalysis",
    "Scene",
    "SceneHeading",
    "DialogueBlock",
    "ActionBlock",
    "Screenplay",
    "Shot",
    "ShotList",
    "VideoPrompt",
    "VideoClip",
    "ScreenplayProject",
    # Services
    "ScreenplayPipeline",
    "ScreenplayRepository",
    "CostCalculator",
]

__version__ = "1.0.0"
