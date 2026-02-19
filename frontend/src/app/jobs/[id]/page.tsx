"use client";

import { use } from "react";
import {
  Download,
  FileText,
  Shield,
  Route,
  CheckCircle,
  LayoutGrid,
  ArrowLeft,
  ArrowRight,
  AlertTriangle,
  Clock,
  BookOpen,
} from "lucide-react";
import Link from "next/link";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useJob } from "@/lib/api/hooks";
import { jobs as jobsApi } from "@/lib/api/client";
import { formatDate, statusVariant } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

function DownloadButton({ jobId, format, filename }: { jobId: string; format: string; filename: string }) {
  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      await jobsApi.download(jobId, format, filename);
    } catch {
      // Download failed
    }
  };

  return (
    <button
      onClick={handleDownload}
      className="flex items-center justify-between p-3 no-underline transition-colors duration-100 w-full text-left"
      style={{
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-default)",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      <div className="flex items-center gap-3">
        <FileText className="w-5 h-5" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>{filename}</p>
          <p className="text-xs uppercase" style={{ color: "var(--fg-tertiary)" }}>{format}</p>
        </div>
      </div>
      <Download className="w-4 h-4" style={{ color: "var(--color-notion-blue)" }} strokeWidth={1.5} />
    </button>
  );
}

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: job, isLoading } = useJob(id);
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 skeleton" />
        <div className="h-40 skeleton" />
      </div>
    );
  }

  if (!job) {
    return <p style={{ color: "var(--fg-tertiary)" }}>{t.jobs.notFound}</p>;
  }

  // Derive outputs from V2 output_paths
  const outputs = job.status === "completed" && job._outputPaths
    ? Object.entries(job._outputPaths).map(([format, path]) => ({
        filename: path.split("/").pop() || `output.${format}`,
        format,
        download_url: jobsApi.getDownloadUrl(id, format),
      }))
    : [];

  // Grade colors
  const GRADE_COLORS: Record<string, string> = {
    A: "var(--color-notion-green)",
    B: "var(--color-notion-blue)",
    C: "var(--color-notion-yellow)",
    D: "var(--color-notion-orange)",
    F: "var(--color-notion-red)",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/jobs"
          className="text-sm flex items-center gap-1 mb-2 no-underline"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-3 h-3" /> {t.jobs.backToJobs}
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2">
              <FileText
                className="w-6 h-6"
                style={{ color: "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              {job.source_filename}
            </h1>
            <p className="mt-1" style={{ color: "var(--fg-secondary)" }}>
              {job.source_language}&rarr;{job.target_language} &middot;{" "}
              {job.output_format} &middot; {formatDate(job.created_at)}
            </p>
          </div>
          <Badge variant={statusVariant(job.status)}>
            {job.status === "processing" && (
              <Clock className="w-3 h-3 inline mr-1" strokeWidth={1.5} />
            )}
            {job.status}
          </Badge>
        </div>
      </div>

      {/* Progress */}
      {(job.status === "processing" || job.status === "pending") && (
        <Card className="px-5 py-4">
          <div className="flex items-center justify-between mb-2">
            <span
              className="text-sm font-medium"
              style={{ color: "var(--fg-primary)" }}
            >
              {job._currentStage || t.jobs.processing}
            </span>
            <span
              className="text-sm"
              style={{ color: "var(--fg-secondary)" }}
            >
              {Math.round(job.progress)}%
            </span>
          </div>
          <div
            className="h-2 overflow-hidden"
            style={{
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <div
              className="h-full transition-all duration-1000"
              style={{
                width: `${job.progress}%`,
                background: "var(--color-notion-blue)",
                borderRadius: "var(--radius-sm)",
              }}
            />
          </div>
        </Card>
      )}

      {/* Completed Summary */}
      {job.status === "completed" && job._qualityLevel && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <CheckCircle
              className="w-5 h-5"
              style={{ color: "var(--color-notion-green)" }}
              strokeWidth={1.5}
            />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.jobs.translationComplete}
              </p>
              <p className="text-xs" style={{ color: "var(--fg-secondary)" }}>
                {t.jobs.quality}: <span className="capitalize">{job._qualityLevel}</span>
                {job._qualityScore !== undefined && ` (${Math.round(job._qualityScore * 100)}%)`}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Error */}
      {job.status === "failed" && job.error && (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle
              className="w-5 h-5"
              style={{ color: "var(--color-notion-red)" }}
              strokeWidth={1.5}
            />
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.jobs.translationFailed}
              </p>
              <p className="text-xs" style={{ color: "var(--color-notion-red)" }}>
                {job.error}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Quality Intelligence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* EQS */}
        {job.eqs && (
          <Card>
            <CardHeader>
              <h3 className="text-[15px] font-semibold flex items-center gap-2">
                <Shield
                  className="w-4 h-4"
                  style={{ color: "var(--color-notion-blue)" }}
                  strokeWidth={1.5}
                />
                {t.jobs.extractionQuality}
              </h3>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-3">
                <span
                  className="text-3xl font-bold"
                  style={{
                    color:
                      GRADE_COLORS[job.eqs.grade] || "var(--fg-primary)",
                  }}
                >
                  {job.eqs.grade}
                </span>
                <span
                  className="text-sm"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {t.jobs.score}: {(job.eqs.score * 100).toFixed(0)}%
                </span>
              </div>
              <p
                className="mt-2 text-sm"
                style={{ color: "var(--fg-secondary)" }}
              >
                {job.eqs.recommendation}
              </p>
              <div className="mt-3 space-y-1.5">
                {Object.entries(job.eqs.signals || {}).map(
                  ([signal, value]) => (
                    <div
                      key={signal}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span
                        className="w-24 capitalize"
                        style={{ color: "var(--fg-tertiary)" }}
                      >
                        {signal.replace("_", " ")}
                      </span>
                      <div
                        className="flex-1 h-1.5 overflow-hidden"
                        style={{
                          background: "var(--bg-secondary)",
                          borderRadius: "var(--radius-sm)",
                        }}
                      >
                        <div
                          className="h-full"
                          style={{
                            width: `${(value as number) * 100}%`,
                            background: "var(--color-notion-blue)",
                            borderRadius: "var(--radius-sm)",
                          }}
                        />
                      </div>
                    </div>
                  ),
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* QAPR */}
        {job.qapr && (
          <Card>
            <CardHeader>
              <h3 className="text-[15px] font-semibold flex items-center gap-2">
                <Route
                  className="w-4 h-4"
                  style={{ color: "var(--color-notion-purple)" }}
                  strokeWidth={1.5}
                />
                {t.jobs.providerRouting}
              </h3>
            </CardHeader>
            <CardContent>
              <p
                className="text-lg font-semibold capitalize"
                style={{ color: "var(--fg-primary)" }}
              >
                {job.qapr.selected_provider}
              </p>
              <Badge variant="info" className="mt-1">
                {job.qapr.mode.replace("_", " ")}
              </Badge>
              <p
                className="mt-2 text-sm"
                style={{ color: "var(--fg-secondary)" }}
              >
                {job.qapr.reasoning}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Consistency */}
        {job.consistency && (
          <Card>
            <CardHeader>
              <h3 className="text-[15px] font-semibold flex items-center gap-2">
                <CheckCircle
                  className="w-4 h-4"
                  style={{ color: "var(--color-notion-green)" }}
                  strokeWidth={1.5}
                />
                {t.jobs.consistencyCheck}
              </h3>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span
                  className="text-2xl font-bold"
                  style={{ color: "var(--fg-primary)" }}
                >
                  {Math.round(job.consistency.score * 100)}%
                </span>
                <Badge
                  variant={job.consistency.passed ? "success" : "warning"}
                >
                  {job.consistency.passed ? t.jobs.passed : t.jobs.issuesFound}
                </Badge>
              </div>
              {job.consistency.issues?.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {job.consistency.issues.slice(0, 5).map((issue, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 text-xs"
                    >
                      <AlertTriangle
                        className="w-3 h-3 mt-0.5 shrink-0"
                        strokeWidth={1.5}
                        style={{
                          color:
                            issue.severity === "high"
                              ? "var(--color-notion-red)"
                              : issue.severity === "medium"
                                ? "var(--color-notion-yellow)"
                                : "var(--fg-tertiary)",
                        }}
                      />
                      <span style={{ color: "var(--fg-secondary)" }}>
                        {issue.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Layout DNA */}
        {job.layout_dna && (
          <Card>
            <CardHeader>
              <h3 className="text-[15px] font-semibold flex items-center gap-2">
                <LayoutGrid
                  className="w-4 h-4"
                  style={{ color: "var(--color-notion-orange)" }}
                  strokeWidth={1.5}
                />
                {t.jobs.documentStructure}
              </h3>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p
                    className="text-2xl font-bold"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {job.layout_dna.total_regions}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--fg-tertiary)" }}
                  >
                    {t.jobs.regions}
                  </p>
                </div>
                <div>
                  <p
                    className="text-2xl font-bold"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {job.layout_dna.tables}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--fg-tertiary)" }}
                  >
                    {t.jobs.tables}
                  </p>
                </div>
                <div>
                  <p
                    className="text-2xl font-bold"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {job.layout_dna.formulas}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--fg-tertiary)" }}
                  >
                    {t.jobs.formulas}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Read in App */}
      {job.status === "completed" && (
        <Link href={`/jobs/${id}/read`} className="block no-underline">
          <Card hover>
            <CardContent className="py-5">
              <div className="flex items-center gap-4">
                <div
                  className="w-10 h-10 flex items-center justify-center shrink-0"
                  style={{
                    borderRadius: "var(--radius-lg)",
                    background: "var(--accent-blue-bg)",
                  }}
                >
                  <BookOpen
                    className="w-5 h-5"
                    style={{ color: "var(--color-notion-blue)" }}
                    strokeWidth={1.5}
                  />
                </div>
                <div className="flex-1">
                  <h3
                    className="font-semibold text-[15px]"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {t.jobs.readInApp}
                  </h3>
                  <p
                    className="text-sm mt-0.5"
                    style={{ color: "var(--fg-tertiary)" }}
                  >
                    {t.jobs.readInAppDesc}
                  </p>
                </div>
                <ArrowRight
                  className="w-4 h-4 shrink-0"
                  style={{ color: "var(--fg-ghost)" }}
                  strokeWidth={1.5}
                />
              </div>
            </CardContent>
          </Card>
        </Link>
      )}

      {/* Download Outputs */}
      {outputs.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold flex items-center gap-2">
              <Download className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              {t.jobs.downloadOutputs}
            </h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {outputs.map((output) => (
                <DownloadButton
                  key={output.format}
                  jobId={id}
                  format={output.format}
                  filename={output.filename}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
