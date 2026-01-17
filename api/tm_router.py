"""
Translation Memory API Router
FastAPI endpoints for TM operations.
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging
import io
import json

from core.tm.service import get_tm_service, TMService
from core.tm.schemas import (
    TMCreate, TMUpdate, TMResponse, TMListResponse,
    SegmentCreate, SegmentUpdate, SegmentResponse, SegmentListResponse,
    BulkSegmentCreate, BulkSegmentResult,
    LookupRequest, LookupResponse,
    ProcessRequest, ProcessResponse,
    TMStats, ImportResult,
)
from core.tm.io import (
    export_tm_to_tmx, export_tm_to_csv,
    import_tm_from_tmx, import_tm_from_csv,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tm", tags=["Translation Memory"])


def get_service() -> TMService:
    """Get TM service instance."""
    return get_tm_service()


# =============================================================================
# TM CRUD
# =============================================================================

@router.post("/", response_model=TMResponse)
async def create_tm(data: TMCreate):
    """
    Create a new Translation Memory.

    - **name**: TM display name
    - **description**: Optional description
    - **source_language**: Source language code (default: en)
    - **target_language**: Target language code (default: vi)
    - **domain**: Domain type (general, medical, legal, tech, etc.)
    """
    service = get_service()
    try:
        return await service.create_tm(data)
    except Exception as e:
        logger.error(f"Error creating TM: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=TMListResponse)
async def list_tms(
    source_language: Optional[str] = Query(None, description="Filter by source language"),
    target_language: Optional[str] = Query(None, description="Filter by target language"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """
    List all Translation Memories with optional filtering.
    """
    service = get_service()
    tms = await service.list_tms(
        source_language=source_language,
        target_language=target_language,
        domain=domain,
        search=search,
    )
    return TMListResponse(tms=tms, total=len(tms))


@router.get("/{tm_id}", response_model=TMResponse)
async def get_tm(tm_id: str):
    """Get Translation Memory by ID."""
    service = get_service()
    tm = await service.get_tm(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")
    return tm


@router.patch("/{tm_id}", response_model=TMResponse)
async def update_tm(tm_id: str, data: TMUpdate):
    """
    Update Translation Memory metadata.
    """
    service = get_service()
    try:
        tm = await service.update_tm(tm_id, data)
        if not tm:
            raise HTTPException(status_code=404, detail="Translation Memory not found")
        return tm
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tm_id}")
async def delete_tm(tm_id: str):
    """
    Delete a Translation Memory.
    """
    service = get_service()
    success = await service.delete_tm(tm_id)
    if not success:
        raise HTTPException(status_code=404, detail="Translation Memory not found")
    return {"status": "deleted", "tm_id": tm_id}


# =============================================================================
# Segment CRUD
# =============================================================================

@router.post("/{tm_id}/segments", response_model=SegmentResponse)
async def add_segment(tm_id: str, data: SegmentCreate):
    """
    Add a new segment to Translation Memory.

    - **source_text**: Source text
    - **target_text**: Translated text
    - **quality_score**: Quality score 0.0-1.0
    - **source_type**: ai, human, or verified
    - **context_before**: Text before this segment (optional)
    - **context_after**: Text after this segment (optional)
    """
    service = get_service()
    try:
        return await service.add_segment(tm_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tm_id}/segments", response_model=SegmentListResponse)
async def list_segments(
    tm_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search source/target text"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
):
    """List segments with pagination."""
    service = get_service()
    return await service.list_segments(
        tm_id=tm_id,
        page=page,
        limit=limit,
        search=search,
        sort=sort,
        order=order,
    )


@router.get("/{tm_id}/segments/{segment_id}", response_model=SegmentResponse)
async def get_segment(tm_id: str, segment_id: str):
    """Get a specific segment."""
    service = get_service()
    segment = await service.get_segment(tm_id, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.patch("/{tm_id}/segments/{segment_id}", response_model=SegmentResponse)
async def update_segment(tm_id: str, segment_id: str, data: SegmentUpdate):
    """Update a segment."""
    service = get_service()
    segment = await service.update_segment(tm_id, segment_id, data)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.delete("/{tm_id}/segments/{segment_id}")
async def delete_segment(tm_id: str, segment_id: str):
    """Delete a segment."""
    service = get_service()
    success = await service.delete_segment(tm_id, segment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Segment not found")
    return {"status": "deleted", "segment_id": segment_id}


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/{tm_id}/segments/bulk", response_model=BulkSegmentResult)
async def add_segments_bulk(tm_id: str, data: BulkSegmentCreate):
    """
    Add multiple segments at once.

    Maximum 5000 segments per request.
    """
    service = get_service()
    try:
        return await service.add_segments_bulk(
            tm_id=tm_id,
            segments=data.segments,
            skip_duplicates=data.skip_duplicates,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Lookup & Matching
# =============================================================================

@router.post("/lookup", response_model=LookupResponse)
async def lookup(data: LookupRequest):
    """
    Look up source text in Translation Memories.

    Finds matching segments sorted by similarity score.
    Returns exact matches first, then fuzzy matches.

    - **tm_ids**: List of TM IDs to search
    - **source_text**: Text to look up
    - **min_similarity**: Minimum similarity threshold (default: 0.75)
    - **max_results**: Maximum results to return (default: 5)
    """
    service = get_service()
    return await service.lookup(data)


@router.post("/process", response_model=ProcessResponse)
async def process(data: ProcessRequest):
    """
    Process text through Translation Memory for translation.

    Segments the text and finds matches for each segment.
    Returns estimated cost savings based on match quality.

    - **tm_ids**: List of TM IDs to search
    - **source_text**: Text to process
    - **segment_type**: sentence, paragraph, or smart
    - **min_similarity**: Minimum similarity threshold (default: 0.75)
    """
    service = get_service()
    return await service.process(data)


# =============================================================================
# Learn from Translations
# =============================================================================

@router.post("/{tm_id}/learn", response_model=SegmentResponse)
async def learn(
    tm_id: str,
    source_text: str = Query(..., min_length=1),
    target_text: str = Query(..., min_length=1),
    quality_score: float = Query(0.8, ge=0.0, le=1.0),
    source_type: str = Query("ai"),
):
    """
    Learn from a new translation.

    Stores the source/target pair in TM for future use.
    Used for automatic TM population during translation.
    """
    service = get_service()
    segment = await service.learn(
        tm_id=tm_id,
        source_text=source_text,
        target_text=target_text,
        quality_score=quality_score,
        source_type=source_type,
    )
    if not segment:
        raise HTTPException(status_code=400, detail="Could not save segment (may be duplicate)")
    return segment


@router.post("/{tm_id}/learn/batch", response_model=BulkSegmentResult)
async def learn_batch(
    tm_id: str,
    pairs: List[dict],  # [{"source": "...", "target": "..."}, ...]
    quality_score: float = Query(0.8, ge=0.0, le=1.0),
    source_type: str = Query("ai"),
):
    """
    Learn from multiple translations.

    Batch stores source/target pairs in TM.
    """
    service = get_service()

    # Convert to list of tuples
    tuple_pairs = [(p.get("source", ""), p.get("target", "")) for p in pairs if p.get("source") and p.get("target")]

    return await service.learn_batch(
        tm_id=tm_id,
        pairs=tuple_pairs,
        quality_score=quality_score,
        source_type=source_type,
    )


# =============================================================================
# Import/Export
# =============================================================================

@router.post("/{tm_id}/import", response_model=ImportResult)
async def import_segments(
    tm_id: str,
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True, description="Skip duplicate segments"),
):
    """
    Import segments from file.

    Supported formats: JSON, CSV, TMX

    JSON format: [{"source": "...", "target": "...", "quality_score": 0.8}, ...]
    CSV format: source,target,quality_score (with header)
    TMX: Standard TMX format
    """
    service = get_service()

    try:
        content = await file.read()
        filename = file.filename.lower()

        segments_data = []

        if filename.endswith('.json'):
            data = json.loads(content)
            for item in data:
                segments_data.append({
                    "source_text": item.get("source", item.get("source_text", "")),
                    "target_text": item.get("target", item.get("target_text", "")),
                    "quality_score": item.get("quality_score", 0.8),
                    "source_type": item.get("source_type", "human"),
                })

        elif filename.endswith('.csv'):
            import csv
            reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            for row in reader:
                segments_data.append({
                    "source_text": row.get("source", row.get("source_text", "")),
                    "target_text": row.get("target", row.get("target_text", "")),
                    "quality_score": float(row.get("quality_score", 0.8)),
                    "source_type": row.get("source_type", "human"),
                })

        elif filename.endswith('.tmx'):
            # Parse TMX using io module
            metadata, parsed_segments = import_tm_from_tmx(content.decode('utf-8'))
            for seg in parsed_segments:
                segments_data.append({
                    "source_text": seg.source_text,
                    "target_text": seg.target_text,
                    "quality_score": seg.quality_score,
                    "source_type": seg.source_type,
                })

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use JSON, CSV, or TMX.")

        # Add segments
        if not segments_data:
            return ImportResult(status="empty", added=0, updated=0, skipped=0, errors=[])

        segments = [SegmentCreate(
            source_text=s["source_text"],
            target_text=s["target_text"],
            quality_score=s["quality_score"],
            source_type=s["source_type"],
        ) for s in segments_data if s["source_text"] and s["target_text"]]

        result = await service.add_segments_bulk(tm_id, segments, skip_duplicates)

        return ImportResult(
            status="success",
            added=result.added,
            updated=0,
            skipped=result.skipped,
            errors=result.errors,
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tm_id}/export")
async def export_segments(
    tm_id: str,
    format: str = Query("json", description="Export format (json, csv, tmx)"),
):
    """Export TM segments to file."""
    service = get_service()

    try:
        # Get TM info
        tm = await service.get_tm(tm_id)
        if not tm:
            raise HTTPException(status_code=404, detail="Translation Memory not found")

        # Get all segments
        result = await service.list_segments(tm_id, page=1, limit=10000)
        segments = result.segments

        if format == "json":
            data = [
                {
                    "source": s.source_text,
                    "target": s.target_text,
                    "quality_score": s.quality_score,
                    "source_type": s.source_type.value if hasattr(s.source_type, 'value') else s.source_type,
                }
                for s in segments
            ]
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="tm_{tm_id}.json"'}
            )

        elif format == "csv":
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["source", "target", "quality_score", "source_type"])
            for s in segments:
                writer.writerow([
                    s.source_text,
                    s.target_text,
                    s.quality_score,
                    s.source_type.value if hasattr(s.source_type, 'value') else s.source_type,
                ])
            content = output.getvalue()
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="tm_{tm_id}.csv"'}
            )

        elif format == "tmx":
            # Generate TMX using io module
            segment_dicts = [
                {
                    "source_text": s.source_text,
                    "target_text": s.target_text,
                    "quality_score": s.quality_score,
                    "source_type": s.source_type.value if hasattr(s.source_type, 'value') else s.source_type,
                    "notes": getattr(s, 'notes', None),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in segments
            ]
            tmx_content = export_tm_to_tmx(
                tm_name=tm.name,
                segments=segment_dicts,
                source_lang=tm.source_language,
                target_lang=tm.target_language,
            )

            return StreamingResponse(
                io.BytesIO(tmx_content.encode('utf-8')),
                media_type="application/xml",
                headers={"Content-Disposition": f'attachment; filename="tm_{tm_id}.tmx"'}
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use json, csv, or tmx.")

    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;"))


# =============================================================================
# Statistics
# =============================================================================

@router.get("/{tm_id}/stats")
async def get_tm_stats(tm_id: str):
    """
    Get Translation Memory statistics.

    Returns segment count, word count, and usage stats.
    """
    service = get_service()
    tm = await service.get_tm(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    return {
        "tm_id": tm_id,
        "tm_name": tm.name,
        "segment_count": tm.segment_count,
        "total_words": tm.total_words,
        "source_language": tm.source_language,
        "target_language": tm.target_language,
        "domain": tm.domain,
        "created_at": tm.created_at,
        "updated_at": tm.updated_at,
    }
