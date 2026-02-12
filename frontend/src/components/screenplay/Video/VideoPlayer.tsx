"use client";

import { getVideoUrl } from "@/lib/screenplay/api";

interface VideoPlayerProps {
  projectId: string;
  finalVideo?: string;
}

export function VideoPlayer({ projectId, finalVideo }: VideoPlayerProps) {
  if (!finalVideo) {
    return (
      <div className="screenplay-empty">
        <p>No video available. Complete video rendering first.</p>
      </div>
    );
  }

  return (
    <div className="screenplay-video-player">
      <video
        className="screenplay-video"
        controls
        preload="metadata"
        src={getVideoUrl(projectId)}
      >
        Your browser does not support video playback.
      </video>
    </div>
  );
}
