"""
Author Mode API Routes (Phase 4.1 MVP)

REST endpoints for co-writing, rewriting, and content generation.
Uses prompt-based style control (no corpus learning).
"""

from typing import List, Optional, Dict
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import uuid
import shutil

from core.author import AuthorEngine, Variation
from core.author.advanced import VariationScorer, MemoryContextBuilder, ExportUtilities
from core.author.book_export import BookExporter
from core.author.document_parser import DocumentParser, ParsedDocument
from core.author.memory_extractor import MemoryExtractor, ExtractionResult
from core.author.consistency_checker import (
    ConsistencyChecker,
    ConsistencyReport,
    ConsistencyIssue,
    SeverityLevel,
    IssueType
)
from core.author.memory_store import MemoryStore
from core.author.llm_provider import create_llm_client
from config.logging_config import get_logger

logger = get_logger(__name__)


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class ProposeRequest(BaseModel):
    """Request to propose next paragraph(s)"""
    context: str = Field(..., description="Previous content for context")
    instruction: str = Field(
        default="Continue writing naturally",
        description="Instruction for what to write"
    )
    style: str = Field(default="neutral", description="Style preset name")
    target_length: int = Field(default=150, description="Target word count")
    n_variations: int = Field(default=3, ge=1, le=5, description="Number of variations")
    custom_style_instruction: Optional[str] = Field(
        default=None,
        description="Custom style override"
    )


class ProposeResponse(BaseModel):
    """Response with paragraph variations"""
    variations: List[dict] = Field(..., description="Generated variations")
    style: str = Field(..., description="Style used")


class RewriteRequest(BaseModel):
    """Request to rewrite text"""
    text: str = Field(..., description="Original text to rewrite")
    improvements: Optional[List[str]] = Field(
        default=None,
        description="Specific improvements to make"
    )
    style: str = Field(default="neutral", description="Style preset name")
    custom_style_instruction: Optional[str] = Field(
        default=None,
        description="Custom style override"
    )


class RewriteResponse(BaseModel):
    """Response with rewritten text"""
    original_text: str = Field(..., description="Original text")
    rewritten_text: str = Field(..., description="Improved text")
    style: str = Field(..., description="Style used")


class ExpandRequest(BaseModel):
    """Request to expand idea"""
    idea: str = Field(..., description="Brief idea to expand")
    target_length: int = Field(default=500, description="Target word count")
    style: str = Field(default="neutral", description="Style preset name")
    context: str = Field(default="", description="Additional context")
    content_type: str = Field(default="paragraph", description="Type of content")
    custom_style_instruction: Optional[str] = Field(
        default=None,
        description="Custom style override"
    )


class ExpandResponse(BaseModel):
    """Response with expanded content"""
    original_idea: str = Field(..., description="Original brief idea")
    expanded_content: str = Field(..., description="Expanded content")
    word_count: int = Field(..., description="Actual word count")
    style: str = Field(..., description="Style used")


class GenerateChapterRequest(BaseModel):
    """Request to generate full chapter"""
    book_title: str = Field(..., description="Title of the book")
    genre: str = Field(..., description="Book genre")
    chapter_outline: str = Field(..., description="Outline for this chapter")
    previous_summary: str = Field(default="", description="Summary of previous chapters")
    style: str = Field(default="neutral", description="Style preset name")
    target_length: int = Field(default=3000, description="Target word count")
    custom_style_instruction: Optional[str] = Field(
        default=None,
        description="Custom style override"
    )


class GenerateChapterResponse(BaseModel):
    """Response with generated chapter"""
    chapter_text: str = Field(..., description="Generated chapter")
    word_count: int = Field(..., description="Actual word count")
    style: str = Field(..., description="Style used")


class BrainstormRequest(BaseModel):
    """Request to brainstorm ideas"""
    focus: str = Field(..., description="What to brainstorm about")
    context: str = Field(default="", description="Project context")
    style: str = Field(default="neutral", description="Style/genre preset")
    n_ideas: int = Field(default=5, ge=3, le=10, description="Number of ideas")
    custom_style_instruction: Optional[str] = Field(
        default=None,
        description="Custom style override"
    )


class BrainstormResponse(BaseModel):
    """Response with brainstormed ideas"""
    ideas: List[str] = Field(..., description="Generated ideas")
    focus: str = Field(..., description="Brainstorming focus")


class CritiqueRequest(BaseModel):
    """Request for text critique"""
    text: str = Field(..., description="Text to critique")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Specific areas to focus on"
    )


class CritiqueResponse(BaseModel):
    """Response with critique"""
    critique: str = Field(..., description="Critique and feedback")


class CreateProjectRequest(BaseModel):
    """Request to create new project"""
    author_id: str = Field(..., description="Author identifier")
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Project description")
    genre: str = Field(..., description="Project genre")
    style: str = Field(default="neutral", description="Writing style")
    target_word_count: int = Field(default=50000, description="Target word count")


class ProjectResponse(BaseModel):
    """Response with project info"""
    project_id: str
    author_id: str
    title: str
    status: str
    word_count: int
    completion: str


class ListProjectsResponse(BaseModel):
    """Response with project list"""
    projects: List[dict] = Field(..., description="List of projects")


# ==============================================================================
# API ROUTER
# ==============================================================================

router = APIRouter(prefix="/api/author", tags=["author"])

# Global engine instance (will be initialized with LLM provider)
_engine: Optional[AuthorEngine] = None


def get_engine() -> AuthorEngine:
    """Get or create AuthorEngine instance"""
    global _engine
    if _engine is None:
        # Initialize without LLM provider for now
        # TODO: Inject LLM provider from config/environment
        _engine = AuthorEngine(
            llm_provider=None,  # Will be configured later
            data_path=Path("data/authors")
        )
    return _engine


# ==============================================================================
# CO-WRITING ENDPOINTS
# ==============================================================================

@router.post("/propose", response_model=ProposeResponse)
async def propose_next_paragraph(request: ProposeRequest):
    """
    Generate next paragraph(s) to continue writing

    Returns multiple variations for the user to choose from.
    Uses prompt-based style control.
    """
    try:
        engine = get_engine()

        variations = await engine.propose_next_paragraph(
            context=request.context,
            instruction=request.instruction,
            style=request.style,
            target_length=request.target_length,
            n_variations=request.n_variations,
            custom_style_instruction=request.custom_style_instruction
        )

        return ProposeResponse(
            variations=[
                {
                    "text": v.text,
                    "style": v.style,
                    "word_count": v.word_count,
                    "confidence": v.confidence
                }
                for v in variations
            ],
            style=request.style
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate proposals: {str(e)}")


# ==============================================================================
# REWRITING ENDPOINTS
# ==============================================================================

@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_text(request: RewriteRequest):
    """
    Rewrite text with improvements

    Improves clarity, flow, and style while maintaining core message.
    """
    try:
        engine = get_engine()

        rewritten = await engine.rewrite_paragraph(
            text=request.text,
            improvements=request.improvements,
            style=request.style,
            custom_style_instruction=request.custom_style_instruction
        )

        return RewriteResponse(
            original_text=request.text,
            rewritten_text=rewritten,
            style=request.style
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rewrite text: {str(e)}")


# ==============================================================================
# EXPANSION ENDPOINTS
# ==============================================================================

@router.post("/expand", response_model=ExpandResponse)
async def expand_idea(request: ExpandRequest):
    """
    Expand brief idea into full content

    Develops a brief idea or outline into complete paragraphs/sections.
    """
    try:
        engine = get_engine()

        expanded = await engine.expand_idea(
            idea=request.idea,
            target_length=request.target_length,
            style=request.style,
            context=request.context,
            content_type=request.content_type,
            custom_style_instruction=request.custom_style_instruction
        )

        return ExpandResponse(
            original_idea=request.idea,
            expanded_content=expanded,
            word_count=len(expanded.split()),
            style=request.style
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to expand idea: {str(e)}")


# ==============================================================================
# CHAPTER GENERATION ENDPOINTS
# ==============================================================================

@router.post("/generate-chapter", response_model=GenerateChapterResponse)
async def generate_chapter(request: GenerateChapterRequest):
    """
    Generate full chapter from outline

    Creates complete chapter text based on outline and book context.
    """
    try:
        engine = get_engine()

        chapter = await engine.generate_chapter(
            book_title=request.book_title,
            genre=request.genre,
            chapter_outline=request.chapter_outline,
            previous_summary=request.previous_summary,
            style=request.style,
            target_length=request.target_length,
            custom_style_instruction=request.custom_style_instruction
        )

        return GenerateChapterResponse(
            chapter_text=chapter,
            word_count=len(chapter.split()),
            style=request.style
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate chapter: {str(e)}")


# ==============================================================================
# BRAINSTORMING ENDPOINTS
# ==============================================================================

@router.post("/brainstorm", response_model=BrainstormResponse)
async def brainstorm_ideas(request: BrainstormRequest):
    """
    Generate creative ideas for development

    Helps authors brainstorm plot points, character development, etc.
    """
    try:
        engine = get_engine()

        ideas = await engine.brainstorm_ideas(
            focus=request.focus,
            context=request.context,
            style=request.style,
            n_ideas=request.n_ideas,
            custom_style_instruction=request.custom_style_instruction
        )

        return BrainstormResponse(
            ideas=ideas,
            focus=request.focus
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to brainstorm ideas: {str(e)}")


# ==============================================================================
# CRITIQUE ENDPOINTS
# ==============================================================================

@router.post("/critique", response_model=CritiqueResponse)
async def critique_text(request: CritiqueRequest):
    """
    Provide constructive feedback on text

    Analyzes text and provides actionable improvement suggestions.
    """
    try:
        engine = get_engine()

        critique = await engine.critique_text(
            text=request.text,
            focus_areas=request.focus_areas
        )

        return CritiqueResponse(
            critique=critique
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to critique text: {str(e)}")


# ==============================================================================
# PROJECT MANAGEMENT ENDPOINTS
# ==============================================================================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """
    Create new author project

    Initializes a new writing project with metadata and structure.
    """
    try:
        engine = get_engine()

        project = engine.create_project(
            author_id=request.author_id,
            title=request.title,
            description=request.description,
            genre=request.genre,
            style=request.style,
            target_word_count=request.target_word_count
        )

        return ProjectResponse(
            project_id=project.project_id,
            author_id=project.author_id,
            title=project.title,
            status=project.status,
            word_count=project.current_word_count,
            completion=f"{project.completion_percentage():.1f}%"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects/{author_id}", response_model=ListProjectsResponse)
async def list_projects(author_id: str):
    """
    List all projects for an author

    Returns metadata for all projects belonging to the specified author.
    """
    try:
        engine = get_engine()
        projects = engine.list_projects(author_id)

        return ListProjectsResponse(
            projects=projects
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


class AddChapterContentRequest(BaseModel):
    """Request to add/update chapter content"""
    content: str
    update_memory: bool = True


@router.post("/projects/{author_id}/{project_id}/chapter/{chapter_num}")
async def add_chapter_content(
    author_id: str,
    project_id: str,
    chapter_num: int,
    request: AddChapterContentRequest
):
    """
    Add or update content for a specific chapter

    This endpoint allows manual content addition and automatically updates
    vector memory if enabled.
    """
    try:
        engine = get_engine()
        project = engine.load_project(author_id, project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Add content to chapter
        project.add_content(chapter_num, request.content, update_memory=request.update_memory)

        # Save project
        project.save(engine.data_path)

        return {
            "status": "success",
            "chapter": chapter_num,
            "word_count": len(request.content.split()),
            "total_word_count": project.current_word_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add chapter content: {str(e)}")


# ==============================================================================
# UTILITY ENDPOINTS
# ==============================================================================

@router.get("/styles")
async def list_available_styles():
    """
    List available style presets

    Returns all predefined styles that can be used for prompt-based control.
    """
    from core.author.models import AuthorConfig

    config = AuthorConfig()
    return {
        "styles": list(config.style_instructions.keys()),
        "descriptions": config.style_instructions
    }


# ==============================================================================
# MEMORY MANAGEMENT ENDPOINTS (Phase 4.3)
# ==============================================================================

class AddCharacterRequest(BaseModel):
    """Request to add character to memory"""
    project_id: str
    author_id: str
    name: str
    description: str = ""
    role: str = ""
    traits: List[str] = Field(default_factory=list)
    first_appearance_chapter: Optional[int] = None


class AddEventRequest(BaseModel):
    """Request to add timeline event"""
    project_id: str
    author_id: str
    description: str
    chapter: int
    participants: List[str] = Field(default_factory=list)
    location: Optional[str] = None


class AddPlotPointRequest(BaseModel):
    """Request to add plot point"""
    project_id: str
    author_id: str
    point_id: str
    type: str
    description: str
    chapter: int


class MemorySearchRequest(BaseModel):
    """Request to search vector memory"""
    project_id: str
    author_id: str
    query: str
    n_results: int = Field(default=5, ge=1, le=20)


@router.post("/memory/character")
async def add_character(request: AddCharacterRequest):
    """Add character to project memory"""
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        from core.author.memory_store import Character

        character = Character(
            name=request.name,
            description=request.description,
            role=request.role,
            traits=request.traits,
            first_appearance_chapter=request.first_appearance_chapter
        )

        project.memory.add_character(character)

        return {"status": "success", "character_name": character.name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add character: {str(e)}")


@router.get("/memory/characters/{author_id}/{project_id}")
async def list_characters(author_id: str, project_id: str, chapter: Optional[int] = None):
    """List characters in project memory"""
    try:
        engine = get_engine()
        project = engine.load_project(author_id, project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        characters = project.memory.list_characters(chapter)

        return {
            "characters": [
                {
                    "name": char.name,
                    "aliases": char.aliases,
                    "description": char.description,
                    "role": char.role,
                    "traits": char.traits,
                    "first_appearance": char.first_appearance_chapter,
                    "last_appearance": char.last_appearance_chapter
                }
                for char in characters
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list characters: {str(e)}")


@router.post("/memory/event")
async def add_timeline_event(request: AddEventRequest):
    """Add event to project timeline"""
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        from core.author.memory_store import TimelineEvent
        import uuid

        event = TimelineEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            description=request.description,
            chapter=request.chapter,
            participants=request.participants,
            location=request.location
        )

        project.memory.add_event(event)

        return {"status": "success", "event_id": event.event_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add event: {str(e)}")


@router.get("/memory/timeline/{author_id}/{project_id}")
async def get_timeline(author_id: str, project_id: str, up_to_chapter: Optional[int] = None):
    """Get project timeline"""
    try:
        engine = get_engine()
        project = engine.load_project(author_id, project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        if up_to_chapter:
            summary = project.memory.get_timeline_summary(up_to_chapter)
            return {"summary": summary}
        else:
            events = project.memory.get_events()
            return {
                "events": [
                    {
                        "event_id": evt.event_id,
                        "description": evt.description,
                        "chapter": evt.chapter,
                        "participants": evt.participants,
                        "location": evt.location
                    }
                    for evt in events
                ]
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


@router.post("/memory/plot-point")
async def add_plot_point(request: AddPlotPointRequest):
    """Add plot point to project memory"""
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        from core.author.memory_store import PlotPoint

        plot_point = PlotPoint(
            point_id=request.point_id,
            type=request.type,
            description=request.description,
            first_introduced_chapter=request.chapter
        )

        project.memory.add_plot_point(plot_point)

        return {"status": "success", "point_id": plot_point.point_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add plot point: {str(e)}")


@router.get("/memory/consistency/{author_id}/{project_id}")
async def check_consistency(author_id: str, project_id: str):
    """Check project for consistency issues"""
    try:
        engine = get_engine()
        project = engine.load_project(author_id, project_id)

        if not project or not project.memory:
            raise HTTPException(status_code=404, detail="Project not found or memory not initialized")

        issues = project.memory.check_character_consistency()

        return {
            "has_issues": len(issues) > 0,
            "character_issues": issues
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check consistency: {str(e)}")


@router.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """Search project memory semantically"""
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project or not project.vector_memory:
            raise HTTPException(status_code=404, detail="Project not found or vector memory not initialized")

        results = project.vector_memory.search(
            query=request.query,
            n_results=request.n_results
        )

        return {
            "results": [
                {
                    "text": text,
                    "similarity": score,
                    "metadata": metadata
                }
                for text, score, metadata in results
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {str(e)}")


# ==============================================================================
# ADVANCED FEATURES ENDPOINTS (Phase 4.4)
# ==============================================================================

class ProposeScoredRequest(BaseModel):
    """Request for memory-aware content generation with scoring"""
    project_id: str
    author_id: str
    chapter: int
    context: str
    instruction: str = "Continue writing naturally"
    style: str = "neutral"
    n_variations: int = Field(default=3, ge=1, le=5)


class ExportRequest(BaseModel):
    """Request to export project data"""
    project_id: str
    author_id: str
    format: str = Field(default="markdown", description="Output format: markdown, txt, html")


@router.post("/propose-scored")
async def propose_with_scoring(request: ProposeScoredRequest):
    """
    Generate next paragraph with memory awareness and quality scoring (Phase 4.4)

    Returns scored and ranked variations based on:
    - Memory consistency
    - Coherence
    - Style matching
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build memory-enriched context
        context_builder = MemoryContextBuilder(project)
        memory_context = context_builder.build_context_for_chapter(
            chapter=request.chapter,
            focus=request.instruction
        )

        # Enhanced context with memory
        full_context = request.context
        if memory_context:
            full_context = f"{memory_context}\n\n---\n\n{request.context}"

        # Generate variations
        variations = await engine.propose_next_paragraph(
            context=full_context,
            instruction=request.instruction,
            style=request.style,
            n_variations=request.n_variations
        )

        # Score and rank variations
        scorer = VariationScorer(project)
        variations_data = [{"text": v.text, "style": v.style} for v in variations]
        scored = scorer.rank_variations(variations_data, chapter=request.chapter)

        return {
            "variations": [
                {
                    "text": v.text,
                    "style": v.style,
                    "word_count": v.word_count,
                    "scores": {
                        "consistency": v.consistency_score,
                        "coherence": v.coherence_score,
                        "style_match": v.style_score,
                        "overall": v.overall_score
                    },
                    "issues": v.issues
                }
                for v in scored
            ],
            "memory_context_used": bool(memory_context)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate scored variations: {str(e)}")


@router.post("/export/glossary")
async def export_character_glossary(request: ExportRequest):
    """
    Export character glossary (Phase 4.4)

    Generates formatted character reference document
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        exporter = ExportUtilities(project)
        glossary = exporter.generate_character_glossary(format=request.format)

        return {
            "content": glossary,
            "format": request.format,
            "character_count": len(project.memory.characters) if project.memory else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export glossary: {str(e)}")


@router.post("/export/timeline")
async def export_timeline(request: ExportRequest):
    """
    Export project timeline (Phase 4.4)

    Generates formatted timeline document
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        exporter = ExportUtilities(project)
        timeline = exporter.generate_timeline_document(format=request.format)

        return {
            "content": timeline,
            "format": request.format,
            "event_count": len(project.memory.timeline) if project.memory else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export timeline: {str(e)}")


@router.post("/export/plot-summary")
async def export_plot_summary(request: ExportRequest):
    """
    Export plot summary (Phase 4.4)

    Generates formatted plot summary document
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        exporter = ExportUtilities(project)
        summary = exporter.generate_plot_summary(format=request.format)

        return {
            "content": summary,
            "format": request.format,
            "plot_point_count": len(project.memory.plot_points) if project.memory else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export plot summary: {str(e)}")


class ExportBookRequest(BaseModel):
    """Request to export project as book"""
    project_id: str
    author_id: str
    output_format: str = Field(default="docx", description="Output format: docx, txt")
    include_glossary: bool = True
    include_timeline: bool = True
    include_plot_summary: bool = False


@router.post("/export/book")
async def export_book(request: ExportBookRequest):
    """
    Export project as professional book (Phase 4.4)

    Combines all chapters with appendices into publication-ready format
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.chapters:
            raise HTTPException(status_code=400, detail="No chapters to export")

        # Create export directory
        export_dir = Path("data/exports") / request.author_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')

        exporter = BookExporter(project)

        if request.output_format == "docx":
            output_path = export_dir / f"{safe_title}.docx"
            result_path = exporter.export_to_docx(
                output_path=output_path,
                include_glossary=request.include_glossary,
                include_timeline=request.include_timeline,
                include_plot_summary=request.include_plot_summary
            )

        elif request.output_format == "txt":
            output_path = export_dir / f"{safe_title}.txt"
            result_path = exporter.export_simple_text(output_path=output_path)

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.output_format}")

        return {
            "status": "success",
            "output_path": str(result_path),
            "format": request.output_format,
            "chapter_count": len(project.chapters),
            "word_count": project.current_word_count,
            "included_appendices": {
                "glossary": request.include_glossary and bool(project.memory and project.memory.characters),
                "timeline": request.include_timeline and bool(project.memory and project.memory.timeline),
                "plot_summary": request.include_plot_summary and bool(project.memory and project.memory.plot_points)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export book: {str(e)}")


# ==============================================================================
# PHASE 5A: DOCUMENT INTELLIGENCE ENDPOINTS
# ==============================================================================

class UploadDraftResponse(BaseModel):
    """Response from draft upload"""
    upload_id: str
    filename: str
    file_size: int
    file_path: str


class ParseDraftRequest(BaseModel):
    """Request to parse uploaded draft"""
    file_path: str


class ParseDraftResponse(BaseModel):
    """Response with parsed chapters"""
    filename: str
    total_chapters: int
    total_words: int
    chapters: List[dict]
    metadata: dict


class ExtractMemoryRequest(BaseModel):
    """Request to extract memory from parsed document"""
    project_id: str
    author_id: str
    parsed_document: dict  # Serialized ParsedDocument


class ExtractMemoryResponse(BaseModel):
    """Response with extracted memory elements"""
    characters_found: int
    events_found: int
    plots_found: int
    extraction_metadata: dict


class ImportDraftRequest(BaseModel):
    """Request to import draft into project (complete workflow)"""
    project_id: str
    author_id: str
    file_path: str
    auto_extract_memory: bool = True
    overwrite_existing: bool = False


class ImportDraftResponse(BaseModel):
    """Response from draft import"""
    status: str
    chapters_imported: int
    total_words: int
    memory_extraction: Optional[dict] = None


@router.post("/upload-draft", response_model=UploadDraftResponse)
async def upload_draft(file: UploadFile = File(...)):
    """
    Upload document draft for import (Phase 5A)

    Supports DOCX, TXT, PDF, MD formats.
    Returns upload ID and file path for subsequent parsing.
    """
    try:
        # Validate file type
        allowed_extensions = [".docx", ".txt", ".pdf", ".md"]
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )

        # Create uploads directory
        upload_dir = Path("data/author_uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        upload_id = uuid.uuid4().hex[:12]
        unique_filename = f"{upload_id}_{file.filename}"
        file_path = upload_dir / unique_filename

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = file_path.stat().st_size

        return UploadDraftResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            file_path=str(file_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload draft: {str(e)}")


@router.post("/parse-draft", response_model=ParseDraftResponse)
async def parse_draft(request: ParseDraftRequest):
    """
    Parse uploaded draft into chapters (Phase 5A)

    Automatically detects chapter boundaries and splits content.
    Returns structured chapter data for review before import.
    """
    try:
        file_path = Path(request.file_path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Upload file not found")

        # Parse document
        parser = DocumentParser()
        parsed_doc = parser.parse_file(file_path)

        return ParseDraftResponse(
            filename=parsed_doc.filename,
            total_chapters=parsed_doc.total_chapters,
            total_words=parsed_doc.total_words,
            chapters=[
                {
                    "chapter_number": ch.chapter_number,
                    "title": ch.title,
                    "word_count": ch.word_count,
                    "content_preview": ch.content[:200] + "..." if len(ch.content) > 200 else ch.content
                }
                for ch in parsed_doc.chapters
            ],
            metadata=parsed_doc.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse draft: {str(e)}")


@router.post("/extract-memory", response_model=ExtractMemoryResponse)
async def extract_memory(request: ExtractMemoryRequest):
    """
    Extract characters, events, and plots from parsed document (Phase 5A)

    Uses AI to scan document and automatically extract memory elements.
    Returns extracted data for review before importing to project.
    """
    try:
        # TODO: Reconstruct ParsedDocument from dict
        # For now, return placeholder

        return ExtractMemoryResponse(
            characters_found=0,
            events_found=0,
            plots_found=0,
            extraction_metadata={
                "status": "placeholder",
                "message": "Memory extraction coming soon"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract memory: {str(e)}")


@router.post("/import-draft", response_model=ImportDraftResponse)
async def import_draft(request: ImportDraftRequest):
    """
    Import draft into project - complete workflow (Phase 5A)

    Performs full import:
    1. Parse document into chapters
    2. Extract memory elements (characters, events, plots)
    3. Import chapters into project
    4. Save all memory to project

    This is the main endpoint for uploading existing drafts.
    """
    try:
        engine = get_engine()
        project = engine.load_project(request.author_id, request.project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Upload file not found")

        # Step 1: Parse document
        parser = DocumentParser()
        parsed_doc = parser.parse_file(file_path)

        # Step 2: Import chapters
        chapters_imported = 0
        for chapter in parsed_doc.chapters:
            if not request.overwrite_existing and chapter.chapter_number in project.chapters:
                continue  # Skip existing chapters

            project.add_content(
                chapter_num=chapter.chapter_number,
                content=chapter.content,
                update_memory=False  # We'll do batch memory extraction
            )
            chapters_imported += 1

        # Step 3: Extract memory (if enabled)
        memory_result = None
        if request.auto_extract_memory:
            # Create LLM client (auto-detects API keys from env, falls back to placeholder)
            try:
                llm_client = create_llm_client(provider="placeholder")
                # Try to use real LLM if API key available
                import os
                if os.getenv('ANTHROPIC_API_KEY'):
                    llm_client = create_llm_client(provider="anthropic")
                elif os.getenv('OPENAI_API_KEY'):
                    llm_client = create_llm_client(provider="openai")
            except Exception as e:
                logger.warning(f"LLM client creation failed, using placeholder: {e}")
                llm_client = None

            extractor = MemoryExtractor(llm_provider=llm_client)
            extraction = await extractor.extract_from_document(
                parsed_doc=parsed_doc,
                author_id=request.author_id,
                project_name=request.project_id
            )

            # Import extracted memory
            if project.memory:
                for character in extraction.characters:
                    project.memory.add_character(character)

                for event in extraction.events:
                    project.memory.add_event(event)

                for plot_point in extraction.plot_points:
                    project.memory.add_plot_point(plot_point)

            memory_result = {
                "characters": extraction.extraction_metadata['characters_found'],
                "events": extraction.extraction_metadata['events_found'],
                "plots": extraction.extraction_metadata['plots_found']
            }

        # Step 4: Save project
        project.save(engine.data_path)

        return ImportDraftResponse(
            status="success",
            chapters_imported=chapters_imported,
            total_words=parsed_doc.total_words,
            memory_extraction=memory_result
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import draft: {str(e)}")


# ==============================================================================
# PHASE 5B: CONSISTENCY CHECKING
# ==============================================================================

class ConsistencyIssueResponse(BaseModel):
    """Response model for a consistency issue"""
    issue_id: str
    issue_type: str
    severity: str
    title: str
    description: str
    chapters_affected: List[int]
    entities_affected: List[str]
    conflicting_values: Dict[str, str] = {}
    suggestion: Optional[str] = None
    resolved: bool = False


class ConsistencyReportResponse(BaseModel):
    """Response model for consistency report"""
    project_id: str
    author_id: str

    # Issues by severity
    critical_issues: List[ConsistencyIssueResponse]
    warnings: List[ConsistencyIssueResponse]
    info: List[ConsistencyIssueResponse]

    # Statistics
    total_issues: int
    chapters_checked: int
    characters_checked: int
    events_checked: int

    # Metadata
    checked_at: str
    check_duration_ms: float


class RunConsistencyCheckRequest(BaseModel):
    """Request to run consistency check"""
    project_id: str
    author_id: str


@router.post("/consistency-check", response_model=ConsistencyReportResponse)
async def run_consistency_check(request: RunConsistencyCheckRequest):
    """
    Run full consistency check on a project

    Detects:
    - Character attribute contradictions
    - Timeline ordering issues
    - Unresolved plot threads
    - World building inconsistencies
    """
    try:
        # Get project
        project = engine.get_project(
            author_id=request.author_id,
            project_name=request.project_id
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get memory store
        project_path = engine.data_path / request.author_id / project.project_name
        memory_store = MemoryStore(project_path)

        # Run consistency check
        checker = ConsistencyChecker(memory_store)
        report = checker.run_full_check(
            author_id=request.author_id,
            project_id=request.project_id
        )

        # Convert to response model
        def issue_to_response(issue: ConsistencyIssue) -> ConsistencyIssueResponse:
            return ConsistencyIssueResponse(
                issue_id=issue.issue_id,
                issue_type=issue.issue_type.value,
                severity=issue.severity.value,
                title=issue.title,
                description=issue.description,
                chapters_affected=issue.chapters_affected,
                entities_affected=issue.entities_affected,
                conflicting_values=issue.conflicting_values,
                suggestion=issue.suggestion,
                resolved=issue.resolved
            )

        response = ConsistencyReportResponse(
            project_id=report.project_id,
            author_id=report.author_id,
            critical_issues=[issue_to_response(i) for i in report.critical_issues],
            warnings=[issue_to_response(i) for i in report.warnings],
            info=[issue_to_response(i) for i in report.info],
            total_issues=report.total_issues,
            chapters_checked=report.chapters_checked,
            characters_checked=report.characters_checked,
            events_checked=report.events_checked,
            checked_at=report.checked_at.isoformat(),
            check_duration_ms=report.check_duration_ms
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Consistency check failed: {str(e)}"
        )


@router.get("/consistency-summary/{author_id}/{project_id}")
async def get_consistency_summary(author_id: str, project_id: str):
    """
    Get quick consistency summary (issue counts by type)
    """
    try:
        # Get project
        project = engine.get_project(
            author_id=author_id,
            project_name=project_id
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get memory store
        project_path = engine.data_path / author_id / project.project_name
        memory_store = MemoryStore(project_path)

        # Run check
        checker = ConsistencyChecker(memory_store)
        report = checker.run_full_check(
            author_id=author_id,
            project_id=project_id
        )

        # Build summary
        summary = {
            "total_issues": report.total_issues,
            "critical": len(report.critical_issues),
            "warnings": len(report.warnings),
            "info": len(report.info),
            "by_type": {}
        }

        # Count by type
        for issue in report.get_all_issues():
            issue_type = issue.issue_type.value
            if issue_type not in summary["by_type"]:
                summary["by_type"][issue_type] = 0
            summary["by_type"][issue_type] += 1

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get consistency summary: {str(e)}"
        )
