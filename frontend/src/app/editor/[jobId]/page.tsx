"use client";

import { useState, useEffect, useCallback, useRef, use } from "react";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { useEditorSegments, useUpdateEditorSegment, useRegenerateDocument, useTMs, useTMLookup } from "@/lib/api/hooks";
import type { EditorSegment, TMMatch } from "@/lib/api/types";
import {
  ArrowLeft,
  Save,
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Keyboard,
  Database,
  Zap,
} from "lucide-react";

export default function EditorPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const { t } = useLocale();
  const [activeIndex, setActiveIndex] = useState(0);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [savingChunk, setSavingChunk] = useState<string | null>(null);
  const [savedChunk, setSavedChunk] = useState<string | null>(null);
  const [showKeyboard, setShowKeyboard] = useState(false);
  const [tmMatches, setTmMatches] = useState<TMMatch[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { data: editorData, isLoading } = useEditorSegments(jobId);
  const updateSegment = useUpdateEditorSegment(jobId);
  const regenerate = useRegenerateDocument(jobId);
  const { data: tmsData } = useTMs();
  const tmLookup = useTMLookup();

  const segments = editorData?.segments ?? [];
  const activeSegment = segments[activeIndex];

  // Initialize edit values from loaded segments
  useEffect(() => {
    if (segments.length > 0) {
      const values: Record<string, string> = {};
      segments.forEach((s) => {
        if (!(s.chunk_id in editValues)) {
          values[s.chunk_id] = s.translated;
        }
      });
      if (Object.keys(values).length > 0) {
        setEditValues((prev) => ({ ...values, ...prev }));
      }
    }
  }, [segments]);

  // TM lookup when active segment changes
  useEffect(() => {
    if (!activeSegment || !tmsData?.tms?.length) {
      setTmMatches([]);
      return;
    }
    const tmIds = tmsData.tms.map((t) => t.id);
    tmLookup.mutate(
      { tmIds, sourceText: activeSegment.source, minSimilarity: 0.5 },
      { onSuccess: (data) => setTmMatches(data.matches) },
    );
  }, [activeIndex, activeSegment?.chunk_id]);

  const goToSegment = useCallback(
    (idx: number) => {
      const clamped = Math.max(0, Math.min(segments.length - 1, idx));
      setActiveIndex(clamped);
      // Scroll active segment into view
      const el = document.getElementById(`segment-${clamped}`);
      el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    },
    [segments.length],
  );

  const handleSave = useCallback(
    (chunkId: string) => {
      const text = editValues[chunkId];
      if (text === undefined) return;
      setSavingChunk(chunkId);
      updateSegment.mutate(
        { chunkId, translatedText: text },
        {
          onSuccess: () => {
            setSavingChunk(null);
            setSavedChunk(chunkId);
            setTimeout(() => setSavedChunk(null), 2000);
          },
          onError: () => setSavingChunk(null),
        },
      );
    },
    [editValues, updateSegment],
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          goToSegment(activeIndex + 1);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          goToSegment(activeIndex - 1);
        } else if (e.key === "s") {
          e.preventDefault();
          if (activeSegment) handleSave(activeSegment.chunk_id);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [activeIndex, activeSegment, goToSegment, handleSave]);

  const applyTMMatch = (match: TMMatch) => {
    if (!activeSegment) return;
    setEditValues((prev) => ({ ...prev, [activeSegment.chunk_id]: match.target_text }));
    textareaRef.current?.focus();
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-sm" style={{ color: "var(--fg-secondary)" }}>
        {t.common.loading}
      </div>
    );
  }

  if (!editorData || segments.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm" style={{ color: "var(--fg-secondary)" }}>
          No segments found for this job.
        </p>
        <Link
          href={`/jobs/${jobId}`}
          className="text-sm mt-2 inline-block"
          style={{ color: "var(--accent)" }}
        >
          {t.editor.backToJob}
        </Link>
      </div>
    );
  }

  const editedCount = segments.filter((s) => s.is_edited || editValues[s.chunk_id] !== s.translated).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center gap-1 text-sm no-underline mb-3"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-4 h-4" />
          {t.editor.backToJob}
        </Link>

        <div className="flex items-center justify-between">
          <div>
            <h1>{t.editor.title}</h1>
            <p className="text-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
              {segments.length} segments · {t.editor.completion}: {editorData.completion_percentage.toFixed(0)}%
              · {editedCount} {t.editor.edited}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowKeyboard(!showKeyboard)}
              className="p-2"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
              title={t.editor.keyboard}
            >
              <Keyboard className="w-4 h-4" />
            </button>
            <button
              onClick={() => regenerate.mutate()}
              disabled={regenerate.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              {t.editor.regenerate}
            </button>
          </div>
        </div>
      </div>

      {/* Keyboard shortcuts help */}
      {showKeyboard && (
        <div
          className="p-3 text-xs space-y-1"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--bg-secondary)",
            color: "var(--fg-secondary)",
          }}
        >
          <p className="font-medium" style={{ color: "var(--fg-primary)" }}>{t.editor.keyboard}</p>
          <p><kbd className="px-1 py-0.5 font-mono" style={{ background: "var(--bg-active)", borderRadius: "3px" }}>Ctrl+↓</kbd> {t.editor.keyNext}</p>
          <p><kbd className="px-1 py-0.5 font-mono" style={{ background: "var(--bg-active)", borderRadius: "3px" }}>Ctrl+↑</kbd> {t.editor.keyPrev}</p>
          <p><kbd className="px-1 py-0.5 font-mono" style={{ background: "var(--bg-active)", borderRadius: "3px" }}>Ctrl+S</kbd> {t.editor.keySave}</p>
        </div>
      )}

      {/* Completion bar */}
      <div
        className="h-1.5 overflow-hidden"
        style={{ borderRadius: "var(--radius-sm)", background: "var(--bg-secondary)" }}
      >
        <div
          className="h-full transition-all"
          style={{
            width: `${editorData.completion_percentage}%`,
            background: "var(--accent)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>

      {/* Main editor layout */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Segment list + editor */}
        <div className="flex-1 min-w-0 space-y-2">
          {segments.map((seg, idx) => {
            const isActive = idx === activeIndex;
            const currentText = editValues[seg.chunk_id] ?? seg.translated;
            const isModified = currentText !== seg.translated;
            const isSaving = savingChunk === seg.chunk_id;
            const justSaved = savedChunk === seg.chunk_id;

            return (
              <div
                key={seg.chunk_id}
                id={`segment-${idx}`}
                onClick={() => setActiveIndex(idx)}
                className="cursor-pointer transition-all"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: `1px solid ${isActive ? "var(--accent)" : "var(--border-default)"}`,
                  background: isActive ? "var(--bg-secondary)" : "var(--bg-primary)",
                }}
              >
                {/* Segment header */}
                <div
                  className="flex items-center justify-between px-3 py-1.5"
                  style={{ borderBottom: isActive ? "1px solid var(--border-default)" : "none" }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5"
                      style={{
                        borderRadius: "var(--radius-sm)",
                        background: "var(--bg-active)",
                        color: "var(--fg-secondary)",
                      }}
                    >
                      #{idx + 1}
                    </span>
                    {seg.is_edited && (
                      <span className="text-[10px] px-1.5 py-0.5" style={{
                        borderRadius: "var(--radius-sm)",
                        background: "rgba(59,130,246,0.1)",
                        color: "var(--accent)",
                      }}>
                        {t.editor.edited}
                      </span>
                    )}
                    {isModified && (
                      <span className="text-[10px] px-1.5 py-0.5" style={{
                        borderRadius: "var(--radius-sm)",
                        background: "rgba(234,179,8,0.1)",
                        color: "rgb(234,179,8)",
                      }}>
                        Modified
                      </span>
                    )}
                    {seg.warnings.length > 0 && (
                      <AlertTriangle className="w-3 h-3" style={{ color: "rgb(234,179,8)" }} />
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    {justSaved && <CheckCircle2 className="w-3.5 h-3.5" style={{ color: "rgb(34,197,94)" }} />}
                    <span
                      className="text-[10px] px-1.5 py-0.5"
                      style={{
                        borderRadius: "var(--radius-sm)",
                        background: seg.quality_score >= 0.8 ? "rgba(34,197,94,0.15)" : "rgba(234,179,8,0.15)",
                        color: seg.quality_score >= 0.8 ? "rgb(34,197,94)" : "rgb(234,179,8)",
                      }}
                    >
                      {(seg.quality_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Source + Translation */}
                <div className={isActive ? "p-3 space-y-3" : "px-3 py-2"}>
                  {/* Source */}
                  <div>
                    {isActive && (
                      <label className="block text-[10px] font-medium mb-1 uppercase tracking-wide" style={{ color: "var(--fg-secondary)" }}>
                        {t.editor.source}
                      </label>
                    )}
                    <p
                      className={isActive ? "text-sm leading-relaxed" : "text-sm truncate"}
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {seg.source}
                    </p>
                  </div>

                  {/* Translation */}
                  {isActive ? (
                    <div>
                      <label className="block text-[10px] font-medium mb-1 uppercase tracking-wide" style={{ color: "var(--fg-secondary)" }}>
                        {t.editor.translation}
                      </label>
                      <textarea
                        ref={textareaRef}
                        value={currentText}
                        onChange={(e) =>
                          setEditValues((prev) => ({ ...prev, [seg.chunk_id]: e.target.value }))
                        }
                        rows={4}
                        className="w-full px-3 py-2 text-sm leading-relaxed resize-none"
                        style={{
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border-default)",
                          background: "var(--bg-primary)",
                          color: "var(--fg-primary)",
                        }}
                      />
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              goToSegment(idx - 1);
                            }}
                            disabled={idx === 0}
                            className="p-1 disabled:opacity-30"
                            style={{ borderRadius: "var(--radius-sm)", border: "1px solid var(--border-default)" }}
                          >
                            <ChevronUp className="w-3.5 h-3.5" style={{ color: "var(--fg-icon)" }} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              goToSegment(idx + 1);
                            }}
                            disabled={idx === segments.length - 1}
                            className="p-1 disabled:opacity-30"
                            style={{ borderRadius: "var(--radius-sm)", border: "1px solid var(--border-default)" }}
                          >
                            <ChevronDown className="w-3.5 h-3.5" style={{ color: "var(--fg-icon)" }} />
                          </button>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSave(seg.chunk_id);
                          }}
                          disabled={isSaving || !isModified}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                          style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
                        >
                          {isSaving ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Save className="w-3.5 h-3.5" />
                          )}
                          {isSaving ? t.editor.saving : t.editor.saveSegment}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm truncate mt-1" style={{ color: "var(--fg-secondary)" }}>
                      {currentText}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* TM Suggestions panel */}
        <div
          className="lg:w-72 shrink-0"
          style={{
            position: "sticky",
            top: "1rem",
            alignSelf: "flex-start",
          }}
        >
          <div
            className="p-3 space-y-3"
            style={{
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--bg-primary)",
            }}
          >
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
              <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.editor.tmSuggestions}
              </span>
            </div>

            {tmLookup.isPending && (
              <div className="py-4 text-center">
                <Loader2 className="w-4 h-4 animate-spin mx-auto" style={{ color: "var(--fg-icon)" }} />
              </div>
            )}

            {!tmLookup.isPending && tmMatches.length === 0 && (
              <p className="text-xs py-4 text-center" style={{ color: "var(--fg-secondary)" }}>
                {t.editor.noSuggestions}
              </p>
            )}

            {tmMatches.map((match) => (
              <div
                key={match.segment_id}
                className="p-2 space-y-1.5"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-secondary)",
                }}
              >
                <div className="flex items-center justify-between">
                  <span
                    className="text-[10px] px-1.5 py-0.5 font-medium"
                    style={{
                      borderRadius: "var(--radius-sm)",
                      background:
                        match.match_type === "exact"
                          ? "rgba(34,197,94,0.15)"
                          : match.match_type === "fuzzy"
                            ? "rgba(234,179,8,0.15)"
                            : "rgba(156,163,175,0.15)",
                      color:
                        match.match_type === "exact"
                          ? "rgb(34,197,94)"
                          : match.match_type === "fuzzy"
                            ? "rgb(234,179,8)"
                            : "var(--fg-secondary)",
                    }}
                  >
                    {(match.similarity * 100).toFixed(0)}%
                  </span>
                  <span className="text-[10px]" style={{ color: "var(--fg-secondary)" }}>
                    {match.tm_name}
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--fg-secondary)" }}>
                  {match.source_text.slice(0, 120)}{match.source_text.length > 120 ? "..." : ""}
                </p>
                <p className="text-xs leading-relaxed font-medium" style={{ color: "var(--fg-primary)" }}>
                  {match.target_text.slice(0, 120)}{match.target_text.length > 120 ? "..." : ""}
                </p>
                <button
                  onClick={() => applyTMMatch(match)}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium"
                  style={{
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    color: "var(--accent)",
                  }}
                >
                  <Zap className="w-3 h-3" />
                  {t.editor.apply}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
