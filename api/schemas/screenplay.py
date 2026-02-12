"""
Pydantic Schemas for Screenplay Studio API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class ProjectTierEnum(str, Enum):
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"
    DIRECTOR = "director"


class VideoProviderEnum(str, Enum):
    PIKA = "pika"
    RUNWAY = "runway"
    VEO = "veo"


class LanguageEnum(str, Enum):
    EN = "en"
    VI = "vi"


class ProjectStatusEnum(str, Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    WRITING = "writing"
    VISUALIZING = "visualizing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateProjectRequest(BaseModel):
    """Request to create a new screenplay project"""
    title: str = Field(..., min_length=1, max_length=200)
    source_text: str = Field(..., min_length=100)
    source_type: str = Field(default="novel")
    language: LanguageEnum = Field(default=LanguageEnum.EN)
    tier: ProjectTierEnum = Field(default=ProjectTierEnum.FREE)
    video_provider: Optional[VideoProviderEnum] = None


class UpdateProjectRequest(BaseModel):
    """Request to update project settings"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    tier: Optional[ProjectTierEnum] = None
    video_provider: Optional[VideoProviderEnum] = None


class EstimateCostRequest(BaseModel):
    """Request to estimate project cost"""
    source_text_length: int = Field(..., gt=0)
    tier: ProjectTierEnum
    video_provider: Optional[VideoProviderEnum] = None
    target_runtime_minutes: int = Field(default=90, ge=5, le=180)


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class CharacterResponse(BaseModel):
    """Character in story analysis"""
    name: str
    description: str
    role: str
    arc: str
    traits: List[str] = []
    visual_description: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None


class StoryAnalysisResponse(BaseModel):
    """Story analysis response"""
    title: str
    logline: str
    synopsis: str
    genre: str
    sub_genres: List[str] = []
    tone: str
    themes: List[str] = []
    setting: str
    time_period: str
    characters: List[CharacterResponse] = []
    estimated_runtime_minutes: int
    estimated_scenes: int


class SceneResponse(BaseModel):
    """Scene in screenplay"""
    scene_number: int
    heading: str
    summary: str
    characters_present: List[str] = []
    emotional_beat: str
    page_count: float
    mood: Optional[str] = None


class ScreenplayResponse(BaseModel):
    """Screenplay response"""
    title: str
    author: str
    genre: str
    logline: str
    total_pages: float
    total_runtime_minutes: int
    scenes: List[SceneResponse] = []


class ProjectResponse(BaseModel):
    """Full project response"""
    id: str
    title: str
    source_type: str
    language: LanguageEnum
    tier: ProjectTierEnum
    video_provider: Optional[VideoProviderEnum]
    status: ProjectStatusEnum
    current_phase: int
    progress_percent: float
    error_message: Optional[str]
    story_analysis: Optional[StoryAnalysisResponse]
    screenplay: Optional[ScreenplayResponse]
    estimated_cost_usd: float
    actual_cost_usd: float
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    output_files: Dict[str, str] = {}


class ProjectListResponse(BaseModel):
    """List of projects response"""
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int


class CostEstimateResponse(BaseModel):
    """Cost estimate response"""
    tier: ProjectTierEnum
    estimated_scenes: int
    estimated_runtime_minutes: int
    costs: Dict[str, float]
    features: Dict[str, bool]


class ProgressResponse(BaseModel):
    """Progress update response"""
    project_id: str
    status: ProjectStatusEnum
    current_phase: int
    progress_percent: float
    message: str
