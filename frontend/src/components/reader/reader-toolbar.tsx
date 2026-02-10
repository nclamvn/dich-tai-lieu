"use client";

import { useReaderSettings } from "./reader-context";
import {
  ArrowLeft,
  PanelLeftClose,
  PanelLeft,
  Sun,
  Moon,
  BookOpen,
  Maximize,
  Minimize,
  Minus,
  Plus,
  Download,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import type { ReaderTheme } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n";

interface ReaderToolbarProps {
  jobId: string;
  title: string;
  currentChapter: number;
  totalChapters: number;
  onPrevChapter: () => void;
  onNextChapter: () => void;
  downloadUrl?: string;
}

const THEME_ICONS = { light: Sun, sepia: BookOpen, dark: Moon };
const THEME_ORDER: ReaderTheme[] = ["light", "sepia", "dark"];
const FONT_SIZE_LABELS = ["XS", "S", "M", "L", "XL"];

const TOOLBAR_BG: Record<ReaderTheme, string> = {
  light: "var(--bg-primary)",
  sepia: "#F4EEDD",
  dark: "#1F1F1F",
};
const TOOLBAR_BORDER: Record<ReaderTheme, string> = {
  light: "var(--border-default)",
  sepia: "#D4C9B0",
  dark: "#333",
};
const TOOLBAR_FG: Record<ReaderTheme, string> = {
  light: "var(--fg-secondary)",
  sepia: "#5F4B32",
  dark: "#ABABAB",
};

export function ReaderToolbar({
  jobId,
  title,
  currentChapter,
  totalChapters,
  onPrevChapter,
  onNextChapter,
  downloadUrl,
}: ReaderToolbarProps) {
  const {
    theme,
    setTheme,
    font,
    setFont,
    fontSize,
    increaseFontSize,
    decreaseFontSize,
    sidebarOpen,
    toggleSidebar,
    fullscreen,
    toggleFullscreen,
  } = useReaderSettings();
  const { t } = useLocale();

  const btnCls =
    "p-1.5 rounded transition-colors hover:opacity-70 cursor-pointer";

  const ThemeIcon = THEME_ICONS[theme];

  return (
    <header
      className="h-11 flex items-center justify-between px-3 gap-2 shrink-0 select-none"
      style={{
        background: TOOLBAR_BG[theme],
        borderBottom: `1px solid ${TOOLBAR_BORDER[theme]}`,
        color: TOOLBAR_FG[theme],
        transition: "background 200ms, border-color 200ms, color 200ms",
      }}
    >
      {/* Left: Back + Sidebar toggle */}
      <div className="flex items-center gap-1.5">
        <Link href={`/jobs/${jobId}`} className={btnCls} title={t.reader.backToJobBtn}>
          <ArrowLeft className="w-4 h-4" strokeWidth={1.5} />
        </Link>
        <button
          onClick={toggleSidebar}
          className={btnCls}
          title={sidebarOpen ? t.reader.hideSidebar : t.reader.showSidebar}
        >
          {sidebarOpen ? (
            <PanelLeftClose className="w-4 h-4" strokeWidth={1.5} />
          ) : (
            <PanelLeft className="w-4 h-4" strokeWidth={1.5} />
          )}
        </button>
        <span className="text-xs truncate max-w-[200px] hidden sm:inline opacity-60">
          {title}
        </span>
      </div>

      {/* Center: Chapter navigation */}
      <div className="flex items-center gap-1">
        <button
          onClick={onPrevChapter}
          disabled={currentChapter <= 0}
          className="p-1 rounded hover:opacity-70 disabled:opacity-30 cursor-pointer transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>
        <span className="text-xs tabular-nums px-2 whitespace-nowrap">
          {currentChapter + 1} / {totalChapters}
        </span>
        <button
          onClick={onNextChapter}
          disabled={currentChapter >= totalChapters - 1}
          className="p-1 rounded hover:opacity-70 disabled:opacity-30 cursor-pointer transition-colors"
        >
          <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-0.5">
        <button onClick={decreaseFontSize} className={btnCls} title={t.reader.smaller}>
          <Minus className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>
        <span className="text-[10px] tabular-nums w-5 text-center">
          {FONT_SIZE_LABELS[fontSize]}
        </span>
        <button onClick={increaseFontSize} className={btnCls} title={t.reader.larger}>
          <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>

        <div className="w-px h-4 bg-current opacity-15 mx-1" />

        <button
          onClick={() => setFont(font === "serif" ? "sans" : "serif")}
          className={`${btnCls} px-1.5 text-[11px] font-medium`}
          style={{ fontFamily: font === "serif" ? "serif" : "sans-serif" }}
          title={`Switch to ${font === "serif" ? "sans-serif" : "serif"}`}
        >
          Aa
        </button>

        <button
          onClick={() => {
            const idx = THEME_ORDER.indexOf(theme);
            setTheme(THEME_ORDER[(idx + 1) % THEME_ORDER.length]);
          }}
          className={btnCls}
          title={`${t.reader.theme}: ${theme}`}
        >
          <ThemeIcon className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>

        <button
          onClick={toggleFullscreen}
          className={`${btnCls} hidden md:block`}
          title={fullscreen ? t.reader.exitFullscreen : t.reader.fullscreen}
        >
          {fullscreen ? (
            <Minimize className="w-3.5 h-3.5" strokeWidth={1.5} />
          ) : (
            <Maximize className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
        </button>

        {downloadUrl && (
          <a href={downloadUrl} download className={btnCls} title={t.reader.downloadBtn}>
            <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
          </a>
        )}
      </div>
    </header>
  );
}
