"use client";

import { Shot } from "@/lib/screenplay/types";

interface ShotDetailProps {
  shot: Shot;
  onClose: () => void;
}

export function ShotDetail({ shot, onClose }: ShotDetailProps) {
  return (
    <div className="screenplay-shot-detail-overlay" onClick={onClose}>
      <div
        className="screenplay-shot-detail"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="screenplay-shot-detail-close" onClick={onClose}>
          &times;
        </button>

        <div className="screenplay-shot-detail-image">
          {shot.storyboard_image ? (
            <img src={shot.storyboard_image} alt={`Shot ${shot.shot_number}`} />
          ) : (
            <div className="screenplay-shot-placeholder-lg">No image</div>
          )}
        </div>

        <div className="screenplay-shot-detail-info">
          <h3>Shot {shot.shot_number}</h3>

          <div className="screenplay-shot-detail-grid">
            <div>
              <span className="screenplay-detail-label">Type</span>
              <span>{shot.shot_type}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Angle</span>
              <span>{shot.camera_angle}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Movement</span>
              <span>{shot.camera_movement}</span>
            </div>
            <div>
              <span className="screenplay-detail-label">Duration</span>
              <span>{shot.duration_seconds}s</span>
            </div>
          </div>

          <div className="screenplay-shot-detail-description">
            <span className="screenplay-detail-label">Description</span>
            <p>{shot.description}</p>
          </div>

          {shot.ai_prompt && (
            <div className="screenplay-shot-detail-prompt">
              <span className="screenplay-detail-label">AI Prompt</span>
              <pre>{shot.ai_prompt}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
