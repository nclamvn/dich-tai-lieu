"use client";

import { useEffect, useRef, useCallback } from "react";
import { useReaderSettings } from "./reader-context";
import { RegionRenderer } from "./reader-regions";
import type { ReaderChapter, ReaderTheme } from "@/lib/api/types";

interface ReaderContentProps {
  chapters: ReaderChapter[];
  currentChapter: number;
  onProgressChange: (progress: number) => void;
}

const FONT_SIZE_MAP = ["14px", "15px", "17px", "19px", "22px"];

const THEME_STYLES: Record<
  ReaderTheme,
  { bg: string; text: string; textSecondary: string }
> = {
  light: {
    bg: "#FFFFFF",
    text: "rgb(55, 53, 47)",
    textSecondary: "rgba(55, 53, 47, 0.65)",
  },
  sepia: {
    bg: "#F4EEDD",
    text: "#433422",
    textSecondary: "#5F4B32",
  },
  dark: {
    bg: "#1A1A1A",
    text: "rgba(255, 255, 255, 0.86)",
    textSecondary: "rgba(255, 255, 255, 0.55)",
  },
};

export function ReaderContentArea({
  chapters,
  currentChapter,
  onProgressChange,
}: ReaderContentProps) {
  const { theme, font, fontSize } = useReaderSettings();
  const contentRef = useRef<HTMLDivElement>(null);
  const themeStyle = THEME_STYLES[theme];
  const chapter = chapters[currentChapter];

  const handleScroll = useCallback(() => {
    const el = contentRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const maxScroll = scrollHeight - clientHeight;
    if (maxScroll <= 0) {
      onProgressChange(100);
      return;
    }
    onProgressChange(
      Math.min(100, Math.max(0, Math.round((scrollTop / maxScroll) * 100))),
    );
  }, [onProgressChange]);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  // Scroll to top on chapter change
  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
    onProgressChange(0);
  }, [currentChapter, onProgressChange]);

  if (!chapter) return null;

  return (
    <div
      ref={contentRef}
      className="reader-content flex-1 overflow-y-auto"
      style={{
        backgroundColor: themeStyle.bg,
        color: themeStyle.text,
        transition: "background-color 300ms, color 300ms",
      }}
    >
      <div
        className="max-w-[680px] mx-auto px-6 md:px-10 lg:px-16 pt-12 pb-24"
        style={{
          fontSize: FONT_SIZE_MAP[fontSize],
          fontFamily:
            font === "serif"
              ? "'Instrument Serif', Georgia, 'Times New Roman', serif"
              : "ui-sans-serif, system-ui, -apple-system, sans-serif",
        }}
      >
        {/* Chapter header */}
        <header className="mb-10">
          <p
            className="text-[0.7em] font-medium uppercase tracking-[0.15em] mb-3"
            style={{ color: themeStyle.textSecondary }}
          >
            Chapter {currentChapter + 1} of {chapters.length}
          </p>
          <h1
            className="text-[2em] leading-[1.15] tracking-[-0.02em]"
            style={{
              fontWeight: font === "serif" ? 400 : 700,
              fontFamily:
                font === "serif"
                  ? "'Instrument Serif', Georgia, serif"
                  : "inherit",
            }}
          >
            {chapter.title}
          </h1>
          <div
            className="mt-6 w-12 h-[2px] rounded-full"
            style={{ backgroundColor: `${themeStyle.text}20` }}
          />
        </header>

        {/* Regions */}
        <article className="leading-[1.8]">
          {chapter.regions.map((region, i) => (
            <RegionRenderer key={i} region={region} font={font} />
          ))}
        </article>

        {/* Chapter end */}
        <footer
          className="mt-16 pt-8 text-center"
          style={{ borderTop: `1px solid ${themeStyle.text}15` }}
        >
          <p className="text-[0.75em] opacity-30 uppercase tracking-widest">
            {currentChapter < chapters.length - 1
              ? "End of chapter"
              : "End of document"}
          </p>
        </footer>
      </div>
    </div>
  );
}
