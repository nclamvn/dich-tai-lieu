"""
Book Writer v2.0 API Schemas

Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class BookGenre(str, Enum):
    NON_FICTION = "non-fiction"
    FICTION = "fiction"
    TECHNICAL = "technical"
    BUSINESS = "business"
    SELF_HELP = "self-help"
    ACADEMIC = "academic"
    MEMOIR = "memoir"
    GUIDE = "guide"


class OutputFormat(str, Enum):
    DOCX = "docx"
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"


# === REQUEST SCHEMAS ===

class BookCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Book title")
    description: str = Field(..., min_length=10, max_length=5000, description="Book description/topic")
    target_pages: int = Field(100, ge=50, le=1000, description="Target number of pages")

    subtitle: Optional[str] = Field(None, max_length=300)
    genre: BookGenre = Field(BookGenre.NON_FICTION)
    audience: Optional[str] = Field(None, max_length=500)

    author_name: Optional[str] = Field("AI Publisher Pro")
    language: str = Field("en")

    output_formats: List[OutputFormat] = Field(
        default=[OutputFormat.DOCX, OutputFormat.MARKDOWN],
    )

    words_per_page: int = Field(300, ge=200, le=500)
    sections_per_chapter: int = Field(4, ge=3, le=6)

    # Continue from draft
    continue_from_draft: bool = Field(False, description="Continue writing from an uploaded draft")
    draft_file_id: Optional[str] = Field(None, description="File ID from upload-draft endpoint")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "AI in Healthcare",
                "description": "A comprehensive guide to artificial intelligence applications in modern healthcare.",
                "target_pages": 300,
                "genre": "technical",
                "audience": "Healthcare professionals and technology enthusiasts",
            }
        }


# === RESPONSE SCHEMAS ===

class WordCountInfo(BaseModel):
    target: int
    actual: int
    completion: float
    remaining: int
    is_complete: bool


class SectionResponse(BaseModel):
    id: str
    number: int
    title: str
    chapter_id: str
    word_count: WordCountInfo
    status: str
    content_preview: Optional[str] = None
    expansion_attempts: int = 0


class ChapterResponse(BaseModel):
    id: str
    number: int
    title: str
    part_id: str
    word_count: WordCountInfo
    sections: List[SectionResponse]
    is_complete: bool
    progress: float
    introduction_preview: Optional[str] = None
    summary_preview: Optional[str] = None
    key_takeaways: List[str] = []


class PartResponse(BaseModel):
    id: str
    number: int
    title: str
    word_count: WordCountInfo
    chapters: List[ChapterResponse]
    is_complete: bool
    progress: float


class BlueprintResponse(BaseModel):
    title: str
    subtitle: Optional[str] = None
    author: str
    genre: str
    language: str
    target_pages: int
    actual_pages: int
    target_words: int
    actual_words: int
    completion: float
    parts: List[PartResponse]
    total_chapters: int
    total_sections: int


class BookProjectResponse(BaseModel):
    id: str
    status: str
    current_agent: str = ""
    current_task: str = ""
    sections_completed: int = 0
    sections_total: int = 0
    progress_percentage: float = 0
    word_progress: float = 0
    expansion_rounds: int = 0
    blueprint: Optional[BlueprintResponse] = None
    output_files: Dict[str, str] = {}
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = []


class BookListResponse(BaseModel):
    items: List[BookProjectResponse]
    total: int
    page: int
    page_size: int


class StructurePreviewResponse(BaseModel):
    target_pages: int
    content_pages: int
    content_words: int
    num_parts: int
    total_chapters: int
    chapters_per_part: int
    total_sections: int
    words_per_chapter: int
    words_per_section: int
    estimated_time_minutes: int


class BookContentResponse(BaseModel):
    title: str
    subtitle: Optional[str] = None
    author: str
    parts: List[Dict[str, Any]]
    word_count: int
    page_count: int


class DraftChapterInfo(BaseModel):
    chapter_number: int
    title: str
    word_count: int


class DraftAnalysisResponse(BaseModel):
    file_id: str
    filename: str
    total_chapters: int
    total_words: int
    chapters: List[DraftChapterInfo]
