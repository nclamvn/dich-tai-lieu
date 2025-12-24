"""
APS V2 API Models

Pydantic models for the Claude-Native Universal Publishing API.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class JobStatusV2(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    RUNNING = "running"
    VISION_READING = "vision_reading"
    EXTRACTING_DNA = "extracting_dna"
    CHUNKING = "chunking"
    TRANSLATING = "translating"
    ASSEMBLING = "assembling"
    CONVERTING = "converting"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormatV2(str, Enum):
    """Supported output formats"""
    DOCX = "docx"
    PDF = "pdf"
    EPUB = "epub"
    HTML = "html"
    MARKDOWN = "md"
    LATEX = "latex"


# ==================== REQUEST MODELS ====================

class PublishRequest(BaseModel):
    """Request to start a publishing job"""
    source_language: str = Field(default="en", description="Source language code")
    target_language: str = Field(default="vi", description="Target language code")
    profile_id: str = Field(default="novel", description="Publishing profile ID")
    output_formats: List[str] = Field(
        default=["docx"],
        description="Output formats to generate"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_language": "en",
                "target_language": "vi",
                "profile_id": "novel",
                "output_formats": ["docx", "pdf", "epub"]
            }
        }


class PublishTextRequest(BaseModel):
    """Request to publish text directly (no file upload)"""
    content: str = Field(..., description="Document content to publish")
    source_language: str = Field(default="en")
    target_language: str = Field(default="vi")
    profile_id: str = Field(default="novel")
    output_formats: List[str] = Field(default=["docx"])
    filename: str = Field(default="document", description="Base filename for outputs")


# ==================== RESPONSE MODELS ====================

class DocumentDNAResponse(BaseModel):
    """Document DNA information"""
    document_id: str = ""
    title: str = ""
    author: str = ""
    language: str = ""
    genre: str = ""
    sub_genre: str = ""
    tone: str = ""
    voice: str = ""
    reading_level: str = ""
    has_chapters: bool = False
    has_sections: bool = False
    has_footnotes: bool = False
    has_citations: bool = False
    has_formulas: bool = False
    has_code: bool = False
    has_tables: bool = False
    characters: List[str] = []
    locations: List[str] = []
    key_terms: List[str] = []
    proper_nouns: List[str] = []
    word_count: int = 0


class ChunkInfoV2(BaseModel):
    """Information about a document chunk"""
    index: int
    chunk_type: str
    title: Optional[str] = None
    word_count: int


class UsageStatsResponse(BaseModel):
    """Token and time usage statistics"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_elapsed_seconds: float = 0.0
    total_calls: int = 0
    estimated_cost_usd: float = 0.0
    calls_by_provider: Dict[str, int] = {}


class JobResponseV2(BaseModel):
    """Response for job status"""
    job_id: str
    status: JobStatusV2
    progress: float = Field(ge=0, le=100)
    current_stage: str = ""
    error: Optional[str] = None

    # Document info
    source_file: str
    source_language: str
    target_language: str
    profile_id: str
    output_formats: List[str]

    # Results (when available)
    dna: Optional[DocumentDNAResponse] = None
    chunks_count: int = 0
    output_paths: Dict[str, str] = {}

    # Verification (when available)
    quality_score: Optional[float] = None
    quality_level: Optional[str] = None

    # Usage statistics
    usage_stats: Optional[UsageStatsResponse] = None
    elapsed_time_seconds: float = 0.0

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc12345",
                "status": "translating",
                "progress": 45.5,
                "current_stage": "Translating chunk 3/5",
                "source_file": "my_novel.docx",
                "source_language": "en",
                "target_language": "vi",
                "profile_id": "novel",
                "output_formats": ["docx", "pdf"],
                "chunks_count": 5,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class PublishingProfileResponse(BaseModel):
    """Publishing profile information"""
    id: str
    name: str
    description: str
    output_format: str
    style_guide: str
    special_instructions: str = ""


class ProfileListResponse(BaseModel):
    """List of available profiles"""
    profiles: List[PublishingProfileResponse]
    total: int


class HealthResponseV2(BaseModel):
    """Health check response"""
    status: str
    version: str
    dependencies: Dict[str, bool]


class ErrorResponseV2(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    job_id: Optional[str] = None
