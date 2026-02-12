"""
Screenplay Studio API Routes
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse, Response

from api.schemas.screenplay import (
    CreateProjectRequest,
    UpdateProjectRequest,
    EstimateCostRequest,
    ProjectResponse,
    ProjectListResponse,
    CostEstimateResponse,
    ProgressResponse,
)
from core.screenplay_studio import (
    ScreenplayProject,
    ScreenplayRepository,
    ScreenplayPipeline,
    CostCalculator,
    ProjectStatus,
    ProjectTier,
    VideoProvider,
    Language,
    DialogueBlock,
)
from core.screenplay_studio.agents.screenplay_formatter import ScreenplayFormatterAgent
from core.screenplay_studio.formats.pdf_export import HAS_REPORTLAB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/screenplay", tags=["Screenplay Studio"])

# Initialize repository
repo = ScreenplayRepository()


def get_user_id() -> str:
    """Get current user ID (placeholder - implement with auth)"""
    return "default_user"


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    user_id: str = Depends(get_user_id),
):
    """Create a new screenplay project"""
    project = ScreenplayProject(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=request.title,
        source_type=request.source_type,
        language=Language(request.language.value),
        tier=ProjectTier(request.tier.value),
        video_provider=VideoProvider(request.video_provider.value) if request.video_provider else None,
        source_text=request.source_text,
        status=ProjectStatus.DRAFT,
    )

    # Estimate cost
    estimated_scenes = len(request.source_text) // 2000  # Rough estimate
    estimated_scenes = max(10, min(50, estimated_scenes))

    costs = CostCalculator.estimate_project_cost(
        tier=project.tier,
        estimated_scenes=estimated_scenes,
        video_provider=project.video_provider,
    )
    project.estimated_cost_usd = costs["total"]

    repo.create(project)

    logger.info(f"Created screenplay project: {project.id}")
    return _project_to_response(project)


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_user_id),
):
    """List user's screenplay projects"""
    offset = (page - 1) * page_size
    projects = repo.get_by_user(user_id, limit=page_size, offset=offset)
    total = repo.count_by_user(user_id)

    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Get project by ID"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _project_to_response(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    user_id: str = Depends(get_user_id),
):
    """Update project settings"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if request.title is not None:
        project.title = request.title

    if request.tier is not None:
        project.tier = ProjectTier(request.tier.value)

    if request.video_provider is not None:
        project.video_provider = VideoProvider(request.video_provider.value)

    repo.update(project)

    return _project_to_response(project)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Delete a project"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    repo.delete(project_id)

    return {"message": "Project deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/analyze", response_model=ProgressResponse)
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """Start Phase 1: Story Analysis"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if project.status not in [ProjectStatus.DRAFT, ProjectStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start analysis in {project.status} state"
        )

    # Update status
    project.status = ProjectStatus.ANALYZING
    project.current_phase = 1
    project.progress_percent = 0
    repo.update(project)

    # Start background task
    background_tasks.add_task(_run_analysis, project_id)

    return ProgressResponse(
        project_id=project_id,
        status=project.status,
        current_phase=1,
        progress_percent=0,
        message="Analysis started",
    )


async def _run_analysis(project_id: str):
    """Background task to run story analysis"""
    try:
        project = repo.get(project_id)
        if not project:
            return

        pipeline = ScreenplayPipeline()
        result = await pipeline.analyze(project)

        if result.success:
            project.story_analysis = result.data
            project.status = ProjectStatus.DRAFT  # Ready for next phase
            project.progress_percent = 25
            project.actual_cost_usd += result.cost_usd
        else:
            project.status = ProjectStatus.FAILED
            project.error_message = result.error

        repo.update(project)

    except Exception as e:
        logger.error(f"Analysis failed for {project_id}: {e}")
        project = repo.get(project_id)
        if project:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            repo.update(project)


# ═══════════════════════════════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(request: EstimateCostRequest):
    """Estimate project cost before creation"""

    # Estimate scenes based on text length
    estimated_scenes = request.source_text_length // 2000
    estimated_scenes = max(10, min(50, estimated_scenes))

    # Calculate costs
    tier = ProjectTier(request.tier.value)
    provider = VideoProvider(request.video_provider.value) if request.video_provider else None

    costs = CostCalculator.estimate_project_cost(
        tier=tier,
        estimated_scenes=estimated_scenes,
        video_provider=provider,
    )

    features = CostCalculator.get_tier_features(tier)

    return CostEstimateResponse(
        tier=request.tier,
        estimated_scenes=estimated_scenes,
        estimated_runtime_minutes=request.target_runtime_minutes,
        costs=costs,
        features=features,
    )


@router.get("/providers")
async def list_providers():
    """List available video providers with pricing"""
    return {
        "providers": [
            {
                "id": "pika",
                "name": "Pika Labs",
                "cost_per_second": 0.02,
                "description": "Budget option, good for drafts",
                "max_duration": 4,
            },
            {
                "id": "runway",
                "name": "Runway Gen-3",
                "cost_per_second": 0.05,
                "description": "Balanced quality and cost",
                "max_duration": 10,
            },
            {
                "id": "veo",
                "name": "Google Veo 2",
                "cost_per_second": 0.08,
                "description": "Best quality, cinematic output",
                "max_duration": 16,
            },
        ],
        "tiers": [
            {
                "id": "free",
                "name": "Free",
                "description": "Screenplay generation only",
                "features": ["screenplay", "shot_list"],
            },
            {
                "id": "standard",
                "name": "Standard",
                "description": "Screenplay + storyboard images",
                "features": ["screenplay", "shot_list", "storyboard_images"],
            },
            {
                "id": "pro",
                "name": "Pro",
                "description": "Full video generation",
                "features": ["screenplay", "shot_list", "storyboard_images", "video_generation"],
            },
            {
                "id": "director",
                "name": "Director",
                "description": "Multi-take, editing, music",
                "features": ["screenplay", "shot_list", "storyboard_images", "video_generation", "multi_take", "video_editing", "music_suggestions"],
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENPLAY GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/generate", response_model=ProgressResponse)
async def generate_screenplay(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """
    Generate complete screenplay (Phase 1 + 2).

    This runs the full FREE tier pipeline:
    1. Story Analysis
    2. Scene Breakdown
    3. Dialogue Writing
    4. Action Writing
    5. Formatting
    """
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if project.status not in [ProjectStatus.DRAFT, ProjectStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate in {project.status.value} state"
        )

    # Update status
    project.status = ProjectStatus.WRITING
    project.current_phase = 1
    project.progress_percent = 0
    repo.update(project)

    # Start background task
    background_tasks.add_task(_run_screenplay_generation, project_id)

    return ProgressResponse(
        project_id=project_id,
        status=project.status,
        current_phase=1,
        progress_percent=0,
        message="Screenplay generation started",
    )


async def _run_screenplay_generation(project_id: str):
    """Background task to run full screenplay generation"""
    try:
        project = repo.get(project_id)
        if not project:
            return

        pipeline = ScreenplayPipeline()

        def progress_callback(type_: str, value: int, message: str):
            p = repo.get(project_id)
            if p:
                if type_ == "phase":
                    p.current_phase = value
                elif type_ == "scene":
                    total_scenes = p.story_analysis.estimated_scenes if p.story_analysis else 25
                    p.progress_percent = min(95, (value / total_scenes) * 100)
                repo.update(p)

        result = await pipeline.run_full_screenplay_generation(
            project,
            progress_callback=progress_callback,
        )

        project = repo.get(project_id)  # Refresh

        if result.success:
            project.story_analysis = result.data["story_analysis"]
            project.screenplay = result.data["screenplay"]
            project.status = ProjectStatus.COMPLETED
            project.progress_percent = 100
            project.actual_cost_usd += result.cost_usd
            project.completed_at = datetime.now()

            # Generate export files
            formatter = ScreenplayFormatterAgent()

            fountain_path = f"outputs/screenplay/{project_id}/screenplay.fountain"
            formatter.export_fountain(project.screenplay, fountain_path)
            project.output_files["screenplay_fountain"] = fountain_path

            if HAS_REPORTLAB:
                pdf_path = f"outputs/screenplay/{project_id}/screenplay.pdf"
                formatter.export_pdf(project.screenplay, pdf_path)
                project.output_files["screenplay_pdf"] = pdf_path

        else:
            project.status = ProjectStatus.FAILED
            project.error_message = result.error

        repo.update(project)
        logger.info(f"Screenplay generation complete for {project_id}")

    except Exception as e:
        logger.error(f"Screenplay generation failed for {project_id}: {e}")
        project = repo.get(project_id)
        if project:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            repo.update(project)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/export/fountain")
async def export_fountain(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Download screenplay as .fountain file"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not project.screenplay:
        raise HTTPException(status_code=400, detail="Screenplay not generated yet")

    # Check if file exists
    fountain_path = project.output_files.get("screenplay_fountain")
    if fountain_path and Path(fountain_path).exists():
        return FileResponse(
            fountain_path,
            media_type="text/plain",
            filename=f"{project.title}.fountain"
        )

    # Generate on the fly
    formatter = ScreenplayFormatterAgent()
    content = formatter.get_fountain_content(project.screenplay)

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{project.title}.fountain"'
        }
    )


@router.get("/projects/{project_id}/export/pdf")
async def export_pdf(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Download screenplay as PDF"""
    if not HAS_REPORTLAB:
        raise HTTPException(
            status_code=501,
            detail="PDF export not available (reportlab not installed)"
        )

    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not project.screenplay:
        raise HTTPException(status_code=400, detail="Screenplay not generated yet")

    # Check if file exists
    pdf_path = project.output_files.get("screenplay_pdf")
    if pdf_path and Path(pdf_path).exists():
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{project.title}.pdf"
        )

    # Generate on the fly
    formatter = ScreenplayFormatterAgent()
    pdf_bytes = formatter.get_pdf_bytes(project.screenplay)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{project.title}.pdf"'
        }
    )


@router.get("/projects/{project_id}/screenplay")
async def get_screenplay_content(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Get screenplay content (scenes, dialogue, action)"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not project.screenplay:
        raise HTTPException(status_code=400, detail="Screenplay not generated yet")

    return {
        "title": project.screenplay.title,
        "author": project.screenplay.author,
        "total_pages": project.screenplay.total_pages,
        "total_scenes": len(project.screenplay.scenes),
        "scenes": [
            {
                "scene_number": s.scene_number,
                "heading": str(s.heading),
                "elements": [
                    {
                        "type": "dialogue" if isinstance(e, DialogueBlock) else "action",
                        "content": e.to_dict() if hasattr(e, 'to_dict') else {"text": e.text}
                    }
                    for e in s.elements
                ],
                "page_count": s.page_count,
            }
            for s in project.screenplay.scenes
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS POLLING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/progress", response_model=ProgressResponse)
async def get_progress(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Get current generation progress for a project"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    status_messages = {
        ProjectStatus.DRAFT: "Ready to start",
        ProjectStatus.ANALYZING: "Analyzing story...",
        ProjectStatus.WRITING: "Writing screenplay...",
        ProjectStatus.VISUALIZING: "Creating storyboard...",
        ProjectStatus.RENDERING: "Rendering video...",
        ProjectStatus.COMPLETED: "Complete",
        ProjectStatus.FAILED: project.error_message or "Generation failed",
    }

    return ProgressResponse(
        project_id=project_id,
        status=project.status,
        current_phase=project.current_phase,
        progress_percent=project.progress_percent,
        message=status_messages.get(project.status, "Processing..."),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION & VIDEO RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/visualize", response_model=ProgressResponse)
async def start_visualization(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """Start Phase 3: Pre-Visualization (storyboard generation)"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not project.screenplay:
        raise HTTPException(status_code=400, detail="Screenplay must be generated first")

    if project.tier == ProjectTier.FREE:
        raise HTTPException(status_code=400, detail="Visualization requires Standard tier or above")

    if project.status not in [ProjectStatus.DRAFT, ProjectStatus.COMPLETED, ProjectStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start visualization in {project.status.value} state"
        )

    project.status = ProjectStatus.VISUALIZING
    project.current_phase = 3
    project.progress_percent = 0
    repo.update(project)

    background_tasks.add_task(_run_visualization, project_id)

    return ProgressResponse(
        project_id=project_id,
        status=project.status,
        current_phase=3,
        progress_percent=0,
        message="Visualization started",
    )


async def _run_visualization(project_id: str):
    """Background task to run storyboard generation"""
    try:
        project = repo.get(project_id)
        if not project:
            return

        pipeline = ScreenplayPipeline()
        output_dir = f"outputs/screenplay/{project_id}/storyboard"

        result = await pipeline.run_phase_3(
            project,
            output_dir=output_dir,
        )

        project = repo.get(project_id)

        if result.success:
            project.status = ProjectStatus.COMPLETED
            project.progress_percent = 100
            project.actual_cost_usd += result.cost_usd
            project.output_files["storyboard_pdf"] = f"{output_dir}/storyboard.pdf"
        else:
            project.status = ProjectStatus.FAILED
            project.error_message = result.error

        repo.update(project)

    except Exception as e:
        logger.error(f"Visualization failed for {project_id}: {e}")
        project = repo.get(project_id)
        if project:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            repo.update(project)


@router.post("/projects/{project_id}/render", response_model=ProgressResponse)
async def start_video_rendering(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """Start Phase 4: Video Rendering"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if project.tier not in [ProjectTier.PRO, ProjectTier.DIRECTOR]:
        raise HTTPException(status_code=400, detail="Video rendering requires Pro tier or above")

    if not project.screenplay:
        raise HTTPException(status_code=400, detail="Screenplay must be generated first")

    if project.status not in [ProjectStatus.DRAFT, ProjectStatus.COMPLETED, ProjectStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start rendering in {project.status.value} state"
        )

    project.status = ProjectStatus.RENDERING
    project.current_phase = 4
    project.progress_percent = 0
    repo.update(project)

    background_tasks.add_task(_run_video_rendering, project_id)

    return ProgressResponse(
        project_id=project_id,
        status=project.status,
        current_phase=4,
        progress_percent=0,
        message="Video rendering started",
    )


async def _run_video_rendering(project_id: str):
    """Background task to run video rendering"""
    try:
        project = repo.get(project_id)
        if not project:
            return

        pipeline = ScreenplayPipeline()
        output_dir = f"outputs/screenplay/{project_id}/video"
        provider = project.video_provider or VideoProvider.RUNWAY

        result = await pipeline.run_phase_4(
            project,
            provider=provider,
            output_dir=output_dir,
        )

        project = repo.get(project_id)

        if result.success:
            project.status = ProjectStatus.COMPLETED
            project.progress_percent = 100
            project.actual_cost_usd += result.cost_usd
            project.output_files["video_final"] = f"{output_dir}/final.mp4"
        else:
            project.status = ProjectStatus.FAILED
            project.error_message = result.error

        repo.update(project)

    except Exception as e:
        logger.error(f"Video rendering failed for {project_id}: {e}")
        project = repo.get(project_id)
        if project:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            repo.update(project)


@router.get("/projects/{project_id}/export/storyboard-pdf")
async def export_storyboard_pdf(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Download storyboard as PDF"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    storyboard_path = project.output_files.get("storyboard_pdf")
    if not storyboard_path or not Path(storyboard_path).exists():
        raise HTTPException(status_code=404, detail="Storyboard PDF not available")

    return FileResponse(
        storyboard_path,
        media_type="application/pdf",
        filename=f"{project.title} - Storyboard.pdf"
    )


@router.get("/projects/{project_id}/export/video")
async def export_video(
    project_id: str,
    user_id: str = Depends(get_user_id),
):
    """Download final rendered video"""
    project = repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    video_path = project.output_files.get("video_final")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video not available")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{project.title}.mp4"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _project_to_response(project: ScreenplayProject) -> ProjectResponse:
    """Convert project model to API response"""
    from api.schemas.screenplay import (
        ProjectResponse, StoryAnalysisResponse, ScreenplayResponse,
        CharacterResponse, SceneResponse, ProjectStatusEnum,
        ProjectTierEnum, VideoProviderEnum, LanguageEnum
    )

    story_analysis = None
    if project.story_analysis:
        sa = project.story_analysis
        story_analysis = StoryAnalysisResponse(
            title=sa.title,
            logline=sa.logline,
            synopsis=sa.synopsis,
            genre=sa.genre,
            sub_genres=sa.sub_genres,
            tone=sa.tone,
            themes=sa.themes,
            setting=sa.setting,
            time_period=sa.time_period,
            characters=[
                CharacterResponse(
                    name=c.name,
                    description=c.description,
                    role=c.role,
                    arc=c.arc,
                    traits=c.traits,
                    visual_description=c.visual_description,
                    age_range=c.age_range,
                    gender=c.gender,
                )
                for c in sa.characters
            ],
            estimated_runtime_minutes=sa.estimated_runtime_minutes,
            estimated_scenes=sa.estimated_scenes,
        )

    screenplay = None
    if project.screenplay:
        sp = project.screenplay
        screenplay = ScreenplayResponse(
            title=sp.title,
            author=sp.author,
            genre=sp.genre,
            logline=sp.logline,
            total_pages=sp.total_pages,
            total_runtime_minutes=sp.total_runtime_minutes,
            scenes=[
                SceneResponse(
                    scene_number=s.scene_number,
                    heading=str(s.heading),
                    summary=s.summary,
                    characters_present=s.characters_present,
                    emotional_beat=s.emotional_beat,
                    page_count=s.page_count,
                    mood=s.mood,
                )
                for s in sp.scenes
            ],
        )

    return ProjectResponse(
        id=project.id,
        title=project.title,
        source_type=project.source_type,
        language=LanguageEnum(project.language.value),
        tier=ProjectTierEnum(project.tier.value),
        video_provider=VideoProviderEnum(project.video_provider.value) if project.video_provider else None,
        status=ProjectStatusEnum(project.status.value),
        current_phase=project.current_phase,
        progress_percent=project.progress_percent,
        error_message=project.error_message,
        story_analysis=story_analysis,
        screenplay=screenplay,
        estimated_cost_usd=project.estimated_cost_usd,
        actual_cost_usd=project.actual_cost_usd,
        created_at=project.created_at,
        updated_at=project.updated_at,
        completed_at=project.completed_at,
        output_files=project.output_files,
    )
