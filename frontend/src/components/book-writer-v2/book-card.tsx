"use client";

import Link from "next/link";
import { BookOpen, Loader2, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n";
import { formatDate, formatNumber } from "@/lib/utils";
import type { BookV2Project } from "@/lib/api/types";

const ACTIVE_STATUSES = new Set([
  "analyzing", "architecting", "outlining", "writing",
  "expanding", "enriching", "editing", "quality_check", "publishing",
]);

function statusBadgeVariant(status: string): "default" | "success" | "warning" | "error" | "info" {
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  if (status === "paused") return "warning";
  if (ACTIVE_STATUSES.has(status)) return "info";
  return "default";
}

export function BookCardV2({
  project,
  onDelete,
}: {
  project: BookV2Project;
  onDelete?: (id: string) => void;
}) {
  const { t } = useLocale();
  const pct = Math.round(project.progress_percentage);
  const title = project.blueprint?.title || `Book #${project.id.slice(0, 8)}`;

  return (
    <Link href={`/write-v2/${project.id}`} className="block no-underline">
      <Card hover>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <BookOpen
                className="w-5 h-5 shrink-0"
                style={{ color: "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              <div className="min-w-0">
                <p className="font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                  {title}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--fg-tertiary)" }}>
                  {project.sections_total > 0 && (
                    <span>
                      {project.sections_completed}/{project.sections_total} {t.writeV2.sections}
                    </span>
                  )}
                  {pct > 0 && ` \u00B7 ${pct}%`}
                  {project.created_at && ` \u00B7 ${formatDate(project.created_at)}`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Badge variant={statusBadgeVariant(project.status)}>
                {ACTIVE_STATUSES.has(project.status) && (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                )}
                {project.status.replace("_", " ")}
              </Badge>
              {onDelete && (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onDelete(project.id);
                  }}
                  className="p-1 transition-colors duration-100"
                  style={{ borderRadius: "var(--radius-sm)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <Trash2
                    className="w-3.5 h-3.5"
                    style={{ color: "var(--fg-tertiary)" }}
                    strokeWidth={1.5}
                  />
                </button>
              )}
            </div>
          </div>

          {/* Mini progress bar */}
          {ACTIVE_STATUSES.has(project.status) && pct > 0 && (
            <div
              className="mt-3 h-1.5 overflow-hidden"
              style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}
            >
              <div
                className="h-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  background: "var(--color-notion-blue)",
                  borderRadius: "var(--radius-sm)",
                }}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
