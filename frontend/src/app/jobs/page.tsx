"use client";

import Link from "next/link";
import { List, FileText, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useJobs, useDeleteJob } from "@/lib/api/hooks";
import { formatDate, statusColor } from "@/lib/utils";

export default function JobsPage() {
  const { data, isLoading } = useJobs({ limit: 50 });
  const deleteJob = useDeleteJob();
  const jobList = data?.jobs || [];

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-slate-200 rounded-lg" />
        ))}
      </div>
    );
  }

  if (jobList.length === 0) {
    return (
      <EmptyState
        icon={List}
        title="No translation jobs yet"
        description="Upload a document to get started"
        action={
          <Link href="/translate">
            <Button>New Translation</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Translation Jobs</h1>
        <Link href="/translate">
          <Button size="sm">New Job</Button>
        </Link>
      </div>

      <div className="space-y-2">
        {jobList.map((job) => (
          <Link key={job.id} href={`/jobs/${job.id}`}>
            <Card className="px-5 py-4 hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="font-medium text-sm">
                      {job.source_filename}
                    </p>
                    <p className="text-xs text-slate-500">
                      {job.source_language}&rarr;{job.target_language} &middot;{" "}
                      {job.output_format} &middot; {formatDate(job.created_at)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {job.eqs && (
                    <Badge
                      variant={job.eqs.grade <= "B" ? "success" : "warning"}
                    >
                      EQS: {job.eqs.grade}
                    </Badge>
                  )}
                  {job.consistency && (
                    <Badge
                      variant={
                        job.consistency.passed ? "success" : "warning"
                      }
                    >
                      {Math.round(job.consistency.score * 100)}%
                    </Badge>
                  )}

                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColor(job.status)}`}
                  >
                    {job.status}
                  </span>

                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (confirm("Delete this job?"))
                        deleteJob.mutate(job.id);
                    }}
                    className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {(job.status === "processing" || job.status === "pending") && (
                <div className="mt-3 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${job.progress || 0}%` }}
                  />
                </div>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
