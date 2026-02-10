"use client";

import { useReaderSettings } from "./reader-context";
import { Badge } from "@/components/ui/badge";
import { Shield, CheckCircle, BookOpen, AlertTriangle } from "lucide-react";
import type { ReaderChapter, ReaderContent, ReaderTheme } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n";

interface ReaderSidebarProps {
  chapters: ReaderChapter[];
  currentChapter: number;
  onSelectChapter: (index: number) => void;
  quality?: ReaderContent["quality"];
  metadata?: ReaderContent["metadata"];
}

const SIDEBAR_BG: Record<ReaderTheme, string> = {
  light: "var(--bg-sidebar)",
  sepia: "#EDE4D1",
  dark: "#181818",
};
const SIDEBAR_BORDER: Record<ReaderTheme, string> = {
  light: "var(--border-default)",
  sepia: "#D4C9B0",
  dark: "#333",
};
const SIDEBAR_FG: Record<ReaderTheme, string> = {
  light: "var(--fg-secondary)",
  sepia: "#5F4B32",
  dark: "#999",
};

export function ReaderSidebar({
  chapters,
  currentChapter,
  onSelectChapter,
  quality,
  metadata,
}: ReaderSidebarProps) {
  const { theme, sidebarOpen } = useReaderSettings();
  const { t } = useLocale();

  if (!sidebarOpen) return null;

  const gradeVariant = (grade?: string) => {
    if (!grade) return "default" as const;
    if (grade <= "B") return "success" as const;
    if (grade <= "C") return "warning" as const;
    return "error" as const;
  };

  return (
    <aside
      className="w-[260px] shrink-0 flex flex-col overflow-hidden hidden md:flex"
      style={{
        background: SIDEBAR_BG[theme],
        borderRight: `1px solid ${SIDEBAR_BORDER[theme]}`,
        color: SIDEBAR_FG[theme],
        transition: "background 200ms, border-color 200ms, color 200ms",
      }}
    >
      {/* TOC Header */}
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ borderBottom: `1px solid ${SIDEBAR_BORDER[theme]}` }}
      >
        <BookOpen className="w-3.5 h-3.5 opacity-50" strokeWidth={1.5} />
        <span className="text-xs font-semibold uppercase tracking-wider opacity-60">
          {t.reader.contents}
        </span>
      </div>

      {/* Chapter List */}
      <nav className="flex-1 overflow-y-auto py-2 px-2">
        {chapters.map((ch, i) => (
          <button
            key={ch.id}
            onClick={() => onSelectChapter(i)}
            className="w-full text-left px-3 py-2 rounded text-sm transition-colors block cursor-pointer"
            style={{
              background:
                i === currentChapter
                  ? theme === "dark"
                    ? "#2A2A2A"
                    : theme === "sepia"
                      ? "#D6CABA"
                      : "var(--bg-active)"
                  : "transparent",
              fontWeight: i === currentChapter ? 500 : 400,
            }}
          >
            <span className="text-[11px] opacity-40 tabular-nums mr-2">
              {i + 1}
            </span>
            <span className="line-clamp-2">{ch.title}</span>
          </button>
        ))}
      </nav>

      {/* Quality Summary */}
      {quality &&
        (quality.eqs_grade || quality.consistency_score !== undefined) && (
          <div
            className="px-4 py-3 space-y-2.5"
            style={{ borderTop: `1px solid ${SIDEBAR_BORDER[theme]}` }}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider opacity-40">
              {t.reader.quality}
            </p>
            {quality.eqs_grade && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Shield
                    className="w-3 h-3 opacity-40"
                    strokeWidth={1.5}
                  />
                  <span className="text-xs">{t.reader.extraction}</span>
                </div>
                <Badge variant={gradeVariant(quality.eqs_grade)}>
                  {quality.eqs_grade}
                </Badge>
              </div>
            )}
            {quality.consistency_score !== undefined && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <CheckCircle
                    className="w-3 h-3 opacity-40"
                    strokeWidth={1.5}
                  />
                  <span className="text-xs">{t.reader.consistency}</span>
                </div>
                <Badge
                  variant={quality.consistency_passed ? "success" : "warning"}
                >
                  {Math.round(quality.consistency_score * 100)}%
                </Badge>
              </div>
            )}
            {quality.provider && (
              <div className="flex items-center justify-between">
                <span className="text-xs opacity-50">{t.reader.providerLabel}</span>
                <span className="text-xs capitalize">{quality.provider}</span>
              </div>
            )}
          </div>
        )}

      {/* Source text warning */}
      {metadata?.content_source?.startsWith("source_") && (
        <div
          className="px-4 py-2.5 flex items-center gap-2"
          style={{ borderTop: `1px solid ${SIDEBAR_BORDER[theme]}` }}
        >
          <AlertTriangle className="w-3 h-3 shrink-0" style={{ color: "var(--color-notion-yellow)" }} strokeWidth={1.5} />
          <span className="text-[11px]" style={{ color: "var(--color-notion-yellow)" }}>
            {t.reader.sourceWarning}
          </span>
        </div>
      )}

      {/* Metadata */}
      {metadata && (
        <div
          className="px-4 py-2.5"
          style={{ borderTop: `1px solid ${SIDEBAR_BORDER[theme]}` }}
        >
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] opacity-40">
            <span>{metadata.total_words.toLocaleString()} {t.reader.words}</span>
            {metadata.tables > 0 && <span>{metadata.tables} {t.reader.tablesLabel}</span>}
            {metadata.formulas > 0 && (
              <span>{metadata.formulas} {t.reader.formulasLabel}</span>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
