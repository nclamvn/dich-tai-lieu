"""
Glossary Pydantic Schemas
API validation schemas for glossary operations.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ==================== CONSTANTS ====================

DOMAINS = [
    "general",
    "medical",
    "legal",
    "tech",
    "finance",
    "academic",
    "literary",
    "business",
    "scientific",
]

PARTS_OF_SPEECH = [
    "noun",
    "verb",
    "adjective",
    "adverb",
    "phrase",
    "abbreviation",
    "proper_noun",
]

LANGUAGES = [
    ("en", "English"),
    ("vi", "Vietnamese"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("ru", "Russian"),
    ("pt", "Portuguese"),
]


# ==================== GLOSSARY SCHEMAS ====================

class GlossaryBase(BaseModel):
    """Base schema for Glossary."""
    name: str = Field(..., min_length=1, max_length=255, description="Glossary name")
    description: Optional[str] = Field(None, description="Optional description")
    domain: str = Field(default="general", description="Domain type")
    source_language: str = Field(default="en", max_length=10, description="Source language code")
    target_language: str = Field(default="vi", max_length=10, description="Target language code")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v not in DOMAINS:
            raise ValueError(f"Domain must be one of: {DOMAINS}")
        return v


class GlossaryCreate(GlossaryBase):
    """Schema for creating a new Glossary."""
    pass


class GlossaryUpdate(BaseModel):
    """Schema for updating a Glossary (partial update)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v is not None and v not in DOMAINS:
            raise ValueError(f"Domain must be one of: {DOMAINS}")
        return v


class GlossaryResponse(GlossaryBase):
    """Schema for Glossary API response."""
    id: str
    is_prebuilt: bool
    term_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GlossaryListResponse(BaseModel):
    """Schema for list of glossaries response."""
    glossaries: List[GlossaryResponse]
    total: int


# ==================== TERM SCHEMAS ====================

class TermBase(BaseModel):
    """Base schema for Term."""
    source_term: str = Field(..., min_length=1, max_length=500, description="Source term")
    target_term: str = Field(..., min_length=1, max_length=1000, description="Target term")
    context: Optional[str] = Field(None, description="Usage context")
    part_of_speech: Optional[str] = Field(None, description="Part of speech")
    case_sensitive: bool = Field(default=False, description="Case sensitive matching")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")

    @field_validator("part_of_speech")
    @classmethod
    def validate_pos(cls, v):
        if v is not None and v not in PARTS_OF_SPEECH:
            raise ValueError(f"part_of_speech must be one of: {PARTS_OF_SPEECH}")
        return v


class TermCreate(TermBase):
    """Schema for creating a new Term."""
    pass


class TermUpdate(BaseModel):
    """Schema for updating a Term (partial update)."""
    source_term: Optional[str] = Field(None, min_length=1, max_length=500)
    target_term: Optional[str] = Field(None, min_length=1, max_length=1000)
    context: Optional[str] = None
    part_of_speech: Optional[str] = None
    case_sensitive: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)

    @field_validator("part_of_speech")
    @classmethod
    def validate_pos(cls, v):
        if v is not None and v not in PARTS_OF_SPEECH:
            raise ValueError(f"part_of_speech must be one of: {PARTS_OF_SPEECH}")
        return v


class TermResponse(TermBase):
    """Schema for Term API response."""
    id: str
    glossary_id: str
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TermListResponse(BaseModel):
    """Schema for paginated term list response."""
    terms: List[TermResponse]
    total: int
    page: int
    limit: int
    pages: int


# ==================== BULK OPERATIONS ====================

class BulkTermCreate(BaseModel):
    """Schema for bulk term creation."""
    terms: List[TermCreate] = Field(..., min_length=1, max_length=1000)
    skip_duplicates: bool = Field(default=True, description="Skip existing terms")


class BulkTermDelete(BaseModel):
    """Schema for bulk term deletion."""
    term_ids: List[str] = Field(..., min_length=1)


class BulkTermResult(BaseModel):
    """Result of bulk term operation."""
    added: int
    skipped: int
    errors: List[dict]


# ==================== IMPORT/EXPORT ====================

class ImportResult(BaseModel):
    """Result of import operation."""
    status: str  # completed, partial, failed
    added: int
    updated: int
    skipped: int
    errors: List[dict]


# ==================== MATCHING ====================

class MatchRequest(BaseModel):
    """Request to find matching terms in text."""
    glossary_ids: List[str] = Field(..., min_length=1, description="Glossary IDs to search")
    text: str = Field(..., min_length=1, description="Text to search for terms")
    highlight: bool = Field(default=False, description="Return highlighted text")


class TermMatch(BaseModel):
    """A matched term in text."""
    source_term: str
    target_term: str
    start: int
    end: int
    glossary_id: str
    priority: int


class MatchResponse(BaseModel):
    """Response with matched terms."""
    matches: List[TermMatch]
    highlighted_text: Optional[str] = None
    match_count: int
    unique_terms: int


# ==================== PRE-BUILT ====================

class PrebuiltGlossaryInfo(BaseModel):
    """Information about a pre-built glossary."""
    id: str
    name: str
    description: str
    domain: str
    term_count: int
    source_language: str
    target_language: str


class PrebuiltListResponse(BaseModel):
    """List of pre-built glossaries."""
    glossaries: List[PrebuiltGlossaryInfo]
