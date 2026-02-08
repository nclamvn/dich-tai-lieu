"""
Pydantic models for the API.

Extracted from api/main.py — request/response models shared across route modules.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from core.job_queue import JobPriority


class JobCreate(BaseModel):
    """Request model for creating a job"""
    job_name: str = Field(..., description="Human-readable job name")
    input_file: str = Field(..., description="Path to input file")
    output_file: str = Field(..., description="Path to output file")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="vi", description="Target language code")
    priority: int = Field(default=JobPriority.NORMAL, description="Job priority (1-50)")
    provider: str = Field(default="openai", description="AI provider")
    model: str = Field(default="gpt-4o-mini", description="Model name")
    use_smart_tables: bool = Field(default=False, description="Enable Premium Vision Table Reconstruction")
    domain: Optional[str] = Field(default=None, description="Domain (general/stem/finance/literature/medical/technology). Use 'stem' for STEM documents with formulas/code.")
    glossary: Optional[str] = Field(default=None, description="Glossary name")
    concurrency: int = Field(default=5, description="Parallel chunks")
    chunk_size: int = Field(default=3000, description="Chunk size in characters")
    output_format: str = Field(default="txt", description="Output format (txt/docx/pdf/html/md)")
    # Phase 3: Advanced STEM features
    input_type: str = Field(default="native_pdf", description="Input type: native_pdf, scanned_pdf, handwritten_pdf")
    output_mode: str = Field(default="docx_reflow", description="Output mode: pdf_preserve (keep layout), docx_reflow (clean single-column)")
    enable_ocr: bool = Field(default=False, description="Enable OCR for scanned/handwritten documents")
    ocr_mode: str = Field(default="auto", description="OCR mode: auto, paddle, hybrid, mathpix, none")
    enable_quality_check: bool = Field(default=False, description="Enable translation quality validation")
    enable_chemical_formulas: bool = Field(default=True, description="Enable chemical formula detection (STEM mode only)")
    layout_mode: str = Field(default="simple", description="DOCX layout mode: 'simple' (clean reflow) or 'academic' (semantic structure with theorem blocks, proofs, etc.) - Phase 2.0.1")
    equation_rendering_mode: str = Field(default="latex_text", description="Equation rendering mode for academic layout: 'latex_text' (plain text LaTeX) or 'omml' (Word native math format, requires pandoc) - Phase 2.0.3b")

    # UI v1.1: New parameters for enhanced UI
    ui_layout_mode: Optional[str] = Field(default=None, description="UI v1.1 Layout mode: 'basic', 'professional', or 'academic'. Overrides layout_mode and use_ast_pipeline if provided.")
    output_formats: Optional[List[str]] = Field(default=None, description="UI v1.1: List of output formats ['docx', 'pdf']. If not provided, uses output_format field.")
    advanced_options: Optional[Dict[str, Any]] = Field(default=None, description="UI v1.1: Advanced options {chunk_size, concurrency, cache_enabled, quality_validation, enable_book_layout}")

    # MathPix credentials (optional per-job overrides, uses server .env defaults if not provided)
    mathpix_app_id: Optional[str] = Field(default=None, description="MathPix App ID (optional, overrides server default)")
    mathpix_app_key: Optional[str] = Field(default=None, description="MathPix App Key (optional, overrides server default)")

    # Image Embedding (Phase 2026-01)
    cover_image: Optional[str] = Field(default=None, description="Cover image as base64 string or data URI. Will be placed as Page 1 before title page.")
    include_images: bool = Field(default=True, description="Extract and embed images from source PDF into output document")

    # Translation Engine (Phase 2026-01)
    engine: str = Field(default="auto", description="Translation engine: 'auto', 'translategemma_4b', 'cloud_api_auto'")

    # Vision Layout (Phase 2026-02)
    use_vision: bool = Field(default=True, description="Use Claude/OpenAI Vision API for layout-preserving PDF translation. Recommended for documents with tables, formulas, or complex layouts.")

    # User API Keys (Phase 2026-02)
    api_key: Optional[str] = Field(default=None, description="User's API key (OpenAI or Anthropic). Overrides server config.")


class JobUpdate(BaseModel):
    """Request model for updating a job"""
    status: Optional[str] = None
    priority: Optional[int] = None


class JobResponse(BaseModel):
    """Response model for job data"""
    job_id: str
    job_name: str
    status: str
    priority: int
    progress: float
    source_lang: str
    target_lang: str
    domain: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    quality_score: float
    total_cost_usd: float
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class QueueStats(BaseModel):
    """Queue statistics"""
    total: int
    pending: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int


class SystemInfo(BaseModel):
    """System information"""
    version: str
    uptime_seconds: float
    processor_running: bool
    current_jobs: int
    queue_stats: QueueStats


class AnalyzeRequest(BaseModel):
    """Request model for file analysis"""
    file_path: str = Field(..., description="Server path to uploaded file")


class AnalyzeResponse(BaseModel):
    """Response model for file analysis"""
    word_count: int = Field(..., description="Actual word count from extracted text")
    character_count: int = Field(..., description="Character count")
    detected_language: str = Field(..., description="Detected language (Tiếng Anh/Tiếng Việt/Trung/Nhật)")
    chunks_estimate: int = Field(..., description="Estimated number of 3000-word chunks")


class ProgressStep(BaseModel):
    """Individual processing step"""
    name: str = Field(..., description="Step identifier (upload, ocr, translation, etc.)")
    display_name: str = Field(..., description="Vietnamese display name")
    status: str = Field(..., description="Step status: pending, in_progress, completed, failed")
    progress: Optional[float] = Field(None, description="Step progress (0.0-1.0) for in_progress steps")
    duration: Optional[float] = Field(None, description="Duration in seconds for completed steps")


class JobProgressResponse(BaseModel):
    """Detailed job progress with step-by-step breakdown (UI v1.1)"""
    job_id: str
    job_name: str
    status: str
    current_step: int = Field(..., description="Current step number (1-indexed)")
    total_steps: int = Field(..., description="Total number of steps")
    progress_percent: int = Field(..., description="Overall progress percentage (0-100)")
    steps: List[ProgressStep]
    elapsed_seconds: float = Field(..., description="Time elapsed since job started")
    estimated_remaining_seconds: Optional[float] = Field(None, description="Estimated time remaining")
    output_file: Optional[str] = Field(None, description="Output file path when completed")


class LoginRequest(BaseModel):
    """Simple login request - for development/internal use"""
    username: str = Field(default="user", description="Username (optional for internal)")
    organization: str = Field(default="Default Organization", description="Organization name")
