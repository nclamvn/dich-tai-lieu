"use client";

import { useState } from "react";
import Link from "next/link";
import { List, FileText, Trash2, Download, CheckSquare, Square, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useJobs, useBulkDeleteJobs } from "@/lib/api/hooks";
import { jobs as jobsApi } from "@/lib/api/client";
import { formatDate, statusVariant } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

export default function JobsPage() {
  const { data, isLoading } = useJobs({ limit: 50 });
  const bulkDelete = useBulkDeleteJobs();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const jobList = data?.jobs || [];
  const { t } = useLocale();

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === jobList.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(jobList.map((j) => j.id)));
    }
  };

  const handleBulkDelete = () => {
    if (selected.size === 0) return;
    if (!confirm(`${t.jobs.delete} ${selected.size}?`)) return;
    bulkDelete.mutate([...selected], {
      onSuccess: () => setSelected(new Set()),
    });
  };

  const handleDownload = async (jobId: string, format: string, outputPath: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const filename = outputPath.split("/").pop() || `output.${format}`;
      await jobsApi.download(jobId, format, filename);
    } catch {
      // Download failed silently
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 skeleton" />
        ))}
      </div>
    );
  }

  if (jobList.length === 0) {
    return (
      <EmptyState
        icon={List}
        title={t.jobs.emptyTitle}
        description={t.jobs.emptyDesc}
        action={
          <Link href="/translate">
            <Button>{t.jobs.newTranslation}</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1>{t.jobs.title}</h1>
        <Link href="/translate">
          <Button size="sm">{t.jobs.newJob}</Button>
        </Link>
      </div>

      {/* Bulk Actions Bar */}
      <div
        className="flex items-center gap-3 sticky top-0 z-10 py-2 -mx-2 px-2"
        style={{ background: "var(--bg-primary)" }}
      >
        <button
          onClick={toggleAll}
          className="flex items-center gap-2 text-sm px-2 py-1 transition-colors"
          style={{ color: "var(--fg-secondary)", cursor: "pointer" }}
        >
          {selected.size === jobList.length ? (
            <CheckSquare className="w-4 h-4" style={{ color: "var(--color-notion-blue)" }} strokeWidth={1.5} />
          ) : (
            <Square className="w-4 h-4" strokeWidth={1.5} />
          )}
          {selected.size > 0 ? `${selected.size} ${t.jobs.selected}` : t.jobs.selectAll}
        </button>
        {selected.size > 0 && (
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleBulkDelete}
              loading={bulkDelete.isPending}
              style={{ color: "var(--color-notion-red)" }}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1" strokeWidth={1.5} />
              {t.jobs.delete} ({selected.size})
            </Button>
          </>
        )}
      </div>

      <div className="space-y-2">
        {jobList.map((job) => (
          <div key={job.id} className="flex items-center gap-2">
            {/* Checkbox */}
            <button
              onClick={(e) => toggleSelect(job.id, e)}
              className="shrink-0 p-1"
              style={{ color: selected.has(job.id) ? "var(--color-notion-blue)" : "var(--fg-ghost)" }}
            >
              {selected.has(job.id) ? (
                <CheckSquare className="w-4 h-4" strokeWidth={1.5} />
              ) : (
                <Square className="w-4 h-4" strokeWidth={1.5} />
              )}
            </button>

            {/* Job Card */}
            <Link href={`/jobs/${job.id}`} className="no-underline flex-1 min-w-0">
              <Card
                className="px-5 py-4 cursor-pointer transition-colors duration-100"
                style={{ background: "var(--bg-primary)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-primary)")}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText
                      className="w-5 h-5 shrink-0"
                      style={{ color: "var(--fg-icon)" }}
                      strokeWidth={1.5}
                    />
                    <div className="min-w-0">
                      <p
                        className="font-medium text-sm truncate"
                        style={{ color: "var(--fg-primary)" }}
                      >
                        {job.source_filename || job.id}
                      </p>
                      <p
                        className="text-xs"
                        style={{ color: "var(--fg-tertiary)" }}
                      >
                        {job.source_language}&rarr;{job.target_language} &middot;{" "}
                        {job.output_format} &middot; {formatDate(job.created_at)}
                        {job._currentStage && job.status === "processing" && (
                          <span style={{ color: "var(--color-notion-blue)" }}>
                            {" "}&middot; {job._currentStage}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {job._qualityLevel && job.status === "completed" && (
                      <Badge variant="success">
                        {job._qualityLevel}
                      </Badge>
                    )}

                    <Badge variant={statusVariant(job.status)}>
                      {job.status === "processing" && (
                        <Loader2 className="w-3 h-3 inline mr-1 animate-spin" strokeWidth={1.5} />
                      )}
                      {job.status}
                    </Badge>

                    {/* Download button for completed jobs */}
                    {job.status === "completed" && job._outputPaths && Object.keys(job._outputPaths).length > 0 && (
                      <button
                        onClick={(e) => {
                          const fmt = Object.keys(job._outputPaths!)[0];
                          handleDownload(job.id, fmt, job._outputPaths![fmt], e);
                        }}
                        className="p-1.5 transition-colors duration-100"
                        style={{ color: "var(--fg-tertiary)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-notion-blue)")}
                        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--fg-tertiary)")}
                        title={t.jobs.download}
                      >
                        <Download className="w-4 h-4" strokeWidth={1.5} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar for active jobs */}
                {(job.status === "processing" || job.status === "pending") && (
                  <div
                    className="mt-3 h-1.5 overflow-hidden"
                    style={{
                      background: "var(--bg-secondary)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <div
                      className="h-full transition-all duration-500"
                      style={{
                        width: `${job.progress || 0}%`,
                        background: "var(--color-notion-blue)",
                        borderRadius: "var(--radius-sm)",
                      }}
                    />
                  </div>
                )}
              </Card>
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
