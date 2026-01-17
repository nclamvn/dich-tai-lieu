"""
Translation Memory Pydantic Schemas
API validation schemas for TM operations.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ==================== ENUMS ====================

class MatchType(str, Enum):
    EXACT = "exact"           # 100% match
    NEAR_EXACT = "near_exact" # 95-99% match
    FUZZY = "fuzzy"           # 75-94% match
    NO_MATCH = "no_match"     # <75% match


class SourceType(str, Enum):
    AI = "ai"           # Machine translated
    HUMAN = "human"     # Human translated
    VERIFIED = "verified"  # Human verified


# ==================== TM SCHEMAS ====================

class TMBase(BaseModel):
    """Base schema for Translation Memory."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_language: str = Field(default="en", max_length=10)
    target_language: str = Field(default="vi", max_length=10)
    domain: str = Field(default="general", max_length=50)


class TMCreate(TMBase):
    """Schema for creating a new TM."""
    pass


class TMUpdate(BaseModel):
    """Schema for updating a TM."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None


class TMResponse(TMBase):
    """Schema for TM API response."""
    id: str
    segment_count: int
    total_words: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TMListResponse(BaseModel):
    """Schema for list of TMs."""
    tms: List[TMResponse]
    total: int


# ==================== SEGMENT SCHEMAS ====================

class SegmentBase(BaseModel):
    """Base schema for TM Segment."""
    source_text: str = Field(..., min_length=1)
    target_text: str = Field(..., min_length=1)
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    source_type: SourceType = Field(default=SourceType.AI)
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    project_name: Optional[str] = None
    notes: Optional[str] = None


class SegmentCreate(SegmentBase):
    """Schema for creating a segment."""
    pass


class SegmentUpdate(BaseModel):
    """Schema for updating a segment."""
    target_text: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_type: Optional[SourceType] = None
    notes: Optional[str] = None


class SegmentResponse(SegmentBase):
    """Schema for segment API response."""
    id: str
    tm_id: str
    source_length: int
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SegmentListResponse(BaseModel):
    """Schema for paginated segment list."""
    segments: List[SegmentResponse]
    total: int
    page: int
    limit: int
    pages: int


# ==================== BULK OPERATIONS ====================

class BulkSegmentCreate(BaseModel):
    """Schema for bulk segment creation."""
    segments: List[SegmentCreate] = Field(..., min_length=1, max_length=5000)
    skip_duplicates: bool = Field(default=True)


class BulkSegmentResult(BaseModel):
    """Result of bulk segment operation."""
    added: int
    skipped: int
    errors: List[dict]


# ==================== MATCHING ====================

class TMMatch(BaseModel):
    """A single TM match result."""
    segment_id: str
    source_text: str
    target_text: str
    similarity: float  # 0.0 to 1.0
    match_type: MatchType
    quality_score: float
    source_type: SourceType
    tm_id: str
    tm_name: str


class LookupRequest(BaseModel):
    """Request to look up segments in TM."""
    tm_ids: List[str] = Field(..., min_length=1)
    source_text: str = Field(..., min_length=1)
    min_similarity: float = Field(default=0.75, ge=0.0, le=1.0)
    max_results: int = Field(default=5, ge=1, le=20)


class LookupResponse(BaseModel):
    """Response with TM matches."""
    matches: List[TMMatch]
    best_match: Optional[TMMatch] = None
    match_count: int


class ProcessRequest(BaseModel):
    """Request to process text through TM."""
    tm_ids: List[str] = Field(..., min_length=1)
    source_text: str = Field(..., min_length=1)
    segment_type: str = Field(default="sentence")  # sentence, paragraph
    min_similarity: float = Field(default=0.75)


class ProcessedSegment(BaseModel):
    """A processed segment with TM match info."""
    source_text: str
    target_text: Optional[str] = None  # From TM if matched
    match: Optional[TMMatch] = None
    needs_translation: bool
    estimated_cost_factor: float  # 0.0 (exact) to 1.0 (no match)


class ProcessResponse(BaseModel):
    """Response from TM processing."""
    segments: List[ProcessedSegment]
    total_segments: int
    matched_segments: int
    estimated_savings: float  # Percentage cost reduction


# ==================== IMPORT/EXPORT ====================

class ImportResult(BaseModel):
    """Result of import operation."""
    status: str
    added: int
    updated: int
    skipped: int
    errors: List[dict]


# ==================== STATS ====================

class TMStats(BaseModel):
    """TM usage statistics."""
    tm_id: str
    tm_name: str
    segment_count: int
    total_words: int
    total_lookups: int
    exact_matches: int
    fuzzy_matches: int
    hit_rate: float
    top_segments: List[SegmentResponse]
