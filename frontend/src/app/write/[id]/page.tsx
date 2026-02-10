"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle,
  Clock,
  Download,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useBookProject, useApproveOutline, useBookWebSocket } from "@/lib/api/hooks";
import { bookWriter } from "@/lib/api/client";
import { formatDate, formatNumber } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import type { BookProject, BookChapter } from "@/lib/api/types";

// ─── Progress calculation ───

const TERMINAL_STATUSES = new Set(["outline_ready", "complete", "failed", "paused"]);

function getProgressPercent(book: BookProject): number {
  const tc = book.progress.total_chapters || 1;
  switch (book.status) {
    case "created":
      return 2;
    case "analyzing":
      return 5;
    case "analysis_ready":
      return 8;
    case "architecting":
      return 12;
    case "outlining":
      return 18;
    case "outline_ready":
      return 20;
    case "writing":
      return 20 + Math.round((book.progress.chapters_written / tc) * 50);
    case "enriching":
      return 70 + Math.round((book.progress.chapters_enriched / tc) * 15);
    case "editing":
      return 85 + Math.round((book.progress.chapters_edited / tc) * 10);
    case "compiling":
      return 96;
    case "complete":
      return 100;
    default:
      return 0;
  }
}

// ─── Chapter components ───

function ChapterStatusBadge({ status }: { status: string }) {
  const { t } = useLocale();
  if (status === "written" || status === "enriched" || status === "edited" || status === "user_edited")
    return (
      <Badge variant="success">
        <CheckCircle className="w-3 h-3 mr-1" strokeWidth={1.5} />
        {t.write.chapterStatus.done}
      </Badge>
    );
  if (status === "writing" || status === "enriching" || status === "editing" || status === "regenerating")
    return (
      <Badge variant="info">
        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        {t.write.chapterStatus.writing}
      </Badge>
    );
  return <Badge variant="default">{t.write.chapterStatus.pending}</Badge>;
}

function ExpandableChapter({ chapter }: { chapter: BookChapter }) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useLocale();
  const isDone = chapter.status !== "pending";
  const content = chapter.final_content || chapter.edited_content || chapter.enriched_content || chapter.content;

  return (
    <div
      style={{
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <button
        onClick={() => isDone && content && setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 text-left"
        style={{ cursor: isDone && content ? "pointer" : "default" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          {isDone && content ? (
            expanded ? (
              <ChevronDown className="w-4 h-4 shrink-0" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            ) : (
              <ChevronRight className="w-4 h-4 shrink-0" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            )
          ) : (
            <div className="w-4 h-4 shrink-0" />
          )}
          <div className="min-w-0">
            <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              Ch {chapter.chapter_number}: {chapter.title}
            </span>
            {chapter.word_count > 0 && (
              <span className="ml-2 text-xs" style={{ color: "var(--fg-tertiary)" }}>
                {formatNumber(chapter.word_count)} {t.write.words}
              </span>
            )}
          </div>
        </div>
        <ChapterStatusBadge status={chapter.status} />
      </button>
      {expanded && content && (
        <div
          className="px-4 pb-4 pt-0 text-sm leading-relaxed whitespace-pre-wrap"
          style={{
            color: "var(--fg-secondary)",
            borderTop: "1px solid var(--border-default)",
            maxHeight: "400px",
            overflowY: "auto",
          }}
        >
          {content.slice(0, 3000)}
          {content.length > 3000 && "..."}
        </div>
      )}
    </div>
  );
}

// ─── Main page ───

export default function BookDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: book, isLoading } = useBookProject(id);
  useBookWebSocket(id);
  const approveOutline = useApproveOutline();
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 skeleton" />
        <div className="h-40 skeleton" />
      </div>
    );
  }

  if (!book) {
    return <p style={{ color: "var(--fg-tertiary)" }}>Book not found</p>;
  }

  const progressPct = getProgressPercent(book);

  const handleApprove = async () => {
    try {
      await approveOutline.mutateAsync({
        bookId: book.id,
        request: { approved: true },
      });
    } catch {
      // Error handled by mutation state
    }
  };

  const handleDownload = async () => {
    const url = bookWriter.getDownloadUrl(book.id);
    const res = await fetch(url);
    if (!res.ok) return;
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${book.title || "book"}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/write"
          className="text-sm flex items-center gap-1 mb-2 no-underline"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-3 h-3" /> {t.write.backToBooks}
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2">
              <BookOpen className="w-6 h-6" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              {book.title || "Untitled Book"}
            </h1>
            <p className="mt-1" style={{ color: "var(--fg-secondary)" }}>
              {book.chapter_count > 0 && `${book.chapter_count} ${t.write.chapters}`}
              {book.total_words > 0 && ` \u00B7 ${formatNumber(book.total_words)} ${t.write.words}`}
              {book.created_at && ` \u00B7 ${formatDate(book.created_at)}`}
            </p>
          </div>
          <Badge
            variant={
              book.status === "complete"
                ? "success"
                : book.status === "failed"
                  ? "error"
                  : book.status === "outline_ready"
                    ? "warning"
                    : "info"
            }
          >
            {!TERMINAL_STATUSES.has(book.status) && book.status !== "created" && (
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            )}
            {book.status === "outline_ready" && <Clock className="w-3 h-3 mr-1" strokeWidth={1.5} />}
            {book.status.replace("_", " ")}
          </Badge>
        </div>
      </div>

      {/* Planning / analyzing state */}
      {["created", "analyzing", "analysis_ready", "architecting", "outlining"].includes(book.status) && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--color-notion-blue)" }} />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.write.planning}
              </p>
              <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                {book.progress.current_agent || book.status.replace("_", " ")}
              </p>
            </div>
          </div>
          <div
            className="mt-3 h-2 overflow-hidden"
            style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}
          >
            <div
              className="h-full transition-all duration-1000"
              style={{
                width: `${progressPct}%`,
                background: "var(--color-notion-blue)",
                borderRadius: "var(--radius-sm)",
              }}
            />
          </div>
        </Card>
      )}

      {/* Outline Ready — approval checkpoint */}
      {book.status === "outline_ready" && book.blueprint && (
        <>
          <Card
            className="px-5 py-4"
            style={{
              border: "2px solid var(--color-notion-yellow)",
              background: "var(--accent-yellow-bg)",
            }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--fg-primary)" }}>
                  {t.write.outlineReady}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--fg-secondary)" }}>
                  {t.write.approveDesc}
                </p>
              </div>
              <Button
                variant="primary"
                size="lg"
                onClick={handleApprove}
                loading={approveOutline.isPending}
              >
                <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                {t.write.approveBtn}
              </Button>
            </div>
          </Card>

          {/* Blueprint details */}
          <Card>
            <CardHeader>
              <h3 className="text-[15px] font-semibold">{book.blueprint.title}</h3>
              {book.blueprint.subtitle && (
                <p className="text-sm mt-0.5" style={{ color: "var(--fg-secondary)" }}>
                  {book.blueprint.subtitle}
                </p>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-4 text-xs" style={{ color: "var(--fg-tertiary)" }}>
                {book.analysis?.target_audience && (
                  <span>
                    {t.write.targetAudience}: {book.analysis.target_audience}
                  </span>
                )}
                {book.blueprint.total_words > 0 && (
                  <span>
                    {t.write.estimatedWords}: {formatNumber(book.blueprint.total_words)}
                  </span>
                )}
              </div>

              <div className="space-y-2 mt-4">
                {book.blueprint.chapters?.map(
                  (ch: { chapter_number: number; title: string; purpose: string; key_points: string[]; word_target: number }) => (
                    <div
                      key={ch.chapter_number}
                      className="p-3"
                      style={{
                        border: "1px solid var(--border-default)",
                        borderRadius: "var(--radius-md)",
                      }}
                    >
                      <div className="flex items-baseline justify-between">
                        <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                          {ch.chapter_number}. {ch.title}
                        </span>
                        <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
                          ~{formatNumber(ch.word_target)} {t.write.words}
                        </span>
                      </div>
                      <p className="text-xs mt-1" style={{ color: "var(--fg-secondary)" }}>
                        {ch.purpose}
                      </p>
                      {ch.key_points?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {ch.key_points.map((kp: string, i: number) => (
                            <span
                              key={i}
                              className="text-[11px] px-1.5 py-0.5"
                              style={{
                                background: "var(--bg-secondary)",
                                borderRadius: "var(--radius-sm)",
                                color: "var(--fg-tertiary)",
                              }}
                            >
                              {kp}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ),
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Writing / enriching / editing / compiling progress */}
      {["writing", "enriching", "editing", "compiling"].includes(book.status) && (
        <Card className="px-5 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              {book.status === "compiling"
                ? t.write.compiling
                : `${t.write.writingProgress} ${book.progress.current_chapter} ${t.write.chapterOf} ${book.progress.total_chapters}...`}
            </span>
            <span className="text-sm" style={{ color: "var(--fg-secondary)" }}>
              {progressPct}%
            </span>
          </div>
          <div
            className="h-2 overflow-hidden"
            style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}
          >
            <div
              className="h-full transition-all duration-1000"
              style={{
                width: `${progressPct}%`,
                background: "var(--color-notion-blue)",
                borderRadius: "var(--radius-sm)",
              }}
            />
          </div>
          <p className="text-xs mt-2" style={{ color: "var(--fg-tertiary)" }}>
            {book.progress.current_agent || book.status.replace("_", " ")}
          </p>
        </Card>
      )}

      {/* Complete */}
      {book.status === "complete" && (
        <Card className="px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5" style={{ color: "var(--color-notion-green)" }} strokeWidth={1.5} />
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                  {t.write.complete}
                </p>
                <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                  {book.chapter_count} {t.write.chapters} &middot; {formatNumber(book.total_words)} {t.write.words}
                  {book.updated_at && ` \u00B7 ${formatDate(book.updated_at)}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="lg" onClick={() => router.push(`/write/${id}/read`)}>
                <Eye className="w-4 h-4 mr-2" strokeWidth={1.5} />
                {t.write.readBook}
              </Button>
              <Button variant="primary" size="lg" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" strokeWidth={1.5} />
                {t.write.downloadBook}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Failed */}
      {book.status === "failed" && book.error && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5" style={{ color: "var(--color-notion-red)" }} strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.write.failed}
              </p>
              <p className="text-xs" style={{ color: "var(--color-notion-red)" }}>
                {book.error}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Chapter list (for writing/complete states) */}
      {book.chapters && book.chapters.length > 0 && book.status !== "outline_ready" && (
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              {t.write.chapters} (
              {book.chapters.filter(
                (c) => !["pending", "writing", "enriching", "editing", "regenerating"].includes(c.status),
              ).length}
              /{book.chapters.length})
            </h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {book.chapters.map((ch) => (
                <ExpandableChapter key={ch.chapter_number} chapter={ch} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
