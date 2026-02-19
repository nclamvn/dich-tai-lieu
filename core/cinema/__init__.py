"""
Book-to-Cinema: AI-Powered Book to Video Adaptation Engine

This module provides a complete pipeline to transform books into cinematic videos:
1. Intelligent text chunking into scene-sized segments
2. Scene extraction and adaptation
Cinema Module - Book-to-Cinema AI Video Production

This module provides tools to transform books and text documents
into cinematic video productions using AI.

Main Components:
- CinemaOrchestrator: Main pipeline controller
- CinemaChunker: Scene-optimized text chunking
- SceneAdapter: Text to cinematic scene conversion
- ScreenplayWriter: Scene to screenplay format
- CinemaPromptGenerator: AI video prompt generation
- VideoRenderer: Multi-provider video rendering
- VideoAssembler: FFmpeg video concatenation
"""

from .models import (
    CinematicChunk,
    CinematicScene,
    ScreenplayScene,
    Screenplay,
    VideoPrompt,
    RenderedVideo,
    CinemaJob,
    CinemaStyle,
    StyleTemplate,
    JobStatus,
)
from .cinema_chunker import CinemaChunker
from .scene_adapter import SceneAdapter
from .screenplay_writer import ScreenplayWriter
from .prompt_generator import CinemaPromptGenerator
from .video_renderer import VideoRenderer
from .video_assembler import VideoAssembler
from .cinema_orchestrator import CinemaOrchestrator

__all__ = [
    # Data models
    "CinematicChunk",
    "CinematicScene",
    "ScreenplayScene",
    "Screenplay",
    "VideoPrompt",
    "RenderedVideo",
    "CinemaStyle",
    "CinemaJob",
    "JobStatus",
    # Components
    "CinemaChunker",
    "SceneAdapter",
    "ScreenplayWriter",
    "CinemaPromptGenerator",
    "VideoRenderer",
    "VideoAssembler",
    "CinemaOrchestrator",
]

__version__ = "0.1.0"
