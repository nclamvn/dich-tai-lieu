"""Pydantic schemas for Integration Bridge API"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    TRANSLATING = "translating"
    FORMATTING = "formatting"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enum"""
    TRANSLATION = "translation"
    EXPORT = "export"


# ============ Translation Models ============

class TranslationOptions(BaseModel):
    """Options for translation"""
    provider: str = "auto"  # auto, openai, anthropic, deepseek
    preserve_formatting: bool = True
    glossary: Optional[Dict[str, str]] = None
    tone: Optional[str] = None  # formal, casual, literary


class TranslationRequest(BaseModel):
    """Request to translate a CW draft"""
    cw_project_id: str = Field(..., description="Companion Writer project ID")
    cw_draft_id: str = Field(..., description="Companion Writer draft ID")
    content: str = Field(..., description="Content to translate")
    source_lang: str = Field(default="vi", description="Source language code")
    target_lang: str = Field(default="en", description="Target language code")
    options: Optional[TranslationOptions] = None
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion")


class TranslationResponse(BaseModel):
    """Response after queuing translation"""
    job_id: str
    bridge_job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Translation job queued"
    tracking_url: str


class TranslationResult(BaseModel):
    """Result of completed translation"""
    translated_content: str
    original_word_count: int
    translated_word_count: int
    provider_used: str
    model_used: str
    token_count: int
    cost: float
    duration_seconds: float


# ============ Export Models ============

class ExportFormat(str, Enum):
    """Export format enum"""
    PDF = "pdf"
    DOCX = "docx"
    EPUB = "epub"
    MD = "md"
    TXT = "txt"


class ExportTemplate(str, Enum):
    """Export template enum"""
    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    EBOOK = "ebook"
    MINIMAL = "minimal"


class ExportOptions(BaseModel):
    """Options for export"""
    include_toc: bool = True
    include_cover: bool = False
    font_family: str = "Times New Roman"
    font_size: int = 12
    page_size: str = "a4"  # a4, letter, a5
    margins: Optional[Dict[str, float]] = None  # top, right, bottom, left in inches
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    cover_image_url: Optional[str] = None


class ExportRequest(BaseModel):
    """Request to export document"""
    source_system: str = Field(..., description="Source system: 'cw' or 'app'")
    project_id: str = Field(..., description="Project/document ID from source system")
    content: Optional[str] = Field(None, description="Content to export (if not fetching from source)")
    title: str = Field(default="Untitled", description="Document title")
    author: Optional[str] = None
    formats: List[ExportFormat] = Field(default=[ExportFormat.PDF])
    template: ExportTemplate = ExportTemplate.PROFESSIONAL
    options: Optional[ExportOptions] = None
    callback_url: Optional[str] = None


class ExportResponse(BaseModel):
    """Response after queuing export"""
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Export job queued"
    tracking_url: str


class ExportFile(BaseModel):
    """Exported file info"""
    format: ExportFormat
    filename: str
    download_url: str
    size_bytes: int


class ExportResult(BaseModel):
    """Result of completed export"""
    files: List[ExportFile]
    total_pages: Optional[int] = None
    duration_seconds: float


# ============ Job Models ============

class BridgeJob(BaseModel):
    """Unified job model"""
    job_id: str
    job_type: JobType
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)

    # Source info
    cw_project_id: Optional[str] = None
    cw_draft_id: Optional[str] = None
    app_job_id: Optional[str] = None

    # Results
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobStatusResponse(BaseModel):
    """Response for job status query"""
    job_id: str
    job_type: JobType
    status: JobStatus
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ============ Webhook Models ============

class WebhookEvent(str, Enum):
    """Webhook event types"""
    TRANSLATION_STARTED = "translation.started"
    TRANSLATION_PROGRESS = "translation.progress"
    TRANSLATION_COMPLETED = "translation.completed"
    TRANSLATION_FAILED = "translation.failed"
    EXPORT_STARTED = "export.started"
    EXPORT_PROGRESS = "export.progress"
    EXPORT_COMPLETED = "export.completed"
    EXPORT_FAILED = "export.failed"


class WebhookPayload(BaseModel):
    """Webhook payload"""
    event: WebhookEvent
    job_id: str
    job_type: JobType
    timestamp: datetime
    data: Dict[str, Any]


class APPWebhookPayload(BaseModel):
    """Webhook from AI Publisher Pro"""
    app_job_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============ Health Models ============

class ServiceHealth(BaseModel):
    """Health status of a service"""
    name: str
    status: str  # healthy, unhealthy, unknown
    url: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall health response"""
    status: str  # healthy, degraded, unhealthy
    version: str
    services: List[ServiceHealth]
    timestamp: datetime
