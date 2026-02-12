"use client";

import { useState } from "react";
import { ShotList } from "@/lib/screenplay/types";
import { ShotCard } from "./ShotCard";
import { ShotDetail } from "./ShotDetail";

interface ShotGridProps {
  shotList: ShotList;
}

export function ShotGrid({ shotList }: ShotGridProps) {
  const [selectedShot, setSelectedShot] = useState<number | null>(null);

  const selected = selectedShot !== null
    ? shotList.shots[selectedShot]
    : null;

  return (
    <div className="screenplay-shot-grid-container">
      <div className="screenplay-shot-grid-header">
        <h4>Scene {shotList.scene_number}</h4>
        <span className="screenplay-shot-count">
          {shotList.shots.length} shots
        </span>
        {shotList.visual_style && (
          <span className="screenplay-visual-style">{shotList.visual_style}</span>
        )}
      </div>

      <div className="screenplay-shot-grid">
        {shotList.shots.map((shot, i) => (
          <ShotCard
            key={shot.shot_number}
            shot={shot}
            onClick={() => setSelectedShot(i)}
          />
        ))}
      </div>

      {selected && (
        <ShotDetail
          shot={selected}
          onClose={() => setSelectedShot(null)}
        />
      )}
    </div>
  );
}
