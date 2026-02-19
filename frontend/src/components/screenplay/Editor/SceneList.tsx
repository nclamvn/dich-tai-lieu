"use client";

import { Scene } from "@/lib/screenplay/types";

interface SceneListProps {
  scenes: Scene[];
  selectedScene: number | null;
  onSelectScene: (sceneNumber: number) => void;
}

export function SceneList({
  scenes,
  selectedScene,
  onSelectScene,
}: SceneListProps) {
  return (
    <div className="screenplay-scene-list">
      <h3 className="screenplay-scene-list-title">Scenes</h3>
      <div className="screenplay-scene-list-items">
        {scenes.map((scene) => (
          <button
            key={scene.scene_number}
            className={`screenplay-scene-item ${
              selectedScene === scene.scene_number ? "active" : ""
            }`}
            onClick={() => onSelectScene(scene.scene_number)}
          >
            <span className="screenplay-scene-item-number">
              {scene.scene_number}
            </span>
            <div className="screenplay-scene-item-info">
              <span className="screenplay-scene-item-slug">
                {scene.heading.int_ext}. {scene.heading.location}
              </span>
              <span className="screenplay-scene-item-time">
                {scene.heading.time}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
