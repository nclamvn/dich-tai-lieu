"use client";

import { Scene } from "@/lib/screenplay/types";
import { DialogueBlock } from "./DialogueBlock";
import { ActionBlock } from "./ActionBlock";

interface ScenePanelProps {
  scene: Scene;
}

function isDialogue(
  el: Scene["elements"][number]
): el is { character: string; dialogue: string; parenthetical?: string } {
  return "character" in el && "dialogue" in el;
}

export function ScenePanel({ scene }: ScenePanelProps) {
  return (
    <div className="screenplay-scene-panel">
      <div className="screenplay-scene-heading">
        <span className="screenplay-scene-number">
          {scene.scene_number}.
        </span>
        <span className="screenplay-scene-slug">
          {scene.heading.int_ext}. {scene.heading.location} -{" "}
          {scene.heading.time}
        </span>
      </div>

      <div className="screenplay-scene-meta">
        <span className="screenplay-emotional-beat">
          {scene.emotional_beat}
        </span>
        {scene.characters_present?.length > 0 && (
          <span className="screenplay-scene-characters">
            {scene.characters_present.join(", ")}
          </span>
        )}
        {scene.page_count && (
          <span className="screenplay-page-count">
            {scene.page_count} {scene.page_count === 1 ? "page" : "pages"}
          </span>
        )}
      </div>

      <p className="screenplay-scene-summary">{scene.summary}</p>

      {scene.elements && scene.elements.length > 0 && (
        <div className="screenplay-elements">
          {scene.elements.map((el, i) =>
            isDialogue(el) ? (
              <DialogueBlock key={i} block={el} />
            ) : (
              <ActionBlock key={i} block={el as { text: string }} />
            )
          )}
        </div>
      )}
    </div>
  );
}
