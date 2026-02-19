"use client";

import { GenerationProgress } from "@/lib/screenplay/types";
import { PHASE_NAMES } from "@/lib/screenplay/constants";

interface RenderProgressProps {
  progress: GenerationProgress | null;
  isActive: boolean;
}

export function RenderProgress({ progress, isActive }: RenderProgressProps) {
  if (!isActive || !progress) return null;

  const phaseName = PHASE_NAMES[progress.current_phase] || "Processing";

  return (
    <div className="screenplay-render-progress">
      <div className="screenplay-render-header">
        <span className="screenplay-render-phase">{phaseName}</span>
        <span className="screenplay-render-percent">
          {Math.round(progress.progress_percent)}%
        </span>
      </div>

      <div className="screenplay-progress-bar screenplay-progress-bar-lg">
        <div
          className="screenplay-progress-fill screenplay-progress-animated"
          style={{ width: `${progress.progress_percent}%` }}
        />
      </div>

      {progress.message && (
        <p className="screenplay-render-message">{progress.message}</p>
      )}

      {progress.estimated_time_remaining != null &&
        progress.estimated_time_remaining > 0 && (
          <p className="screenplay-render-eta">
            Estimated time remaining:{" "}
            {Math.ceil(progress.estimated_time_remaining / 60)} min
          </p>
        )}
    </div>
  );
}
