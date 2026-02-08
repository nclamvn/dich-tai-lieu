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
  AlertTriangle,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useJob, useJobOutputs } from "@/lib/api/hooks";
import { jobs as jobsApi } from "@/lib/api/client";
import { formatDate, gradeColor, cn } from "@/lib/utils";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: job, isLoading } = useJob(id);
  const { data: outputsData } = useJobOutputs(
    job?.status === "completed" ? id : null,
  );

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="h-40 bg-slate-200 rounded-lg" />
      </div>
    );
  }

  if (!job) {
    return <p className="text-slate-500">Job not found</p>;
  }

  const outputs = outputsData?.outputs || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/jobs"
          className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1 mb-2"
        >
          <ArrowLeft className="w-3 h-3" /> Back to Jobs
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <FileText className="w-6 h-6" />
              {job.source_filename}
            </h1>
            <p className="text-slate-500 mt-1">
              {job.source_language}&rarr;{job.target_language} &middot;{" "}
              {job.output_format} &middot; {formatDate(job.created_at)}
            </p>
          </div>
          <span
            className={`px-3 py-1.5 rounded-full text-sm font-medium ${
              job.status === "completed"
                ? "bg-green-100 text-green-800"
                : job.status === "processing"
                  ? "bg-blue-100 text-blue-800"
                  : job.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : "bg-slate-100 text-slate-800"
            }`}
          >
            {job.status === "processing" && (
              <Clock className="w-3 h-3 inline mr-1" />
            )}
            {job.status}
          </span>
        </div>
      </div>

      {/* Progress */}
      {(job.status === "processing" || job.status === "pending") && (
        <Card className="px-5 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Processing...</span>
            <span className="text-sm text-slate-500">{job.progress}%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-1000"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </Card>
      )}

      {/* Quality Intelligence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* EQS */}
        {job.eqs && (
          <Card>
            <CardHeader>
              <h3 className="font-semibold flex items-center gap-2 text-sm">
                <Shield className="w-4 h-4 text-blue-500" />
                Extraction Quality
              </h3>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-3">
                <span
                  className={cn(
                    "text-3xl font-bold",
                    gradeColor(job.eqs.grade),
                  )}
                >
                  {job.eqs.grade}
                </span>
                <span className="text-sm text-slate-500">
                  Score: {(job.eqs.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {job.eqs.recommendation}
              </p>
              <div className="mt-3 space-y-1.5">
                {Object.entries(job.eqs.signals || {}).map(
                  ([signal, value]) => (
                    <div
                      key={signal}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span className="w-24 text-slate-500 capitalize">
                        {signal.replace("_", " ")}
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{
                            width: `${(value as number) * 100}%`,
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
              <h3 className="font-semibold flex items-center gap-2 text-sm">
                <Route className="w-4 h-4 text-purple-500" />
                Provider Routing
              </h3>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold capitalize">
                {job.qapr.selected_provider}
              </p>
              <Badge variant="info" className="mt-1">
                {job.qapr.mode.replace("_", " ")}
              </Badge>
              <p className="mt-2 text-sm text-slate-600">
                {job.qapr.reasoning}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Consistency */}
        {job.consistency && (
          <Card>
            <CardHeader>
              <h3 className="font-semibold flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Consistency Check
              </h3>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold">
                  {Math.round(job.consistency.score * 100)}%
                </span>
                <Badge
                  variant={job.consistency.passed ? "success" : "warning"}
                >
                  {job.consistency.passed ? "Passed" : "Issues Found"}
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
                        className={cn(
                          "w-3 h-3 mt-0.5 flex-shrink-0",
                          issue.severity === "high"
                            ? "text-red-500"
                            : issue.severity === "medium"
                              ? "text-yellow-500"
                              : "text-slate-400",
                        )}
                      />
                      <span className="text-slate-600">
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
              <h3 className="font-semibold flex items-center gap-2 text-sm">
                <LayoutGrid className="w-4 h-4 text-orange-500" />
                Document Structure
              </h3>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-2xl font-bold">
                    {job.layout_dna.total_regions}
                  </p>
                  <p className="text-xs text-slate-500">Regions</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {job.layout_dna.tables}
                  </p>
                  <p className="text-xs text-slate-500">Tables</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {job.layout_dna.formulas}
                  </p>
                  <p className="text-xs text-slate-500">Formulas</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Download Outputs */}
      {outputs.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Download Outputs</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {outputs.map((output) => (
                <a
                  key={output.filename}
                  href={jobsApi.getDownloadUrl(id, output.filename)}
                  download
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-sm font-medium">
                        {output.filename}
                      </p>
                      <p className="text-xs text-slate-500">
                        {(output.size_bytes / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <Download className="w-4 h-4 text-blue-500" />
                </a>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
