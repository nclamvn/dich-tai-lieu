"""
Translation Memory Service
Business logic layer for TM operations.
"""
import logging
from typing import Optional, List, Tuple
from datetime import datetime

from .models import TranslationMemory, TMSegment
from .schemas import (
    TMCreate, TMUpdate, TMResponse, TMListResponse,
    SegmentCreate, SegmentUpdate, SegmentResponse, SegmentListResponse,
    BulkSegmentResult, LookupRequest, LookupResponse,
    ProcessRequest, ProcessResponse, ProcessedSegment,
    TMMatch, MatchType, SourceType,
)
from .repository import TMRepository, get_repository
from .matcher import TMMatcher, get_matcher, MatchResult
from .segmenter import Segmenter, get_segmenter, SegmentType

logger = logging.getLogger(__name__)


class TMService:
    """
    Service layer for Translation Memory operations.

    Handles business logic, matching, and processing.
    """

    def __init__(self):
        """Initialize service."""
        self.repository = get_repository()
        self.matcher = get_matcher()

    # ==================== TM OPERATIONS ====================

    async def create_tm(self, data: TMCreate) -> TMResponse:
        """Create a new Translation Memory."""
        tm = self.repository.create_tm(
            name=data.name,
            description=data.description,
            source_language=data.source_language,
            target_language=data.target_language,
            domain=data.domain,
        )
        return TMResponse.model_validate(tm.to_dict())

    async def get_tm(self, tm_id: str) -> Optional[TMResponse]:
        """Get TM by ID."""
        tm = self.repository.get_tm(tm_id)
        if tm:
            return TMResponse.model_validate(tm.to_dict())
        return None

    async def list_tms(
        self,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        domain: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[TMResponse]:
        """List TMs with filters."""
        tms = self.repository.list_tms(
            source_language=source_language,
            target_language=target_language,
            domain=domain,
            search=search,
        )
        return [TMResponse.model_validate(tm.to_dict()) for tm in tms]

    async def update_tm(
        self,
        tm_id: str,
        data: TMUpdate,
    ) -> Optional[TMResponse]:
        """Update TM metadata."""
        tm = self.repository.update_tm(
            tm_id=tm_id,
            name=data.name,
            description=data.description,
            domain=data.domain,
        )
        if tm:
            return TMResponse.model_validate(tm.to_dict())
        return None

    async def delete_tm(self, tm_id: str) -> bool:
        """Delete TM."""
        return self.repository.delete_tm(tm_id)

    # ==================== SEGMENT OPERATIONS ====================

    async def add_segment(
        self,
        tm_id: str,
        data: SegmentCreate,
    ) -> SegmentResponse:
        """Add a segment to TM."""
        # Check TM exists
        tm = self.repository.get_tm(tm_id)
        if not tm:
            raise ValueError("TM not found")

        segment = self.repository.add_segment(
            tm_id=tm_id,
            source_text=data.source_text,
            target_text=data.target_text,
            quality_score=data.quality_score,
            source_type=data.source_type.value,
            context_before=data.context_before,
            context_after=data.context_after,
            project_name=data.project_name,
            notes=data.notes,
        )

        if not segment:
            raise ValueError("Segment already exists in TM")

        return SegmentResponse.model_validate(segment.to_dict())

    async def add_segments_bulk(
        self,
        tm_id: str,
        segments: List[SegmentCreate],
        skip_duplicates: bool = True,
    ) -> BulkSegmentResult:
        """Add multiple segments to TM."""
        segment_data = [
            {
                "source_text": s.source_text,
                "target_text": s.target_text,
                "quality_score": s.quality_score,
                "source_type": s.source_type.value,
                "context_before": s.context_before,
                "context_after": s.context_after,
                "project_name": s.project_name,
                "notes": s.notes,
            }
            for s in segments
        ]

        added, skipped, errors = self.repository.add_segments_bulk(
            tm_id=tm_id,
            segments=segment_data,
            skip_duplicates=skip_duplicates,
        )

        return BulkSegmentResult(added=added, skipped=skipped, errors=errors)

    async def list_segments(
        self,
        tm_id: str,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> SegmentListResponse:
        """List segments with pagination."""
        segments, total = self.repository.list_segments(
            tm_id=tm_id,
            page=page,
            limit=limit,
            search=search,
            sort=sort,
            order=order,
        )

        pages = (total + limit - 1) // limit

        return SegmentListResponse(
            segments=[SegmentResponse.model_validate(s.to_dict()) for s in segments],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_segment(
        self,
        tm_id: str,
        segment_id: str,
    ) -> Optional[SegmentResponse]:
        """Get a specific segment."""
        segment = self.repository.get_segment(tm_id, segment_id)
        if segment:
            return SegmentResponse.model_validate(segment.to_dict())
        return None

    async def update_segment(
        self,
        tm_id: str,
        segment_id: str,
        data: SegmentUpdate,
    ) -> Optional[SegmentResponse]:
        """Update a segment."""
        update_data = {}
        if data.target_text is not None:
            update_data["target_text"] = data.target_text
        if data.quality_score is not None:
            update_data["quality_score"] = data.quality_score
        if data.source_type is not None:
            update_data["source_type"] = data.source_type.value
        if data.notes is not None:
            update_data["notes"] = data.notes

        segment = self.repository.update_segment(tm_id, segment_id, **update_data)

        if segment:
            return SegmentResponse.model_validate(segment.to_dict())
        return None

    async def delete_segment(self, tm_id: str, segment_id: str) -> bool:
        """Delete a segment."""
        return self.repository.delete_segment(tm_id, segment_id)

    # ==================== LOOKUP & MATCHING ====================

    async def lookup(self, request: LookupRequest) -> LookupResponse:
        """
        Look up source text in TMs.

        Returns matching segments sorted by similarity.
        """
        # Get all segments from specified TMs
        all_segments = []
        tm_names = {}

        for tm_id in request.tm_ids:
            tm = self.repository.get_tm(tm_id)
            if tm:
                tm_names[tm_id] = tm.name
                segments = self.repository.get_all_segments(tm_id)
                all_segments.extend(segments)

        if not all_segments:
            return LookupResponse(matches=[], best_match=None, match_count=0)

        # Find matches
        matches = self.matcher.find_fuzzy(
            request.source_text,
            all_segments,
            min_similarity=request.min_similarity,
            max_results=request.max_results,
        )

        # Convert to response
        tm_matches = [
            self._match_to_response(m, tm_names.get(m.segment.tm_id, "Unknown"))
            for m in matches
        ]

        # Update usage counts for matched segments
        if matches:
            segment_ids = [m.segment.id for m in matches]
            self.repository.increment_usage_count(segment_ids)

        return LookupResponse(
            matches=tm_matches,
            best_match=tm_matches[0] if tm_matches else None,
            match_count=len(tm_matches),
        )

    async def process(self, request: ProcessRequest) -> ProcessResponse:
        """
        Process text through TM for translation.

        Segments the text and finds matches for each segment.
        """
        # Get segmenter
        segment_type = SegmentType(request.segment_type)
        segmenter = get_segmenter(segment_type)

        # Segment the text
        text_segments = segmenter.segment(request.source_text)

        # Get all TM segments
        all_tm_segments = []
        tm_names = {}

        for tm_id in request.tm_ids:
            tm = self.repository.get_tm(tm_id)
            if tm:
                tm_names[tm_id] = tm.name
                segments = self.repository.get_all_segments(tm_id)
                all_tm_segments.extend(segments)

        # Match each segment
        processed = []
        matched_count = 0
        total_cost_factor = 0.0

        for seg in text_segments:
            match = self.matcher.find_best(
                seg.text,
                all_tm_segments,
                min_similarity=request.min_similarity,
            )

            cost_factor = self.matcher.estimate_cost_factor(match)
            total_cost_factor += cost_factor

            if match and match.match_type != MatchType.NO_MATCH:
                matched_count += 1
                processed.append(ProcessedSegment(
                    source_text=seg.text,
                    target_text=match.segment.target_text,
                    match=self._match_to_response(match, tm_names.get(match.segment.tm_id, "")),
                    needs_translation=match.match_type == MatchType.FUZZY,
                    estimated_cost_factor=cost_factor,
                ))
            else:
                processed.append(ProcessedSegment(
                    source_text=seg.text,
                    target_text=None,
                    match=None,
                    needs_translation=True,
                    estimated_cost_factor=1.0,
                ))

        # Calculate savings
        total_segments = len(text_segments)
        avg_cost_factor = total_cost_factor / total_segments if total_segments > 0 else 1.0
        estimated_savings = (1.0 - avg_cost_factor) * 100

        return ProcessResponse(
            segments=processed,
            total_segments=total_segments,
            matched_segments=matched_count,
            estimated_savings=estimated_savings,
        )

    def _match_to_response(self, match: MatchResult, tm_name: str) -> TMMatch:
        """Convert MatchResult to TMMatch schema."""
        return TMMatch(
            segment_id=match.segment.id,
            source_text=match.segment.source_text,
            target_text=match.segment.target_text,
            similarity=match.similarity,
            match_type=match.match_type,
            quality_score=match.segment.quality_score,
            source_type=SourceType(match.segment.source_type),
            tm_id=match.segment.tm_id,
            tm_name=tm_name,
        )

    # ==================== LEARN FROM TRANSLATIONS ====================

    async def learn(
        self,
        tm_id: str,
        source_text: str,
        target_text: str,
        quality_score: float = 0.8,
        source_type: str = "ai",
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
    ) -> Optional[SegmentResponse]:
        """
        Learn from a new translation.

        Stores the segment in TM for future use.
        """
        segment = self.repository.add_segment(
            tm_id=tm_id,
            source_text=source_text,
            target_text=target_text,
            quality_score=quality_score,
            source_type=source_type,
            context_before=context_before,
            context_after=context_after,
        )

        if segment:
            return SegmentResponse.model_validate(segment.to_dict())
        return None

    async def learn_batch(
        self,
        tm_id: str,
        pairs: List[Tuple[str, str]],
        quality_score: float = 0.8,
        source_type: str = "ai",
    ) -> BulkSegmentResult:
        """
        Learn from multiple translations.

        Args:
            tm_id: Translation Memory ID
            pairs: List of (source, target) tuples
            quality_score: Quality score for all segments
            source_type: Source type for all segments

        Returns:
            Bulk result
        """
        segment_data = [
            {
                "source_text": source,
                "target_text": target,
                "quality_score": quality_score,
                "source_type": source_type,
            }
            for source, target in pairs
        ]

        added, skipped, errors = self.repository.add_segments_bulk(
            tm_id=tm_id,
            segments=segment_data,
            skip_duplicates=True,
        )

        return BulkSegmentResult(added=added, skipped=skipped, errors=errors)


# Global instance
_service: Optional[TMService] = None


def get_tm_service() -> TMService:
    """Get or create the global service instance."""
    global _service
    if _service is None:
        _service = TMService()
    return _service
