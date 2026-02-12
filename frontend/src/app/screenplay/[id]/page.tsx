"use client";

import { use } from "react";
import Link from "next/link";
import { useProject } from "@/hooks/screenplay/useProject";
import { useGeneration } from "@/hooks/screenplay/useGeneration";
import { ScriptEditor } from "@/components/screenplay/Editor/ScriptEditor";
import { StoryboardViewer } from "@/components/screenplay/Storyboard/StoryboardViewer";
import { VideoPlayer } from "@/components/screenplay/Video/VideoPlayer";
import { RenderProgress } from "@/components/screenplay/Video/RenderProgress";
import { ExportPanel } from "@/components/screenplay/Export/ExportPanel";
import { TIER_INFO, STATUS_COLORS, PHASE_NAMES } from "@/lib/screenplay/constants";
import "@/styles/screenplay.css";

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const {
    project,
    loading,
    error,
    refresh,
    analyze,
    generate,
    visualize,
    renderVideo,
    isProcessing,
  } = useProject(id);

  const {
    progress,
    isActive: isPolling,
    start: startPolling,
    stop: stopPolling,
  } = useGeneration(id, {
    onComplete: refresh,
  });

  if (loading) {
    return (
      <div className="screenplay-loading">
        <div className="screenplay-spinner-lg" />
        <p>Loading project...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="screenplay-error">
        <h2>Error</h2>
        <p>{error || "Project not found"}</p>
        <Link href="/screenplay" className="screenplay-btn">
          Back to Projects
        </Link>
      </div>
    );
  }

  const tier = TIER_INFO[project.tier];
  const statusColor = STATUS_COLORS[project.status] || "gray";

  const handleAction = async (action: () => Promise<void>) => {
    try {
      await action();
      startPolling();
    } catch {
      // Error is set in the hook
    }
  };

  return (
    <div className="screenplay-page">
      <div className="screenplay-page-header">
        <Link href="/screenplay" className="screenplay-back-link">
          &larr; Back to Projects
        </Link>
        <div className="screenplay-project-header">
          <h1>{project.title}</h1>
          <div className="screenplay-project-badges">
            <span className={`screenplay-badge screenplay-badge-${tier.color}`}>
              {tier.name}
            </span>
            <span className={`screenplay-status screenplay-status-${statusColor}`}>
              {isProcessing && <span className="screenplay-spinner" />}
              {project.status}
            </span>
            <span className="screenplay-phase-badge">
              {PHASE_NAMES[project.current_phase]}
            </span>
          </div>
        </div>
      </div>

      {(isProcessing || isPolling) && (
        <RenderProgress progress={progress} isActive={isPolling} />
      )}

      <div className="screenplay-project-actions">
        {project.current_phase === 0 && (
          <button
            className="screenplay-btn screenplay-btn-primary"
            disabled={isProcessing}
            onClick={() => handleAction(analyze)}
          >
            Start Analysis
          </button>
        )}
        {project.current_phase === 1 && project.status === "completed" && (
          <button
            className="screenplay-btn screenplay-btn-primary"
            disabled={isProcessing}
            onClick={() => handleAction(generate)}
          >
            Generate Screenplay
          </button>
        )}
        {project.current_phase === 2 &&
          project.status === "completed" &&
          project.tier !== "free" && (
            <button
              className="screenplay-btn screenplay-btn-primary"
              disabled={isProcessing}
              onClick={() => handleAction(visualize)}
            >
              Create Storyboard
            </button>
          )}
        {project.current_phase === 3 &&
          project.status === "completed" &&
          (project.tier === "pro" || project.tier === "director") && (
            <button
              className="screenplay-btn screenplay-btn-primary"
              disabled={isProcessing}
              onClick={() => handleAction(renderVideo)}
            >
              Render Video
            </button>
          )}
      </div>

      {project.story_analysis && (
        <div className="screenplay-analysis-summary">
          <h3>Story Analysis</h3>
          <div className="screenplay-analysis-grid">
            <div>
              <span className="screenplay-detail-label">Genre</span>
              <span>{project.story_analysis.genre}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Tone</span>
              <span>{project.story_analysis.tone}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Setting</span>
              <span>{project.story_analysis.setting}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Runtime</span>
              <span>{project.story_analysis.estimated_runtime_minutes} min</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Scenes</span>
              <span>{project.story_analysis.estimated_scenes}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Characters</span>
              <span>{project.story_analysis.characters.length}</span>
            </div>
          </div>
          <p className="screenplay-logline">{project.story_analysis.logline}</p>
        </div>
      )}

      {project.screenplay && (
        <ScriptEditor screenplay={project.screenplay} />
      )}

      {project.shot_lists && project.shot_lists.length > 0 && (
        <StoryboardViewer shotLists={project.shot_lists} />
      )}

      {project.final_video && (
        <VideoPlayer projectId={project.id} finalVideo={project.final_video} />
      )}

      <ExportPanel project={project} />

      {project.error_message && (
        <div className="screenplay-error-banner">
          <p>{project.error_message}</p>
        </div>
      )}
    </div>
  );
}
