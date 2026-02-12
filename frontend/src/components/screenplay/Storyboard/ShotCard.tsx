"use client";

import { Shot } from "@/lib/screenplay/types";

interface ShotCardProps {
  shot: Shot;
  onClick?: () => void;
}

export function ShotCard({ shot, onClick }: ShotCardProps) {
  return (
    <div className="screenplay-shot-card" onClick={onClick}>
      <div className="screenplay-shot-image">
        {shot.storyboard_image ? (
          <img
            src={shot.storyboard_image}
            alt={`Shot ${shot.shot_number}`}
            loading="lazy"
          />
        ) : (
          <div className="screenplay-shot-placeholder">
            <span>No image</span>
          </div>
        )}
      </div>
      <div className="screenplay-shot-info">
        <span className="screenplay-shot-number">Shot {shot.shot_number}</span>
        <span className="screenplay-shot-type">{shot.shot_type}</span>
        <span className="screenplay-shot-duration">
          {shot.duration_seconds}s
        </span>
      </div>
      <p className="screenplay-shot-desc">{shot.description}</p>
    </div>
  );
}
