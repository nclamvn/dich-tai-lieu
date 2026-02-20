"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { List, FileText, Trash2, Download, CheckSquare, Square, Loader2, Search, XCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useJobs, useBulkDeleteJobs, useCancelJob } from "@/lib/api/hooks";
import { jobs as jobsApi } from "@/lib/api/client";
import { formatDate, statusVariant } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

const STATUS_FILTERS = ["all", "processing", "pending", "completed", "failed", "cancelled"] as const;
const JOBS_PER_PAGE = 20;

export default function JobsPage() {
  const { data, isLoading } = useJobs({ limit: 200 });
  const bulkDelete = useBulkDeleteJobs();
  const cancelJob = useCancelJob();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [visibleCount, setVisibleCount] = useState(JOBS_PER_PAGE);
  const allJobs = data?.jobs || [];
  const { t } = useLocale();

  // Client-side search + status filter
  const filteredJobs = useMemo(() => {
    let result = allJobs;
    if (statusFilter !== "all") {
      result = result.filter((j) => j.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (j) =>
          (j.source_filename || "").toLowerCase().includes(q) ||
          j.id.toLowerCase().includes(q) ||
          (j.source_language || "").toLowerCase().includes(q) ||
          (j.target_language || "").toLowerCase().includes(q),
      );
    }
    return result;
  }, [allJobs, statusFilter, search]);

  const visibleJobs = filteredJobs.slice(0, visibleCount);
  const hasMore = visibleCount < filteredJobs.length;

  // Status counts for filter badges
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: allJobs.length };
    for (const j of allJobs) {
      counts[j.status] = (counts[j.status] || 0) + 1;
    }
    return counts;
  }, [allJobs]);

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
    if (selected.size === visibleJobs.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(visibleJobs.map((j) => j.id)));
    }
  };

  const handleBulkDelete = () => {
    if (selected.size === 0) return;
    if (!confirm(`${t.jobs.delete} ${selected.size}?`)) return;
    bulkDelete.mutate([...selected], {
      onSuccess: () => setSelected(new Set()),
    });
  };

  const handleBulkCancel = async () => {
    const activeIds = [...selected].filter((id) => {
      const job = allJobs.find((j) => j.id === id);
      return job && (job.status === "processing" || job.status === "pending");
    });
    if (activeIds.length === 0) return;
    if (!confirm(`Cancel ${activeIds.length} active job(s)?`)) return;
    for (const id of activeIds) {
      cancelJob.mutate(id);
    }
    setSelected(new Set());
  };

  const handleBulkDownload = async () => {
    const completedJobs = [...selected]
      .map((id) => allJobs.find((j) => j.id === id))
      .filter((j) => j && j.status === "completed" && j._outputPaths && Object.keys(j._outputPaths).length > 0);
    for (const job of completedJobs) {
      if (!job?._outputPaths) continue;
      const fmt = Object.keys(job._outputPaths)[0];
      const filename = job._outputPaths[fmt].split("/").pop() || `output.${fmt}`;
      try {
        await jobsApi.download(job.id, fmt, filename);
      } catch { /* silently skip */ }
    }
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

  if (allJobs.length === 0) {
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

      {/* Search + Status Filters */}
      <div className="space-y-3">
        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
            style={{ color: "var(--fg-ghost)" }}
            strokeWidth={1.5}
          />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setVisibleCount(JOBS_PER_PAGE); }}
            placeholder={t.jobs.searchPlaceholder || "Search jobs..."}
            className="w-full py-2 text-sm"
            style={{
              paddingLeft: 36,
              paddingRight: 12,
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              color: "var(--fg-primary)",
            }}
          />
        </div>

        {/* Status filter pills */}
        <div className="flex gap-1.5 flex-wrap">
          {STATUS_FILTERS.map((s) => {
            const count = statusCounts[s] || 0;
            if (s !== "all" && count === 0) return null;
            const isActive = statusFilter === s;
            return (
              <button
                key={s}
                onClick={() => { setStatusFilter(s); setVisibleCount(JOBS_PER_PAGE); setSelected(new Set()); }}
                className="px-2.5 py-1 text-xs capitalize transition-colors duration-100"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: `1px solid ${isActive ? "var(--color-notion-blue)" : "var(--border-default)"}`,
                  background: isActive ? "var(--accent-blue-bg)" : "transparent",
                  color: isActive ? "var(--color-notion-blue)" : "var(--fg-secondary)",
                  fontWeight: isActive ? 500 : 400,
                }}
              >
                {s === "all" ? (t.jobs.filterAll || "All") : s} {count > 0 && <span style={{ opacity: 0.7 }}>({count})</span>}
              </button>
            );
          })}
        </div>
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
          {selected.size === visibleJobs.length && visibleJobs.length > 0 ? (
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
            {[...selected].some((id) => {
              const j = allJobs.find((job) => job.id === id);
              return j && (j.status === "processing" || j.status === "pending");
            }) && (
              <Button size="sm" variant="secondary" onClick={handleBulkCancel}>
                <XCircle className="w-3.5 h-3.5 mr-1" strokeWidth={1.5} />
                {t.jobs.cancel || "Cancel"}
              </Button>
            )}
            {[...selected].some((id) => {
              const j = allJobs.find((job) => job.id === id);
              return j && j.status === "completed" && j._outputPaths && Object.keys(j._outputPaths).length > 0;
            }) && (
              <Button size="sm" variant="secondary" onClick={handleBulkDownload}>
                <Download className="w-3.5 h-3.5 mr-1" strokeWidth={1.5} />
                {t.jobs.download || "Download"}
              </Button>
            )}
          </>
        )}
        <span className="ml-auto text-xs" style={{ color: "var(--fg-tertiary)" }}>
          {filteredJobs.length} {t.jobs.jobsCount || "jobs"}
        </span>
      </div>

      {/* Job List */}
      {visibleJobs.length === 0 ? (
        <p className="text-center py-8 text-sm" style={{ color: "var(--fg-tertiary)" }}>
          {t.jobs.noResults || "No matching jobs found"}
        </p>
      ) : (
        <div className="space-y-2">
          {visibleJobs.map((job) => (
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
      )}

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center py-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setVisibleCount((prev) => prev + JOBS_PER_PAGE)}
          >
            {t.jobs.loadMore || "Load More"} ({filteredJobs.length - visibleCount} {t.jobs.remaining || "remaining"})
          </Button>
        </div>
      )}
    </div>
  );
}
