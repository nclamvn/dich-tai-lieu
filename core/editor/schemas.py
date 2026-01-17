from typing import List, Optional, Any
from pydantic import BaseModel

class SegmentResponse(BaseModel):
    """A single translation segment (chunk) for editing."""
    chunk_id: str
    index: int  # Ordering index
    source: str
    translated: str
    quality_score: float = 0.0
    is_edited: bool = False
    warnings: List[str] = []

class EditorJobResponse(BaseModel):
    """Full job data for the editor."""
    job_id: str
    segments: List[SegmentResponse]
    completion_percentage: float
    can_export: bool

class UpdateSegmentRequest(BaseModel):
    """Request to update a segment."""
    translated_text: str
