"use client";

import { useState } from "react";
import { Screenplay } from "@/lib/screenplay/types";
import { SceneList } from "./SceneList";
import { ScenePanel } from "./ScenePanel";

interface ScriptEditorProps {
  screenplay: Screenplay;
}

export function ScriptEditor({ screenplay }: ScriptEditorProps) {
  const [selectedScene, setSelectedScene] = useState<number | null>(
    screenplay.scenes.length > 0 ? screenplay.scenes[0].scene_number : null
  );

  const currentScene = screenplay.scenes.find(
    (s) => s.scene_number === selectedScene
  );

  return (
    <div className="screenplay-editor">
      <div className="screenplay-editor-header">
        <div>
          <h2 className="screenplay-editor-title">{screenplay.title}</h2>
          <p className="screenplay-editor-meta">
            by {screenplay.author} &middot; {screenplay.total_pages} pages
            &middot; {screenplay.genre}
          </p>
        </div>
        {screenplay.logline && (
          <p className="screenplay-editor-logline">{screenplay.logline}</p>
        )}
      </div>

      <div className="screenplay-editor-body">
        <SceneList
          scenes={screenplay.scenes}
          selectedScene={selectedScene}
          onSelectScene={setSelectedScene}
        />

        <div className="screenplay-editor-content">
          {currentScene ? (
            <ScenePanel scene={currentScene} />
          ) : (
            <div className="screenplay-empty-scene">
              <p>Select a scene to view</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
