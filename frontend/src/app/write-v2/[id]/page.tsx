"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle,
  Download,
  AlertTriangle,
  Eye,
  Pause,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useBookV2Project, useBookV2WebSocket, usePauseBookV2 } from "@/lib/api/hooks";
import { bookWriterV2 } from "@/lib/api/client";
import { formatDate, formatNumber } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import { BookProgress } from "@/components/book-writer-v2/book-progress";
import { useState } from "react";
import type { BookV2Project, BookV2Blueprint } from "@/lib/api/types";

const TERMINAL = new Set(["completed", "failed", "paused"]);
const ACTIVE = new Set([
  "analyzing", "architecting", "outlining", "writing",
  "expanding", "enriching", "editing", "quality_check", "publishing",
]);

export default function BookV2DetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: project, isLoading } = useBookV2Project(id);
  useBookV2WebSocket(id);
  const pauseBook = usePauseBookV2();
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 skeleton" />
        <div className="h-40 skeleton" />
      </div>
    );
  }

  if (!project) {
    return <p style={{ color: "var(--fg-tertiary)" }}>Book not found</p>;
  }

  const title = project.blueprint?.title || `Book #${project.id.slice(0, 8)}`;
  const isActive = ACTIVE.has(project.status);

  const handleDownload = async (format = "docx") => {
    try {
      await bookWriterV2.download(project.id, format, `${title}.${format}`);
    } catch {
      // handled
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/write-v2"
          className="text-sm flex items-center gap-1 mb-2 no-underline"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-3 h-3" /> {t.writeV2.backToBooks}
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2">
              <BookOpen className="w-6 h-6" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              {title}
            </h1>
            {project.blueprint && (
              <p className="mt-1 text-sm" style={{ color: "var(--fg-secondary)" }}>
                {project.blueprint.actual_words > 0 &&
                  `${formatNumber(project.blueprint.actual_words)} ${t.writeV2.words}`}
                {project.blueprint.actual_pages > 0 &&
                  ` \u00B7 ${project.blueprint.actual_pages} ${t.writeV2.pages}`}
                {project.created_at && ` \u00B7 ${formatDate(project.created_at)}`}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isActive && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => pauseBook.mutate(project.id)}
                loading={pauseBook.isPending}
              >
                <Pause className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
                {t.writeV2.pause}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Created — waiting for pipeline to start */}
      {project.status === "created" && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <div
              className="w-5 h-5 rounded-full animate-pulse"
              style={{ background: "var(--color-notion-blue)", opacity: 0.6 }}
            />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.statusCreated}
              </p>
              <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                Waiting for pipeline to start...
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Progress */}
      {(isActive || project.status === "paused") && <BookProgress project={project} />}

      {/* Completed */}
      {project.status === "completed" && (
        <Card className="px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5" style={{ color: "var(--color-notion-green)" }} strokeWidth={1.5} />
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                  {t.writeV2.bookComplete}
                </p>
                <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                  {project.blueprint &&
                    `${formatNumber(project.blueprint.actual_words)} ${t.writeV2.words} \u00B7 ${project.blueprint.actual_pages} ${t.writeV2.pages}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="lg" onClick={() => router.push(`/write-v2/${id}/read`)}>
                <Eye className="w-4 h-4 mr-2" strokeWidth={1.5} />
                {t.writeV2.readBook}
              </Button>
              {Object.keys(project.output_files).length > 0 ? (
                Object.keys(project.output_files).map((fmt) => (
                  <Button key={fmt} variant="primary" size="lg" onClick={() => handleDownload(fmt)}>
                    <Download className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    {fmt.toUpperCase()}
                  </Button>
                ))
              ) : (
                <Button variant="primary" size="lg" onClick={() => handleDownload()}>
                  <Download className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  {t.writeV2.download}
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Failed */}
      {project.status === "failed" && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5" style={{ color: "var(--color-notion-red)" }} strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.bookFailed}
              </p>
              {project.errors.length > 0 && (
                <p className="text-xs mt-1" style={{ color: "var(--color-notion-red)" }}>
                  {project.errors[project.errors.length - 1].message}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Blueprint details */}
      {project.blueprint && <BlueprintView blueprint={project.blueprint} />}

      {/* Errors */}
      {project.errors.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold" style={{ color: "var(--fg-primary)" }}>
              {t.writeV2.errors} ({project.errors.length})
            </h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {project.errors.map((err, i) => (
                <div
                  key={i}
                  className="text-xs p-2"
                  style={{
                    background: "var(--accent-red-bg)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--color-notion-red)",
                  }}
                >
                  {err.agent && <span className="font-medium">[{err.agent}] </span>}
                  {err.message}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BlueprintView({ blueprint }: { blueprint: BookV2Blueprint }) {
  const { t } = useLocale();
  const [expandedParts, setExpandedParts] = useState<Set<number>>(new Set([1]));

  const togglePart = (num: number) => {
    setExpandedParts((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  };

  return (
    <Card>
      <CardHeader>
        <h3 className="text-[15px] font-semibold flex items-center gap-2" style={{ color: "var(--fg-primary)" }}>
          <BookOpen className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
          {t.writeV2.blueprint}
        </h3>
        <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
          {blueprint.total_chapters} {t.writeV2.chapters} \u00B7 {blueprint.total_sections}{" "}
          {t.writeV2.sections} \u00B7 {Math.round(blueprint.completion)}% complete
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {blueprint.parts.map((part) => (
          <div
            key={part.id}
            style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}
          >
            <button
              onClick={() => togglePart(part.number)}
              className="w-full flex items-center justify-between p-3 text-left"
              style={{ cursor: "pointer" }}
            >
              <div className="flex items-center gap-2">
                {expandedParts.has(part.number) ? (
                  <ChevronDown className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
                ) : (
                  <ChevronRight className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
                )}
                <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                  Part {part.number}: {part.title}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={part.is_complete ? "success" : "default"}>
                  {part.chapters.length} ch
                </Badge>
                <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
                  {Math.round(part.progress)}%
                </span>
              </div>
            </button>

            {expandedParts.has(part.number) && (
              <div
                className="px-4 pb-3 space-y-1.5"
                style={{ borderTop: "1px solid var(--border-default)" }}
              >
                {part.chapters.map((ch) => (
                  <div
                    key={ch.id}
                    className="flex items-center justify-between py-1.5 text-sm"
                    style={{ borderBottom: "1px solid var(--border-default)" }}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {ch.is_complete ? (
                        <CheckCircle
                          className="w-3.5 h-3.5 shrink-0"
                          style={{ color: "var(--color-notion-green)" }}
                          strokeWidth={1.5}
                        />
                      ) : (
                        <div
                          className="w-3.5 h-3.5 shrink-0 rounded-full"
                          style={{ border: "2px solid var(--border-default)" }}
                        />
                      )}
                      <span style={{ color: "var(--fg-primary)" }}>
                        Ch {ch.number}: {ch.title}
                      </span>
                    </div>
                    <span className="text-xs shrink-0 ml-2" style={{ color: "var(--fg-tertiary)" }}>
                      {formatNumber(ch.word_count.actual)}/{formatNumber(ch.word_count.target)}{" "}
                      {t.writeV2.words}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
