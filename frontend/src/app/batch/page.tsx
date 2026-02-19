"use client";

import { useState, useCallback, useRef } from "react";
import { useLocale } from "@/lib/i18n";
import {
  useBatches,
  useCreateBatch,
  useStartBatch,
  useBatchStatus,
  useCancelBatch,
  useDeleteBatch,
} from "@/lib/api/hooks";
import { batch as batchApi } from "@/lib/api/client";
import { SUPPORTED_LANGUAGES, OUTPUT_FORMATS } from "@/lib/api/types";
import type { BatchJob } from "@/lib/api/types";
import {
  FolderUp,
  Upload,
  X,
  FileText,
  Trash2,
  Download,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
} from "lucide-react";

const ACCEPTED_EXTS = [".pdf", ".docx", ".txt", ".md", ".epub"];

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function BatchPage() {
  const { t } = useLocale();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("vi");
  const [outputFormats, setOutputFormats] = useState<string[]>(["docx"]);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);

  const { data: batchList } = useBatches();
  const createBatch = useCreateBatch();
  const startBatch = useStartBatch();
  const { data: activeBatch } = useBatchStatus(activeBatchId);
  const cancelBatch = useCancelBatch();
  const deleteBatch = useDeleteBatch();

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      ACCEPTED_EXTS.some((ext) => f.name.toLowerCase().endsWith(ext)),
    );
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...dropped.filter((f) => !existing.has(f.name))].slice(0, 10);
    });
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...selected.filter((f) => !existing.has(f.name))].slice(0, 10);
    });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeFile = (name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const toggleFormat = (fmt: string) => {
    setOutputFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt],
    );
  };

  const handleStartBatch = async () => {
    if (files.length === 0) return;
    createBatch.mutate(
      { files, sourceLang, targetLang, outputFormats },
      {
        onSuccess: (data) => {
          setActiveBatchId(data.batch_id);
          setFiles([]);
          // Auto-start
          startBatch.mutate(data.batch_id);
        },
      },
    );
  };

  const handleDownload = (batchId: string) => {
    batchApi.download(batchId);
  };

  const isProcessing = activeBatch?.status === "processing" || activeBatch?.status === "pending";

  const batches = batchList?.batches ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1>{t.batch.title}</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--fg-secondary)" }}>
          {t.batch.subtitle}
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="cursor-pointer py-12 flex flex-col items-center justify-center gap-3 transition-colors"
        style={{
          borderRadius: "var(--radius-sm)",
          border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border-default)"}`,
          background: dragOver ? "rgba(59,130,246,0.05)" : "var(--bg-secondary)",
        }}
      >
        <Upload
          className="w-8 h-8"
          style={{ color: dragOver ? "var(--accent)" : "var(--fg-icon)" }}
          strokeWidth={1.5}
        />
        <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
          {t.batch.dropFiles}
        </p>
        <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
          {t.batch.dropHint}
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTS.join(",")}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Selected files */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div
            className="p-4 space-y-2"
            style={{
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--bg-primary)",
            }}
          >
            <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              {t.batch.selectedFiles} ({files.length})
            </p>
            {files.map((f) => (
              <div
                key={f.name}
                className="flex items-center justify-between py-1.5"
                style={{ borderBottom: "1px solid var(--border-default)" }}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 shrink-0" style={{ color: "var(--fg-icon)" }} />
                  <span className="text-sm truncate" style={{ color: "var(--fg-primary)" }}>
                    {f.name}
                  </span>
                  <span className="text-xs shrink-0" style={{ color: "var(--fg-secondary)" }}>
                    {formatFileSize(f.size)}
                  </span>
                </div>
                <button onClick={() => removeFile(f.name)} className="p-1 shrink-0">
                  <X className="w-3.5 h-3.5" style={{ color: "var(--fg-icon)" }} />
                </button>
              </div>
            ))}
          </div>

          {/* Settings */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.batch.sourceLang}
              </label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.batch.targetLang}
              </label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.batch.outputFormats}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {OUTPUT_FORMATS.map((fmt) => (
                  <button
                    key={fmt.value}
                    onClick={() => toggleFormat(fmt.value)}
                    className="px-2.5 py-1 text-xs"
                    style={{
                      borderRadius: "var(--radius-sm)",
                      border: `1px solid ${outputFormats.includes(fmt.value) ? "var(--accent)" : "var(--border-default)"}`,
                      background: outputFormats.includes(fmt.value) ? "rgba(59,130,246,0.1)" : "transparent",
                      color: outputFormats.includes(fmt.value) ? "var(--accent)" : "var(--fg-secondary)",
                    }}
                  >
                    {fmt.value}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={handleStartBatch}
            disabled={createBatch.isPending || files.length === 0}
            className="w-full py-2.5 text-sm font-medium text-white disabled:opacity-50"
            style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
          >
            {createBatch.isPending ? t.batch.processing : t.batch.startBatch}
          </button>
        </div>
      )}

      {/* Active batch progress */}
      {activeBatch && isProcessing && (
        <BatchProgress
          batch={activeBatch}
          onCancel={() => cancelBatch.mutate(activeBatch.batch_id)}
          t={t}
        />
      )}

      {/* Completed active batch */}
      {activeBatch && activeBatch.status === "completed" && (
        <div
          className="p-4 flex items-center justify-between"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid rgba(34,197,94,0.3)",
            background: "rgba(34,197,94,0.05)",
          }}
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" style={{ color: "rgb(34,197,94)" }} />
            <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              {t.batch.batchComplete}
            </span>
          </div>
          <button
            onClick={() => handleDownload(activeBatch.batch_id)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white"
            style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
          >
            <Download className="w-3.5 h-3.5" />
            {t.batch.downloadZip}
          </button>
        </div>
      )}

      {/* Batch history */}
      {batches.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium" style={{ color: "var(--fg-secondary)" }}>
            {t.batch.batchHistory}
          </h2>
          <div className="grid gap-2">
            {batches.map((b) => (
              <div
                key={b.batch_id}
                className="flex items-center justify-between p-3"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                }}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <BatchStatusIcon status={b.status} />
                  <div className="min-w-0">
                    <p className="text-sm truncate" style={{ color: "var(--fg-primary)" }}>
                      {b.total_files} {t.batch.files} · {b.source_language} → {b.target_language}
                    </p>
                    <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                      {new Date(b.created_at).toLocaleDateString()}
                      {b.status === "processing" && ` · ${b.overall_progress.toFixed(0)}%`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {b.zip_available && (
                    <button
                      onClick={() => handleDownload(b.batch_id)}
                      className="p-1.5"
                      style={{ borderRadius: "var(--radius-sm)" }}
                    >
                      <Download className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
                    </button>
                  )}
                  <button
                    onClick={() => {
                      if (confirm("Delete this batch?")) deleteBatch.mutate(b.batch_id);
                    }}
                    className="p-1.5"
                    style={{ borderRadius: "var(--radius-sm)" }}
                  >
                    <Trash2 className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {files.length === 0 && !activeBatch && batches.length === 0 && (
        <div className="py-8 text-center">
          <FolderUp
            className="w-12 h-12 mx-auto mb-3"
            style={{ color: "var(--fg-icon)" }}
            strokeWidth={1}
          />
          <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
            {t.batch.emptyTitle}
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
            {t.batch.emptyDesc}
          </p>
        </div>
      )}
    </div>
  );
}

function BatchProgress({ batch, onCancel, t }: { batch: BatchJob; onCancel: () => void; t: any }) {
  return (
    <div
      className="p-4 space-y-3"
      style={{
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--border-default)",
        background: "var(--bg-primary)",
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--accent)" }} />
          <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
            {t.batch.processing}
          </span>
        </div>
        <button
          onClick={onCancel}
          className="px-2.5 py-1 text-xs"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            color: "var(--fg-secondary)",
          }}
        >
          {t.batch.cancel}
        </button>
      </div>

      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs" style={{ color: "var(--fg-secondary)" }}>
            {batch.completed_files}/{batch.total_files} {t.batch.files}
          </span>
          <span className="text-xs font-medium" style={{ color: "var(--fg-primary)" }}>
            {batch.overall_progress.toFixed(0)}%
          </span>
        </div>
        <div
          className="h-2 overflow-hidden"
          style={{ borderRadius: "var(--radius-sm)", background: "var(--bg-secondary)" }}
        >
          <div
            className="h-full transition-all duration-500"
            style={{
              width: `${batch.overall_progress}%`,
              background: "var(--accent)",
              borderRadius: "var(--radius-sm)",
            }}
          />
        </div>
      </div>

      {/* Per-file status */}
      <div className="space-y-1">
        {batch.files.map((f) => (
          <div key={f.file_id} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2 min-w-0">
              <BatchStatusIcon status={f.status} size={14} />
              <span className="text-xs truncate" style={{ color: "var(--fg-primary)" }}>
                {f.filename}
              </span>
            </div>
            <span className="text-xs shrink-0" style={{ color: "var(--fg-secondary)" }}>
              {f.progress.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BatchStatusIcon({ status, size = 16 }: { status: string; size?: number }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 style={{ color: "rgb(34,197,94)", width: size, height: size }} />;
    case "failed":
      return <XCircle style={{ color: "rgb(239,68,68)", width: size, height: size }} />;
    case "processing":
      return <Loader2 className="animate-spin" style={{ color: "var(--accent)", width: size, height: size }} />;
    default:
      return <Clock style={{ color: "var(--fg-icon)", width: size, height: size }} />;
  }
}
