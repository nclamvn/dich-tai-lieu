"""
Glossary API Router
FastAPI endpoints for glossary and term management.
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging

from core.glossary.service import get_glossary_service, GlossaryService
from core.glossary.schemas import (
    GlossaryCreate, GlossaryUpdate, GlossaryResponse, GlossaryListResponse,
    TermCreate, TermUpdate, TermResponse, TermListResponse,
    BulkTermCreate, BulkTermDelete, BulkTermResult,
    MatchRequest, MatchResponse,
    PrebuiltListResponse, ImportResult,
    DOMAINS, LANGUAGES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/glossary", tags=["Glossary"])


def get_service() -> GlossaryService:
    """Get glossary service instance."""
    return get_glossary_service()


# =============================================================================
# Glossary CRUD
# =============================================================================

@router.post("/", response_model=GlossaryResponse)
async def create_glossary(data: GlossaryCreate):
    """
    Create a new glossary.

    - **name**: Glossary display name
    - **description**: Optional description
    - **domain**: Domain type (general, medical, legal, tech, etc.)
    - **source_language**: Source language code (default: en)
    - **target_language**: Target language code (default: vi)
    """
    service = get_service()
    try:
        return await service.create_glossary(data)
    except Exception as e:
        logger.error(f"Error creating glossary: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=GlossaryListResponse)
async def list_glossaries(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    source_language: Optional[str] = Query(None, description="Filter by source language"),
    target_language: Optional[str] = Query(None, description="Filter by target language"),
    include_prebuilt: bool = Query(True, description="Include pre-built glossaries"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """
    List all glossaries with optional filtering.
    """
    service = get_service()
    glossaries = await service.list_glossaries(
        domain=domain,
        source_language=source_language,
        target_language=target_language,
        include_prebuilt=include_prebuilt,
        search=search,
    )
    return GlossaryListResponse(glossaries=glossaries, total=len(glossaries))


@router.get("/domains")
async def list_domains():
    """Get list of available domains."""
    return {"domains": DOMAINS}


@router.get("/languages")
async def list_languages():
    """Get list of available languages."""
    return {"languages": [{"code": code, "name": name} for code, name in LANGUAGES]}


@router.get("/{glossary_id}", response_model=GlossaryResponse)
async def get_glossary(glossary_id: str):
    """Get glossary by ID."""
    service = get_service()
    glossary = await service.get_glossary(glossary_id)
    if not glossary:
        raise HTTPException(status_code=404, detail="Glossary not found")
    return glossary


@router.patch("/{glossary_id}", response_model=GlossaryResponse)
async def update_glossary(glossary_id: str, data: GlossaryUpdate):
    """
    Update glossary metadata.

    Note: Pre-built glossaries cannot be modified.
    """
    service = get_service()
    try:
        glossary = await service.update_glossary(glossary_id, data)
        if not glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")
        return glossary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{glossary_id}")
async def delete_glossary(glossary_id: str):
    """
    Delete a glossary.

    Note: Pre-built glossaries cannot be deleted.
    """
    service = get_service()
    try:
        success = await service.delete_glossary(glossary_id)
        if not success:
            raise HTTPException(status_code=404, detail="Glossary not found")
        return {"status": "deleted", "glossary_id": glossary_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{glossary_id}/duplicate", response_model=GlossaryResponse)
async def duplicate_glossary(
    glossary_id: str,
    new_name: Optional[str] = Query(None, description="Name for duplicated glossary"),
):
    """Duplicate a glossary with all its terms."""
    service = get_service()
    glossary = await service.duplicate_glossary(glossary_id, new_name)
    if not glossary:
        raise HTTPException(status_code=404, detail="Glossary not found")
    return glossary


# =============================================================================
# Term CRUD
# =============================================================================

@router.post("/{glossary_id}/terms", response_model=TermResponse)
async def add_term(glossary_id: str, data: TermCreate):
    """
    Add a new term to glossary.

    - **source_term**: Term in source language
    - **target_term**: Translation in target language
    - **context**: Optional usage context
    - **part_of_speech**: Word type (noun, verb, etc.)
    - **priority**: 1-10, higher means preferred
    """
    service = get_service()
    try:
        return await service.add_term(glossary_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{glossary_id}/terms", response_model=TermListResponse)
async def list_terms(
    glossary_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search source/target terms"),
    sort: str = Query("source_term", description="Sort field"),
    order: str = Query("asc", description="Sort order (asc/desc)"),
):
    """List terms with pagination."""
    service = get_service()
    return await service.list_terms(
        glossary_id=glossary_id,
        page=page,
        limit=limit,
        search=search,
        sort=sort,
        order=order,
    )


@router.get("/{glossary_id}/terms/{term_id}", response_model=TermResponse)
async def get_term(glossary_id: str, term_id: str):
    """Get a specific term."""
    service = get_service()
    term = await service.get_term(glossary_id, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return term


@router.patch("/{glossary_id}/terms/{term_id}", response_model=TermResponse)
async def update_term(glossary_id: str, term_id: str, data: TermUpdate):
    """Update a term."""
    service = get_service()
    term = await service.update_term(glossary_id, term_id, data)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return term


@router.delete("/{glossary_id}/terms/{term_id}")
async def delete_term(glossary_id: str, term_id: str):
    """Delete a term."""
    service = get_service()
    success = await service.delete_term(glossary_id, term_id)
    if not success:
        raise HTTPException(status_code=404, detail="Term not found")
    return {"status": "deleted", "term_id": term_id}


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/{glossary_id}/terms/bulk", response_model=BulkTermResult)
async def add_terms_bulk(glossary_id: str, data: BulkTermCreate):
    """
    Add multiple terms at once.

    Maximum 1000 terms per request.
    """
    service = get_service()
    try:
        return await service.add_terms_bulk(
            glossary_id=glossary_id,
            terms=data.terms,
            skip_duplicates=data.skip_duplicates,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{glossary_id}/terms/bulk")
async def delete_terms_bulk(glossary_id: str, data: BulkTermDelete):
    """Delete multiple terms at once."""
    service = get_service()
    deleted = await service.delete_terms_bulk(glossary_id, data.term_ids)
    return {"status": "deleted", "count": deleted}


# =============================================================================
# Import/Export
# =============================================================================

@router.post("/{glossary_id}/import", response_model=ImportResult)
async def import_terms(
    glossary_id: str,
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True, description="Skip duplicate terms"),
    update_existing: bool = Query(False, description="Update existing terms"),
):
    """
    Import terms from file.

    Supported formats: xlsx, csv, tbx
    """
    service = get_service()
    try:
        result = await service.import_terms(
            glossary_id=glossary_id,
            file=file,
            skip_duplicates=skip_duplicates,
            update_existing=update_existing,
        )
        return result
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{glossary_id}/export")
async def export_terms(
    glossary_id: str,
    format: str = Query("xlsx", description="Export format (xlsx, csv, tbx)"),
):
    """Export glossary terms to file."""
    service = get_service()
    try:
        content, filename, media_type = await service.export_terms(glossary_id, format)
        return StreamingResponse(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{format}")
async def get_import_template(format: str = "xlsx"):
    """Get import template file."""
    service = get_service()
    content, filename, media_type = service.get_import_template(format)
    return StreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# =============================================================================
# Pre-built Glossaries
# =============================================================================

@router.get("/prebuilt/list", response_model=PrebuiltListResponse)
async def list_prebuilt():
    """List available pre-built glossaries."""
    service = get_service()
    result = await service.list_prebuilt_glossaries()
    return PrebuiltListResponse(glossaries=result["glossaries"])


@router.post("/prebuilt/{prebuilt_id}/clone", response_model=GlossaryResponse)
async def clone_prebuilt(
    prebuilt_id: str,
    new_name: Optional[str] = Query(None, description="Name for cloned glossary"),
):
    """
    Clone a pre-built glossary to create editable copy.

    Available pre-built glossaries:
    - tech_vi: Technology terms EN-VI
    - medical_vi: Medical terms EN-VI
    - legal_vi: Legal terms EN-VI
    """
    service = get_service()
    glossary = await service.clone_prebuilt(prebuilt_id, new_name)
    if not glossary:
        raise HTTPException(status_code=404, detail="Pre-built glossary not found")
    return glossary


# =============================================================================
# Matching
# =============================================================================

@router.post("/match", response_model=MatchResponse)
async def match_terms(data: MatchRequest):
    """
    Find glossary terms in text.

    Useful for previewing which terms will be matched before translation.
    """
    service = get_service()
    return await service.match_terms(
        glossary_ids=data.glossary_ids,
        text=data.text,
        highlight=data.highlight,
    )
