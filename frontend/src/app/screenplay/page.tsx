"use client";

import { ProjectList } from "@/components/screenplay/Dashboard/ProjectList";
import "@/styles/screenplay.css";

export default function ScreenplayPage() {
  return (
    <div className="screenplay-page">
      <div className="screenplay-page-header">
        <h1>Screenplay Studio</h1>
        <p>Transform stories into screenplays, storyboards, and videos.</p>
      </div>
      <ProjectList />
    </div>
  );
}
