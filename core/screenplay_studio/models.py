"""
Screenplay Studio Data Models

Professional screenplay and video production data structures.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import json


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectTier(str, Enum):
    """Pricing tier for project features"""
    FREE = "free"           # Screenplay only
    STANDARD = "standard"   # + Storyboard images
    PRO = "pro"            # + Video generation
    DIRECTOR = "director"   # + Multi-take, editing


class VideoProvider(str, Enum):
    """AI video generation providers"""
    PIKA = "pika"           # Budget option ~$0.02/sec
    RUNWAY = "runway"       # Balanced ~$0.05/sec
    VEO = "veo"            # Best quality ~$0.08/sec


class ProjectStatus(str, Enum):
    """Project processing status"""
    DRAFT = "draft"
    ANALYZING = "analyzing"
    WRITING = "writing"
    VISUALIZING = "visualizing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    VIETNAMESE = "vi"


class ShotType(str, Enum):
    """Standard cinematography shot types"""
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM_WIDE = "medium_wide"
    MEDIUM = "medium"
    MEDIUM_CLOSE = "medium_close"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    POV = "pov"
    OVER_SHOULDER = "over_shoulder"
    TWO_SHOT = "two_shot"
    INSERT = "insert"


class CameraMovement(str, Enum):
    """Camera movement types"""
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class CameraAngle(str, Enum):
    """Camera angle types"""
    EYE_LEVEL = "eye_level"
    HIGH = "high"
    LOW = "low"
    DUTCH = "dutch"
    BIRDS_EYE = "birds_eye"
    WORMS_EYE = "worms_eye"


# ═══════════════════════════════════════════════════════════════════════════════
# STORY ANALYSIS MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Character:
    """Character profile extracted from story"""
    name: str
    description: str
    role: str  # protagonist, antagonist, supporting, minor
    arc: str  # Character development arc
    traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # {name: relationship}
    visual_description: Optional[str] = None  # For AI image generation
    age_range: Optional[str] = None
    gender: Optional[str] = None
    reference_images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "arc": self.arc,
            "traits": self.traits,
            "relationships": self.relationships,
            "visual_description": self.visual_description,
            "age_range": self.age_range,
            "gender": self.gender,
            "reference_images": self.reference_images,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        return cls(**data)


@dataclass
class StoryAnalysis:
    """Complete story analysis from Phase 1"""

    # Basic info
    title: str
    logline: str  # One-sentence summary
    synopsis: str  # Short paragraph summary

    # Genre & tone
    genre: str
    sub_genres: List[str] = field(default_factory=list)
    tone: str = ""
    themes: List[str] = field(default_factory=list)

    # Setting
    setting: str = ""
    time_period: str = ""
    locations: List[str] = field(default_factory=list)

    # Structure
    structure_type: str = "three_act"  # three_act, heroes_journey, five_act
    act_breakdown: Dict[str, str] = field(default_factory=dict)

    # Characters
    characters: List[Character] = field(default_factory=list)

    # Dramatic elements
    inciting_incident: str = ""
    midpoint: str = ""
    climax: str = ""
    resolution: str = ""
    key_scenes: List[str] = field(default_factory=list)

    # Estimates
    estimated_runtime_minutes: int = 0
    estimated_scenes: int = 0
    estimated_pages: int = 0

    # Metadata
    language: Language = Language.ENGLISH
    cultural_notes: List[str] = field(default_factory=list)  # For Vietnamese content

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "logline": self.logline,
            "synopsis": self.synopsis,
            "genre": self.genre,
            "sub_genres": self.sub_genres,
            "tone": self.tone,
            "themes": self.themes,
            "setting": self.setting,
            "time_period": self.time_period,
            "locations": self.locations,
            "structure_type": self.structure_type,
            "act_breakdown": self.act_breakdown,
            "characters": [c.to_dict() for c in self.characters],
            "inciting_incident": self.inciting_incident,
            "midpoint": self.midpoint,
            "climax": self.climax,
            "resolution": self.resolution,
            "key_scenes": self.key_scenes,
            "estimated_runtime_minutes": self.estimated_runtime_minutes,
            "estimated_scenes": self.estimated_scenes,
            "estimated_pages": self.estimated_pages,
            "language": self.language.value,
            "cultural_notes": self.cultural_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StoryAnalysis":
        data = data.copy()
        data["characters"] = [Character.from_dict(c) for c in data.get("characters", [])]
        data["language"] = Language(data.get("language", "en"))
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENPLAY MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SceneHeading:
    """Scene heading (slugline) in screenplay format"""
    int_ext: str  # INT or EXT
    location: str
    time: str  # DAY, NIGHT, CONTINUOUS, LATER, etc.

    def __str__(self) -> str:
        return f"{self.int_ext}. {self.location.upper()} - {self.time.upper()}"

    def to_dict(self) -> Dict:
        return {
            "int_ext": self.int_ext,
            "location": self.location,
            "time": self.time,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SceneHeading":
        return cls(**data)


@dataclass
class DialogueBlock:
    """Dialogue in screenplay format"""
    character: str
    dialogue: str
    parenthetical: Optional[str] = None  # (whispering), (to John)

    def to_fountain(self) -> str:
        """Convert to Fountain format"""
        lines = [f"\n{self.character.upper()}"]
        if self.parenthetical:
            lines.append(f"({self.parenthetical})")
        lines.append(self.dialogue)
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "type": "dialogue",
            "character": self.character,
            "dialogue": self.dialogue,
            "parenthetical": self.parenthetical,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DialogueBlock":
        return cls(
            character=data["character"],
            dialogue=data["dialogue"],
            parenthetical=data.get("parenthetical"),
        )


@dataclass
class ActionBlock:
    """Action/description in screenplay format"""
    text: str

    def to_fountain(self) -> str:
        """Convert to Fountain format"""
        return f"\n{self.text}"

    def to_dict(self) -> Dict:
        return {
            "type": "action",
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ActionBlock":
        return cls(text=data["text"])


@dataclass
class Scene:
    """A single scene in the screenplay"""
    scene_number: int
    heading: SceneHeading

    # Content - list of ActionBlock and DialogueBlock
    elements: List[Union[ActionBlock, DialogueBlock]] = field(default_factory=list)

    # Metadata
    summary: str = ""
    characters_present: List[str] = field(default_factory=list)
    emotional_beat: str = ""
    purpose: str = ""  # What this scene accomplishes in the story

    # Timing
    estimated_duration_seconds: int = 60
    page_count: float = 1.0  # 1 page ≈ 1 minute

    # Visual notes for later phases
    visual_notes: Optional[str] = None
    mood: Optional[str] = None

    # Generated content (filled in later phases)
    shot_list: Optional["ShotList"] = None
    storyboard_images: List[str] = field(default_factory=list)
    video_clips: List[str] = field(default_factory=list)

    def to_fountain(self) -> str:
        """Convert to Fountain format"""
        lines = [f"\n{self.heading}"]
        for element in self.elements:
            lines.append(element.to_fountain())
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        elements_data = []
        for el in self.elements:
            elements_data.append(el.to_dict())

        return {
            "scene_number": self.scene_number,
            "heading": self.heading.to_dict(),
            "elements": elements_data,
            "summary": self.summary,
            "characters_present": self.characters_present,
            "emotional_beat": self.emotional_beat,
            "purpose": self.purpose,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "page_count": self.page_count,
            "visual_notes": self.visual_notes,
            "mood": self.mood,
            "storyboard_images": self.storyboard_images,
            "video_clips": self.video_clips,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Scene":
        data = data.copy()
        data["heading"] = SceneHeading.from_dict(data["heading"])

        elements = []
        for el in data.get("elements", []):
            if el.get("type") == "dialogue":
                elements.append(DialogueBlock.from_dict(el))
            else:
                elements.append(ActionBlock.from_dict(el))
        data["elements"] = elements

        # Remove shot_list from dict - handle separately
        data.pop("shot_list", None)

        return cls(**data)


@dataclass
class Screenplay:
    """Complete screenplay document"""
    title: str
    author: str
    language: Language

    # Content
    scenes: List[Scene] = field(default_factory=list)

    # Metadata
    genre: str = ""
    logline: str = ""
    draft_number: int = 1

    # Optional front matter
    contact_info: Optional[str] = None
    copyright_notice: Optional[str] = None

    # Stats (calculated)
    total_pages: float = 0
    total_runtime_minutes: int = 0

    def calculate_stats(self):
        """Calculate total pages and runtime"""
        self.total_pages = sum(s.page_count for s in self.scenes)
        self.total_runtime_minutes = int(self.total_pages)  # 1 page ≈ 1 minute

    def to_fountain(self) -> str:
        """Export to Fountain format"""
        lines = [
            f"Title: {self.title}",
            f"Author: {self.author}",
            f"Draft: {self.draft_number}",
            "",
        ]

        if self.contact_info:
            lines.append(f"Contact: {self.contact_info}")

        lines.append("")
        lines.append("===")  # Page break before content
        lines.append("")

        for scene in self.scenes:
            lines.append(scene.to_fountain())

        lines.append("")
        lines.append("THE END")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "author": self.author,
            "language": self.language.value,
            "scenes": [s.to_dict() for s in self.scenes],
            "genre": self.genre,
            "logline": self.logline,
            "draft_number": self.draft_number,
            "contact_info": self.contact_info,
            "copyright_notice": self.copyright_notice,
            "total_pages": self.total_pages,
            "total_runtime_minutes": self.total_runtime_minutes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Screenplay":
        data = data.copy()
        data["language"] = Language(data.get("language", "en"))
        data["scenes"] = [Scene.from_dict(s) for s in data.get("scenes", [])]
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# CINEMATOGRAPHY MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Shot:
    """A single camera shot"""
    shot_number: str  # "1A", "1B", etc.
    shot_type: ShotType
    description: str

    # Camera settings
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    camera_movement: CameraMovement = CameraMovement.STATIC
    lens: str = "50mm"

    # Timing
    duration_seconds: int = 3

    # Technical notes
    lighting_notes: str = ""
    color_notes: str = ""
    audio_notes: str = ""

    # AI generation (filled in later)
    ai_prompt: Optional[str] = None
    storyboard_image: Optional[str] = None
    video_clip: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "shot_number": self.shot_number,
            "shot_type": self.shot_type.value,
            "description": self.description,
            "camera_angle": self.camera_angle.value,
            "camera_movement": self.camera_movement.value,
            "lens": self.lens,
            "duration_seconds": self.duration_seconds,
            "lighting_notes": self.lighting_notes,
            "color_notes": self.color_notes,
            "audio_notes": self.audio_notes,
            "ai_prompt": self.ai_prompt,
            "storyboard_image": self.storyboard_image,
            "video_clip": self.video_clip,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Shot":
        data = data.copy()
        data["shot_type"] = ShotType(data["shot_type"])
        data["camera_angle"] = CameraAngle(data.get("camera_angle", "eye_level"))
        data["camera_movement"] = CameraMovement(data.get("camera_movement", "static"))
        return cls(**data)


@dataclass
class ShotList:
    """Shot list for a scene"""
    scene_number: int
    shots: List[Shot] = field(default_factory=list)

    # Overall scene visual notes
    visual_style: str = ""
    color_palette: List[str] = field(default_factory=list)
    reference_films: List[str] = field(default_factory=list)
    mood_board_images: List[str] = field(default_factory=list)

    def total_duration_seconds(self) -> int:
        return sum(s.duration_seconds for s in self.shots)

    def to_dict(self) -> Dict:
        return {
            "scene_number": self.scene_number,
            "shots": [s.to_dict() for s in self.shots],
            "visual_style": self.visual_style,
            "color_palette": self.color_palette,
            "reference_films": self.reference_films,
            "mood_board_images": self.mood_board_images,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ShotList":
        data = data.copy()
        data["shots"] = [Shot.from_dict(s) for s in data.get("shots", [])]
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO GENERATION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VideoPrompt:
    """AI video generation prompt"""
    shot_id: str
    scene_number: int

    # Prompts
    prompt: str
    negative_prompt: str = ""

    # Technical settings
    duration_seconds: int = 5
    aspect_ratio: str = "16:9"  # 16:9, 2.39:1, 4:3, 9:16
    style: str = "cinematic"

    # Camera
    camera_motion: str = "static"

    # Quality
    quality_preset: str = "standard"  # draft, standard, high

    # Provider specific
    provider: VideoProvider = VideoProvider.RUNWAY
    provider_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "shot_id": self.shot_id,
            "scene_number": self.scene_number,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "duration_seconds": self.duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "style": self.style,
            "camera_motion": self.camera_motion,
            "quality_preset": self.quality_preset,
            "provider": self.provider.value,
            "provider_params": self.provider_params,
        }


@dataclass
class VideoClip:
    """Generated video clip"""
    shot_id: str
    provider: VideoProvider

    # Files
    file_path: str
    thumbnail_path: Optional[str] = None

    # Metadata
    duration_seconds: float = 0
    resolution: str = "1920x1080"
    file_size_bytes: int = 0

    # Generation info
    prompt_used: str = ""
    generation_time_seconds: float = 0
    cost_usd: float = 0

    # Selection
    take_number: int = 1
    is_selected: bool = False

    def to_dict(self) -> Dict:
        return {
            "shot_id": self.shot_id,
            "provider": self.provider.value,
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "file_size_bytes": self.file_size_bytes,
            "prompt_used": self.prompt_used,
            "generation_time_seconds": self.generation_time_seconds,
            "cost_usd": self.cost_usd,
            "take_number": self.take_number,
            "is_selected": self.is_selected,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScreenplayProject:
    """Main project container"""
    id: str
    user_id: str

    # Basic info
    title: str
    source_type: str = "novel"  # novel, short_story, original, script
    language: Language = Language.ENGLISH

    # Tier & provider
    tier: ProjectTier = ProjectTier.FREE
    video_provider: Optional[VideoProvider] = None

    # Status
    status: ProjectStatus = ProjectStatus.DRAFT
    current_phase: int = 0  # 0=not started, 1-4
    progress_percent: float = 0
    error_message: Optional[str] = None

    # Source content
    source_text: str = ""
    source_file_path: Optional[str] = None

    # Generated content
    story_analysis: Optional[StoryAnalysis] = None
    screenplay: Optional[Screenplay] = None

    # Cost tracking
    estimated_cost_usd: float = 0
    actual_cost_usd: float = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Output files
    output_files: Dict[str, str] = field(default_factory=dict)
    # Keys: screenplay_fountain, screenplay_pdf, storyboard_pdf, video_scene_N, video_final

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "source_type": self.source_type,
            "language": self.language.value,
            "tier": self.tier.value,
            "video_provider": self.video_provider.value if self.video_provider else None,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
            "source_text": self.source_text,
            "source_file_path": self.source_file_path,
            "story_analysis": self.story_analysis.to_dict() if self.story_analysis else None,
            "screenplay": self.screenplay.to_dict() if self.screenplay else None,
            "estimated_cost_usd": self.estimated_cost_usd,
            "actual_cost_usd": self.actual_cost_usd,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_files": self.output_files,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ScreenplayProject":
        data = data.copy()

        data["language"] = Language(data.get("language", "en"))
        data["tier"] = ProjectTier(data.get("tier", "free"))
        data["status"] = ProjectStatus(data.get("status", "draft"))

        if data.get("video_provider"):
            data["video_provider"] = VideoProvider(data["video_provider"])

        if data.get("story_analysis"):
            data["story_analysis"] = StoryAnalysis.from_dict(data["story_analysis"])

        if data.get("screenplay"):
            data["screenplay"] = Screenplay.from_dict(data["screenplay"])

        # Parse timestamps
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        return cls(**data)
