"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { useTM, useTMSegments, useAddTMSegment, useDeleteTMSegment, useImportTM } from "@/lib/api/hooks";
import { tm as tmApi } from "@/lib/api/client";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Search,
  X,
  Upload,
  Download,
  Database,
} from "lucide-react";

export default function TMDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: tmId } = use(params);
  const { t } = useLocale();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);
  const [newSource, setNewSource] = useState("");
  const [newTarget, setNewTarget] = useState("");

  const { data: tmData, isLoading: tmLoading } = useTM(tmId);
  const { data: segData, isLoading: segLoading } = useTMSegments(tmId, {
    page,
    limit: 50,
    search: search || undefined,
  });
  const addSegment = useAddTMSegment(tmId);
  const deleteSegment = useDeleteTMSegment(tmId);
  const importTM = useImportTM(tmId);

  const handleAdd = () => {
    if (!newSource.trim() || !newTarget.trim()) return;
    addSegment.mutate(
      { source_text: newSource.trim(), target_text: newTarget.trim() },
      {
        onSuccess: () => {
          setShowAdd(false);
          setNewSource("");
          setNewTarget("");
        },
      },
    );
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,.csv,.tmx";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) importTM.mutate(file);
    };
    input.click();
  };

  const handleExport = (format: string) => {
    window.open(tmApi.getExportUrl(tmId, format), "_blank");
  };

  if (tmLoading) {
    return (
      <div className="py-12 text-center text-sm" style={{ color: "var(--fg-secondary)" }}>
        {t.common.loading}
      </div>
    );
  }

  if (!tmData) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm" style={{ color: "var(--fg-secondary)" }}>
          {t.tm.notFound}
        </p>
        <Link
          href="/tm"
          className="text-sm mt-2 inline-block"
          style={{ color: "var(--accent)" }}
        >
          {t.tm.backToList}
        </Link>
      </div>
    );
  }

  const segments = segData?.segments ?? [];
  const totalPages = segData?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/tm"
          className="inline-flex items-center gap-1 text-sm no-underline mb-3"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-4 h-4" />
          {t.tm.backToList}
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2">
              <Database className="w-5 h-5" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              {tmData.name}
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
              {tmData.source_language} → {tmData.target_language}
              {" · "}
              {tmData.segment_count} {t.tm.segments}
              {" · "}
              {tmData.total_words.toLocaleString()} {t.tm.words}
              {tmData.domain !== "general" && ` · ${tmData.domain}`}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleImport}
              disabled={importTM.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
            >
              <Upload className="w-3.5 h-3.5" />
              {t.tm.import}
            </button>
            <button
              onClick={() => handleExport("json")}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
            >
              <Download className="w-3.5 h-3.5" />
              {t.tm.export}
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white"
              style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
            >
              <Plus className="w-3.5 h-3.5" />
              {t.tm.addSegment}
            </button>
          </div>
        </div>
      </div>

      {/* Add segment form */}
      {showAdd && (
        <div
          className="p-4 space-y-3"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--bg-secondary)",
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.tm.sourceText}
              </label>
              <textarea
                value={newSource}
                onChange={(e) => setNewSource(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 text-sm resize-none"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.tm.targetText}
              </label>
              <textarea
                value={newTarget}
                onChange={(e) => setNewTarget(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 text-sm resize-none"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 text-sm"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
            >
              {t.common.cancel}
            </button>
            <button
              onClick={handleAdd}
              disabled={!newSource.trim() || !newTarget.trim() || addSegment.isPending}
              className="px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
            >
              {t.common.create}
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
          style={{ color: "var(--fg-icon)" }}
        />
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder={t.tm.searchSegments}
          className="w-full pl-9 pr-8 py-2 text-sm"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--bg-primary)",
            color: "var(--fg-primary)",
          }}
        />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2">
            <X className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
          </button>
        )}
      </div>

      {/* Segments table */}
      {segLoading ? (
        <div className="py-8 text-center text-sm" style={{ color: "var(--fg-secondary)" }}>
          {t.common.loading}
        </div>
      ) : segments.length === 0 ? (
        <div className="py-12 text-center text-sm" style={{ color: "var(--fg-secondary)" }}>
          {t.common.noData}
        </div>
      ) : (
        <div
          className="overflow-x-auto"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
          }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-default)", background: "var(--bg-secondary)" }}>
                <th className="text-left px-4 py-2 font-medium" style={{ color: "var(--fg-secondary)" }}>
                  {t.tm.sourceText}
                </th>
                <th className="text-left px-4 py-2 font-medium" style={{ color: "var(--fg-secondary)" }}>
                  {t.tm.targetText}
                </th>
                <th className="text-center px-4 py-2 font-medium w-20" style={{ color: "var(--fg-secondary)" }}>
                  {t.tm.qualityScore}
                </th>
                <th className="text-center px-4 py-2 font-medium w-20" style={{ color: "var(--fg-secondary)" }}>
                  {t.tm.sourceType}
                </th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {segments.map((seg) => (
                <tr
                  key={seg.id}
                  style={{ borderBottom: "1px solid var(--border-default)" }}
                >
                  <td className="px-4 py-2.5" style={{ color: "var(--fg-primary)", maxWidth: "300px" }}>
                    <p className="truncate">{seg.source_text}</p>
                  </td>
                  <td className="px-4 py-2.5" style={{ color: "var(--fg-primary)", maxWidth: "300px" }}>
                    <p className="truncate">{seg.target_text}</p>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span
                      className="inline-block px-1.5 py-0.5 text-xs font-medium"
                      style={{
                        borderRadius: "var(--radius-sm)",
                        background: seg.quality_score >= 0.8 ? "rgba(34,197,94,0.15)" : "rgba(234,179,8,0.15)",
                        color: seg.quality_score >= 0.8 ? "rgb(34,197,94)" : "rgb(234,179,8)",
                      }}
                    >
                      {(seg.quality_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                      {seg.source_type}
                    </span>
                  </td>
                  <td className="px-2 py-2.5">
                    <button
                      onClick={() => deleteSegment.mutate(seg.id)}
                      className="p-1 transition-colors"
                      style={{ borderRadius: "var(--radius-sm)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-active)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <Trash2 className="w-3.5 h-3.5" style={{ color: "var(--fg-icon)" }} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm disabled:opacity-30"
            style={{
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              color: "var(--fg-secondary)",
            }}
          >
            Prev
          </button>
          <span className="text-sm" style={{ color: "var(--fg-secondary)" }}>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm disabled:opacity-30"
            style={{
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              color: "var(--fg-secondary)",
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
