"use client";

import { FileText, FileDown, Image, Clapperboard } from "lucide-react";
import { ScreenplayProject } from "@/lib/screenplay/types";
import {
  getFountainUrl,
  getPdfUrl,
  getStoryboardPdfUrl,
  getVideoUrl,
} from "@/lib/screenplay/api";
import { DownloadButton } from "./DownloadButton";

interface ExportPanelProps {
  project: ScreenplayProject;
}

export function ExportPanel({ project }: ExportPanelProps) {
  const hasScreenplay = project.current_phase >= 2;
  const hasStoryboard = project.current_phase >= 3;
  const hasVideo = project.current_phase >= 4 && !!project.final_video;

  return (
    <div className="screenplay-export-panel">
      <h3>Export</h3>

      <div className="screenplay-export-grid">
        <div className="screenplay-export-section">
          <h4>Screenplay</h4>
          <div className="screenplay-export-buttons">
            <DownloadButton
              href={getFountainUrl(project.id)}
              label="Fountain (.fountain)"
              icon={<FileText size={16} strokeWidth={1.5} />}
              disabled={!hasScreenplay}
            />
            <DownloadButton
              href={getPdfUrl(project.id)}
              label="PDF"
              icon={<FileDown size={16} strokeWidth={1.5} />}
              disabled={!hasScreenplay}
            />
          </div>
        </div>

        <div className="screenplay-export-section">
          <h4>Storyboard</h4>
          <div className="screenplay-export-buttons">
            <DownloadButton
              href={getStoryboardPdfUrl(project.id)}
              label="Storyboard PDF"
              icon={<Image size={16} strokeWidth={1.5} />}
              disabled={!hasStoryboard}
            />
          </div>
        </div>

        {(project.tier === "pro" || project.tier === "director") && (
          <div className="screenplay-export-section">
            <h4>Video</h4>
            <div className="screenplay-export-buttons">
              <DownloadButton
                href={getVideoUrl(project.id)}
                label="Final Video"
                icon={<Clapperboard size={16} strokeWidth={1.5} />}
                disabled={!hasVideo}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
