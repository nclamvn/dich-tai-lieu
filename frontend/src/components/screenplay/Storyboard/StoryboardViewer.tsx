"use client";

import { useState } from "react";
import { ShotList } from "@/lib/screenplay/types";
import { ShotGrid } from "./ShotGrid";

interface StoryboardViewerProps {
  shotLists: ShotList[];
}

export function StoryboardViewer({ shotLists }: StoryboardViewerProps) {
  const [selectedScene, setSelectedScene] = useState<number>(0);

  if (shotLists.length === 0) {
    return (
      <div className="screenplay-empty">
        <p>No storyboard data available. Run visualization first.</p>
      </div>
    );
  }

  return (
    <div className="screenplay-storyboard">
      <div className="screenplay-storyboard-nav">
        <h3>Storyboard</h3>
        <div className="screenplay-storyboard-tabs">
          {shotLists.map((sl, i) => (
            <button
              key={sl.scene_number}
              className={`screenplay-storyboard-tab ${
                selectedScene === i ? "active" : ""
              }`}
              onClick={() => setSelectedScene(i)}
            >
              Scene {sl.scene_number}
            </button>
          ))}
        </div>
      </div>

      <ShotGrid shotList={shotLists[selectedScene]} />
    </div>
  );
}
