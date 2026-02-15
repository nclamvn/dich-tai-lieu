"""
Data Models for Book-to-Cinema Pipeline

This module defines all data structures used throughout the cinema adaptation pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class CinemaStyle(Enum):
    """Available cinema style templates."""
    ANIME = "anime"
    NOIR = "noir"
    BLOCKBUSTER = "blockbuster"
    DOCUMENTARY = "documentary"
    FANTASY = "fantasy"
    HORROR = "horror"
    ROMANTIC = "romantic"
    SCIFI = "scifi"
    CUSTOM = "custom"


class JobStatus(Enum):
    """Cinema job processing status."""
    PENDING = "pending"
    CHUNKING = "chunking"
    ADAPTING = "adapting"
    WRITING_SCREENPLAY = "writing_screenplay"
    GENERATING_PROMPTS = "generating_prompts"
    RENDERING = "rendering"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class CinematicChunk:
    """A text chunk optimized for scene conversion.
    
    Each chunk represents ~2-3 minutes of potential video content.
    """
    chunk_id: str
    text: str
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    
    # Position info
    index: int = 0
    total_chunks: int = 0
    char_start: int = 0
    char_end: int = 0
    word_count: int = 0
    
    # Context for continuity
    previous_summary: Optional[str] = None
    next_preview: Optional[str] = None
    
    def __post_init__(self):
        self.word_count = len(self.text.split())


@dataclass
class CinematicScene:
    """A scene extracted from text, ready for screenplay.
    
    Contains all visual, character, and mood information needed
    to generate a screenplay and video prompts.
    """
    scene_id: str
    chunk_id: str
    original_text: str
    
    # Setting & Location
    setting: str = ""  # "A dark alley in 1920s Chicago"
    time_of_day: str = "day"  # day, night, dawn, dusk
    location_type: str = "interior"  # interior, exterior
    
    # Characters
    characters: List[Dict[str, str]] = field(default_factory=list)
    # [{"name": "John", "description": "tall detective", "emotion": "tense"}]
    
    # Actions & Events
    key_actions: List[str] = field(default_factory=list)
    # ["walks slowly through shadows", "reaches for gun"]
    
    # Dialogue
    dialogue: List[Dict[str, str]] = field(default_factory=list)
    # [{"character": "John", "line": "Who's there?", "direction": "whispers"}]
    
    # Mood & Atmosphere
    mood: str = "neutral"  # tense, romantic, action, peaceful, dark
    emotional_arc: str = ""  # "builds tension", "resolves conflict"
    
    # Visual Suggestions
    camera_suggestions: List[str] = field(default_factory=list)
    # ["wide establishing shot", "close-up on face", "tracking shot"]
    
    lighting_mood: str = ""  # "low-key noir", "bright natural", "moody blue"
    color_palette: List[str] = field(default_factory=list)
    # ["#1a1a2e", "#16213e", "#0f3460"]
    
    # Duration estimate (seconds)
    estimated_duration: int = 15
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "setting": self.setting,
            "time_of_day": self.time_of_day,
            "location_type": self.location_type,
            "characters": self.characters,
            "key_actions": self.key_actions,
            "dialogue": self.dialogue,
            "mood": self.mood,
            "camera_suggestions": self.camera_suggestions,
            "lighting_mood": self.lighting_mood,
            "estimated_duration": self.estimated_duration,
        }


@dataclass
class ScreenplayScene:
    """A single scene in screenplay format."""
    scene_number: int
    scene_id: str
    
    # Scene heading
    int_ext: str  # INT or EXT
    location: str
    time: str  # DAY, NIGHT, CONTINUOUS
    
    # Content
    action_lines: List[str] = field(default_factory=list)
    dialogue_blocks: List[Dict[str, str]] = field(default_factory=list)
    # [{"character": "JOHN", "parenthetical": "(whispering)", "line": "..."}]
    
    # Transitions
    opening_transition: Optional[str] = None  # FADE IN:
    closing_transition: Optional[str] = None  # CUT TO:
    
    def to_screenplay_format(self) -> str:
        """Convert to standard screenplay text format."""
        lines = []
        
        if self.opening_transition:
            lines.append(f"{self.opening_transition}")
            lines.append("")
        
        # Scene heading
        heading = f"{self.int_ext}. {self.location.upper()} - {self.time.upper()}"
        lines.append(heading)
        lines.append("")
        
        # Action and dialogue
        for action in self.action_lines:
            lines.append(action)
            lines.append("")
        
        for block in self.dialogue_blocks:
            lines.append(f"                    {block['character'].upper()}")
            if block.get('parenthetical'):
                lines.append(f"              {block['parenthetical']}")
            lines.append(f"          {block['line']}")
            lines.append("")
        
        if self.closing_transition:
            lines.append(f"                                        {self.closing_transition}")
        
        return "\n".join(lines)


@dataclass
class Screenplay:
    """Complete screenplay document."""
    title: str
    author: str
    scenes: List[ScreenplayScene] = field(default_factory=list)
    
    # Metadata
    genre: str = ""
    style: CinemaStyle = CinemaStyle.BLOCKBUSTER
    estimated_runtime_minutes: int = 0
    
    def to_text(self) -> str:
        """Export as formatted screenplay text."""
        header = f"""
                              {self.title.upper()}
                              
                                Written by
                              {self.author}

{"=" * 60}

"""
        scenes_text = "\n\n".join(s.to_screenplay_format() for s in self.scenes)
        return header + scenes_text


@dataclass
class VideoPrompt:
    """AI video generation prompt for a scene."""
    scene_id: str
    provider: str  # "veo", "runway", "replicate"
    
    # Main prompt
    prompt: str
    negative_prompt: Optional[str] = None
    
    # Video settings
    duration_seconds: int = 5
    aspect_ratio: str = "16:9"
    fps: int = 24
    
    # Style settings
    style_preset: Optional[str] = None
    reference_images: List[str] = field(default_factory=list)
    
    # Provider-specific params
    provider_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "provider": self.provider,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "duration_seconds": self.duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "style_preset": self.style_preset,
            "provider_params": self.provider_params,
        }


@dataclass
class RenderedVideo:
    """A rendered video segment."""
    scene_id: str
    video_path: Path
    
    # Video info
    duration_seconds: float = 0.0
    resolution: str = "1920x1080"
    fps: int = 24
    file_size_bytes: int = 0
    
    # Generation info
    provider: str = ""
    prompt_used: str = ""
    generation_time_seconds: float = 0.0
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CinemaJob:
    """A complete book-to-cinema job."""
    job_id: str
    source_path: Path
    output_dir: Path
    
    # Configuration
    style: CinemaStyle = CinemaStyle.BLOCKBUSTER
    video_provider: str = "veo"
    target_segment_duration: int = 15  # seconds
    
    # Status
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    current_stage: str = ""
    error: Optional[str] = None
    
    # Results
    chunks: List[CinematicChunk] = field(default_factory=list)
    scenes: List[CinematicScene] = field(default_factory=list)
    screenplay: Optional[Screenplay] = None
    prompts: List[VideoPrompt] = field(default_factory=list)
    videos: List[RenderedVideo] = field(default_factory=list)
    final_video_path: Optional[Path] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": str(self.source_path),
            "style": self.style.value,
            "status": self.status.value,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "error": self.error,
            "chunks_count": len(self.chunks),
            "scenes_count": len(self.scenes),
            "videos_count": len(self.videos),
            "final_video": str(self.final_video_path) if self.final_video_path else None,
        }


@dataclass
class StyleTemplate:
    """Cinema style template configuration."""
    name: str
    description: str
    
    # Visual style
    visual_style: str
    color_grading: str
    lighting_style: str
    
    # Camera
    camera_movements: List[str] = field(default_factory=list)
    default_shots: List[str] = field(default_factory=list)
    
    # References
    reference_films: List[str] = field(default_factory=list)
    
    # Technical
    aspect_ratio: str = "16:9"
    default_fps: int = 24
    default_transitions: str = "crossfade"
    
    # Prompt engineering
    prompt_prefix: str = ""
    prompt_suffix: str = ""
    negative_prompt: str = ""
    
    # Audio suggestions
    music_style: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleTemplate":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            visual_style=data.get("visual_style", ""),
            color_grading=data.get("color_grading", ""),
            lighting_style=data.get("lighting_style", ""),
            camera_movements=data.get("camera_movements", []),
            default_shots=data.get("default_shots", []),
            reference_films=data.get("reference_films", []),
            aspect_ratio=data.get("aspect_ratio", "16:9"),
            default_fps=data.get("default_fps", 24),
            default_transitions=data.get("default_transitions", "crossfade"),
            prompt_prefix=data.get("prompt_prefix", ""),
            prompt_suffix=data.get("prompt_suffix", ""),
            negative_prompt=data.get("negative_prompt", ""),
            music_style=data.get("music_style", ""),
        )
