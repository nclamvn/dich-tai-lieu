"use client";

import Link from "next/link";
import { ScreenplayProject } from "@/lib/screenplay/types";
import { TIER_INFO, STATUS_COLORS, PHASE_NAMES } from "@/lib/screenplay/constants";

function timeAgo(dateStr: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 1000
  );
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

interface ProjectCardProps {
  project: ScreenplayProject;
  onDelete?: (id: string) => void;
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const tier = TIER_INFO[project.tier];
  const statusColor = STATUS_COLORS[project.status] || "gray";
  const phaseName = PHASE_NAMES[project.current_phase] || "Unknown";
  const isProcessing = ["analyzing", "writing", "visualizing", "rendering"].includes(
    project.status
  );

  return (
    <div className="screenplay-card">
      <div className="screenplay-card-header">
        <div className="screenplay-card-title-row">
          <Link
            href={`/screenplay/${project.id}`}
            className="screenplay-card-title"
          >
            {project.title || "Untitled Project"}
          </Link>
          <span className={`screenplay-badge screenplay-badge-${tier.color}`}>
            {tier.name}
          </span>
        </div>
        <div className="screenplay-card-meta">
          <span className={`screenplay-status screenplay-status-${statusColor}`}>
            {isProcessing && (
              <span className="screenplay-spinner" />
            )}
            {project.status}
          </span>
          <span className="screenplay-card-phase">{phaseName}</span>
          <span className="screenplay-card-time">
            {timeAgo(project.updated_at)}
          </span>
        </div>
      </div>

      {isProcessing && (
        <div className="screenplay-progress-bar">
          <div
            className="screenplay-progress-fill"
            style={{ width: `${project.progress_percent}%` }}
          />
        </div>
      )}

      {project.story_analysis && (
        <p className="screenplay-card-logline">
          {project.story_analysis.logline}
        </p>
      )}

      <div className="screenplay-card-footer">
        <div className="screenplay-card-stats">
          {project.screenplay && (
            <span>{project.screenplay.total_pages} pages</span>
          )}
          {project.story_analysis && (
            <span>{project.story_analysis.genre}</span>
          )}
          {project.actual_cost_usd > 0 && (
            <span>${project.actual_cost_usd.toFixed(2)}</span>
          )}
        </div>
        <div className="screenplay-card-actions">
          <Link
            href={`/screenplay/${project.id}`}
            className="screenplay-btn screenplay-btn-sm"
          >
            Open
          </Link>
          {onDelete && project.status !== "analyzing" && (
            <button
              className="screenplay-btn screenplay-btn-sm screenplay-btn-danger"
              onClick={(e) => {
                e.preventDefault();
                if (confirm("Delete this project?")) {
                  onDelete(project.id);
                }
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
