# ═══════════════════════════════════════════════════════════════════
# FILE: api/book_writer_models.py
# PURPOSE: Enhanced Pydantic models — 3 modes, 7-agent pipeline,
#          chapter-level tracking, WebSocket events
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ─────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────

class InputMode(str, Enum):
    """4 input modes for the book writer."""
    SEEDS = "seeds"          # Vài ý tưởng → AI generate ~95%
    MESSY_DRAFT = "messy_draft"  # Bản thảo lộn xộn → restructure + expand
    ENRICH = "enrich"        # Bản thảo ok → thêm depth, ví dụ, data
    CONTINUE_DRAFT = "continue_draft"  # Upload draft → AI continues writing


class BookStatus(str, Enum):
    """Pipeline status — matches 7-agent flow."""
    CREATED = "created"
    ANALYZING = "analyzing"          # Agent 1: Analyst
    ANALYSIS_READY = "analysis_ready"
    ARCHITECTING = "architecting"    # Agent 2: Architect
    OUTLINING = "outlining"          # Agent 3: Outliner
    OUTLINE_READY = "outline_ready"  # Checkpoint: user reviews
    WRITING = "writing"              # Agent 4: Writer (N calls)
    ENRICHING = "enriching"          # Agent 5: Enricher
    EDITING = "editing"              # Agent 6: Editor
    COMPILING = "compiling"          # Agent 7: Publisher
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"                # User paused pipeline


class ChapterStatus(str, Enum):
    """Per-chapter tracking."""
    PENDING = "pending"
    WRITING = "writing"
    WRITTEN = "written"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    EDITING = "editing"
    EDITED = "edited"
    USER_EDITED = "user_edited"      # User manually edited
    REGENERATING = "regenerating"    # User requested rewrite


class Genre(str, Enum):
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    SELF_HELP = "self_help"
    TECHNICAL = "technical"
    ACADEMIC = "academic"
    MEMOIR = "memoir"
    BUSINESS = "business"
    CHILDREN = "children"
    POETRY = "poetry"
    OTHER = "other"


class OutputFormat(str, Enum):
    DOCX = "docx"
    EPUB = "epub"
    PDF = "pdf"
    MARKDOWN = "markdown"
    TXT = "txt"


# ─────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────

class CreateBookRequest(BaseModel):
    """Create a new book project."""
    title: Optional[str] = None
    input_mode: InputMode = InputMode.SEEDS

    # Content input (one of these)
    ideas: Optional[str] = None            # Mode A: text ideas
    draft_content: Optional[str] = None    # Mode B/C: pasted draft
    draft_file_id: Optional[str] = None    # Mode B/C: uploaded file job_id

    # User preferences
    language: str = "vi"                    # Output language
    target_pages: int = 200                 # Approximate page target
    genre: Optional[Genre] = None           # Auto-detect if None
    tone: Optional[str] = None              # e.g. "conversational", "academic"
    model: str = "claude-opus-4-6"          # AI model for writing
    output_formats: list[OutputFormat] = Field(default_factory=lambda: [OutputFormat.DOCX])

    # Advanced
    custom_instructions: Optional[str] = None  # Extra writing instructions
    reference_style: Optional[str] = None      # "Write like [author]"


class AnalysisReport(BaseModel):
    """Agent 1 output — analysis of user input."""
    input_mode: InputMode
    genre: Genre
    detected_language: str
    target_audience: str
    core_thesis: str
    tone: str
    strengths: list[str] = []
    gaps: list[str] = []
    estimated_chapters: int
    estimated_words: int
    key_themes: list[str] = []
    voice_profile: str
    recommendations: list[str] = []


class ChapterBlueprint(BaseModel):
    """Single chapter in the blueprint."""
    chapter_number: int
    title: str
    purpose: str
    key_points: list[str] = []
    word_target: int = 5000
    connects_to: list[int] = []          # Related chapter numbers
    emotional_tone: str = ""
    source_content: Optional[str] = None  # Mapped user draft content


class CharacterSheet(BaseModel):
    """Fiction character tracking."""
    name: str
    description: str
    motivation: str = ""
    arc: str = ""
    relationships: dict[str, str] = {}    # name → relationship
    voice_notes: str = ""                  # How they speak


class TermSheet(BaseModel):
    """Non-fiction term tracking."""
    term: str
    definition: str
    first_chapter: int = 1


class BookBlueprint(BaseModel):
    """Agent 2 output — book architecture."""
    title: str
    subtitle: Optional[str] = None
    title_alternatives: list[str] = []
    total_words: int
    total_chapters: int

    # Structure
    chapters: list[ChapterBlueprint] = []
    narrative_arc: Optional[dict[str, Any]] = None  # Fiction
    argument_arc: Optional[dict[str, Any]] = None   # Non-fiction

    # Tracking sheets
    characters: list[CharacterSheet] = []
    terms: list[TermSheet] = []


class ChapterOutlineSection(BaseModel):
    """Detailed section within chapter outline."""
    section_id: str              # "ch3.s5"
    title: str
    content_brief: str           # What to write
    word_target: int = 500
    includes: list[str] = []     # ["example", "data", "anecdote"]
    source_material: Optional[str] = None  # From user draft
    is_from_user: bool = False   # [FROM_USER] vs [AI_EXPAND]


class ChapterOutline(BaseModel):
    """Agent 3 output — detailed chapter outline."""
    chapter_number: int
    title: str
    summary: str
    word_target: int
    opening_hook: str = ""
    closing_hook: str = ""
    sections: list[ChapterOutlineSection] = []
    transition_from_previous: str = ""
    transition_to_next: str = ""


class ChapterResult(BaseModel):
    """Output for a single written chapter."""
    chapter_number: int
    title: str
    status: ChapterStatus = ChapterStatus.PENDING
    content: str = ""                     # Full chapter text
    enriched_content: Optional[str] = None
    edited_content: Optional[str] = None
    final_content: Optional[str] = None   # Best available version
    summary: str = ""                     # For context chain
    word_count: int = 0

    # Tracking
    writing_model: str = ""
    writing_tokens_in: int = 0
    writing_tokens_out: int = 0
    enrichment_additions: int = 0         # Words added by enricher
    edit_changes: list[str] = []          # Editor change notes
    user_edits: Optional[str] = None      # User's manual edits


class PipelineProgress(BaseModel):
    """Real-time progress tracking."""
    status: BookStatus
    current_agent: str = ""               # "writer", "enricher", etc.
    current_chapter: int = 0
    total_chapters: int = 0
    chapters_written: int = 0
    chapters_enriched: int = 0
    chapters_edited: int = 0
    total_words: int = 0
    elapsed_seconds: float = 0
    estimated_remaining_seconds: float = 0

    # Cost tracking
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    estimated_cost_usd: float = 0


class BookProject(BaseModel):
    """Full book project — stored in DB."""
    id: str
    created_at: datetime
    updated_at: datetime

    # Input
    request: CreateBookRequest

    # Pipeline state
    status: BookStatus = BookStatus.CREATED
    progress: PipelineProgress = Field(default_factory=lambda: PipelineProgress(status=BookStatus.CREATED))

    # Agent outputs
    analysis: Optional[AnalysisReport] = None
    blueprint: Optional[BookBlueprint] = None
    outlines: list[ChapterOutline] = []
    chapters: list[ChapterResult] = []

    # Output files
    output_files: list[dict[str, str]] = []   # [{"format": "docx", "path": "...", "filename": "..."}]

    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0


class BookProjectResponse(BaseModel):
    """API response — subset of BookProject."""
    id: str
    created_at: datetime
    updated_at: datetime
    title: Optional[str] = None
    status: BookStatus
    input_mode: InputMode
    progress: PipelineProgress

    # Included based on status
    analysis: Optional[AnalysisReport] = None
    blueprint: Optional[BookBlueprint] = None
    outlines: list[ChapterOutline] = []
    chapters: list[ChapterResult] = []
    chapter_count: int = 0
    total_words: int = 0
    output_files: list[dict[str, str]] = []
    error: Optional[str] = None


class BookListItem(BaseModel):
    """Lightweight list item."""
    id: str
    title: Optional[str] = None
    status: BookStatus
    input_mode: InputMode
    created_at: datetime
    updated_at: datetime
    chapter_count: int = 0
    total_words: int = 0


# ─────────────────────────────────────────────────────────────────
# CHAPTER MANAGEMENT REQUESTS
# ─────────────────────────────────────────────────────────────────

class ApproveOutlineRequest(BaseModel):
    """User approves/adjusts outline before writing."""
    approved: bool = True
    chapter_adjustments: Optional[dict[int, dict[str, Any]]] = None
    # e.g. {3: {"title": "New Title", "word_target": 8000}}
    custom_notes: Optional[str] = None


class RegenerateChapterRequest(BaseModel):
    """Request to rewrite a specific chapter."""
    chapter_number: int
    instructions: Optional[str] = None  # Additional instructions
    preserve_outline: bool = True


class EditChapterRequest(BaseModel):
    """User submits manual edits to a chapter."""
    chapter_number: int
    content: str


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET EVENTS
# ─────────────────────────────────────────────────────────────────

class WSEventType(str, Enum):
    STATUS_CHANGE = "status_change"
    CHAPTER_PROGRESS = "chapter_progress"
    CHAPTER_COMPLETE = "chapter_complete"
    PIPELINE_COMPLETE = "pipeline_complete"
    ERROR = "error"
    COST_UPDATE = "cost_update"


class WSEvent(BaseModel):
    """WebSocket event payload."""
    event: WSEventType
    book_id: str
    data: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
