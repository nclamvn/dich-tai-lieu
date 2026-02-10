"use client";

import { useState, useCallback, useEffect } from "react";
import { ReaderProvider, useReaderSettings } from "./reader-context";
import { ReaderToolbar } from "./reader-toolbar";
import { ReaderSidebar } from "./reader-sidebar";
import { ReaderContentArea } from "./reader-content";
import { ReaderProgress } from "./reader-progress";
import type { ReaderContent } from "@/lib/api/types";

interface ReaderLayoutProps {
  content: ReaderContent;
  downloadUrl?: string;
}

function ReaderInner({ content, downloadUrl }: ReaderLayoutProps) {
  const { fullscreen } = useReaderSettings();
  const [currentChapter, setCurrentChapter] = useState(0);
  const [chapterProgress, setChapterProgress] = useState(0);

  const chapters = content.chapters;
  const totalChapters = chapters.length;

  const globalProgress =
    totalChapters > 0
      ? Math.round(
          ((currentChapter + chapterProgress / 100) / totalChapters) * 100,
        )
      : 0;

  const goToChapter = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalChapters) setCurrentChapter(index);
    },
    [totalChapters],
  );

  const prevChapter = useCallback(
    () => goToChapter(currentChapter - 1),
    [currentChapter, goToChapter],
  );
  const nextChapter = useCallback(
    () => goToChapter(currentChapter + 1),
    [currentChapter, goToChapter],
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          prevChapter();
          break;
        case "ArrowRight":
          e.preventDefault();
          nextChapter();
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [prevChapter, nextChapter]);

  // Save/restore reading position
  useEffect(() => {
    const key = `aipub-reader-pos-${content.job_id}`;
    try {
      const saved = localStorage.getItem(key);
      if (saved) {
        const pos = JSON.parse(saved);
        if (pos.chapter >= 0 && pos.chapter < totalChapters) {
          setCurrentChapter(pos.chapter);
        }
      }
    } catch {
      /* ignore */
    }
  }, [content.job_id, totalChapters]);

  useEffect(() => {
    const key = `aipub-reader-pos-${content.job_id}`;
    try {
      localStorage.setItem(key, JSON.stringify({ chapter: currentChapter }));
    } catch {
      /* ignore */
    }
  }, [content.job_id, currentChapter]);

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={
        fullscreen
          ? { position: "fixed", inset: 0, zIndex: 100 }
          : undefined
      }
    >
      <ReaderToolbar
        jobId={content.job_id}
        title={content.title}
        currentChapter={currentChapter}
        totalChapters={totalChapters}
        onPrevChapter={prevChapter}
        onNextChapter={nextChapter}
        downloadUrl={downloadUrl}
      />
      <ReaderProgress globalProgress={globalProgress} />
      <div className="flex flex-1 overflow-hidden">
        <ReaderSidebar
          chapters={chapters}
          currentChapter={currentChapter}
          onSelectChapter={goToChapter}
          quality={content.quality}
          metadata={content.metadata}
        />
        <ReaderContentArea
          chapters={chapters}
          currentChapter={currentChapter}
          onProgressChange={setChapterProgress}
        />
      </div>
    </div>
  );
}

export function ReaderLayout(props: ReaderLayoutProps) {
  return (
    <ReaderProvider>
      <ReaderInner {...props} />
    </ReaderProvider>
  );
}
