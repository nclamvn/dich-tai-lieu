"use client";

import { Loader2, CheckCircle, AlertTriangle, Pause } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n";
import type { BookV2Project } from "@/lib/api/types";

const AGENT_NAMES: Record<string, string> = {
  Analyst: "agentAnalyst",
  Architect: "agentArchitect",
  Outliner: "agentOutliner",
  Writer: "agentWriter",
  Expander: "agentExpander",
  Enricher: "agentEnricher",
  Editor: "agentEditor",
  QualityGate: "agentQualityGate",
  Publisher: "agentPublisher",
};

const AGENT_ORDER = [
  "Analyst", "Architect", "Outliner", "Writer",
  "Expander", "Enricher", "Editor", "QualityGate", "Publisher",
];

function statusBadgeVariant(status: string): "default" | "success" | "warning" | "error" | "info" {
  const map: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
    created: "default",
    analyzing: "info",
    architecting: "info",
    outlining: "info",
    writing: "info",
    expanding: "info",
    enriching: "info",
    editing: "info",
    quality_check: "info",
    publishing: "info",
    completed: "success",
    failed: "error",
    paused: "warning",
  };
  return map[status] || "default";
}

function getStatusLabel(status: string, t: any): string {
  const map: Record<string, string> = {
    created: t.writeV2.statusCreated,
    analyzing: t.writeV2.statusAnalyzing,
    architecting: t.writeV2.statusArchitecting,
    outlining: t.writeV2.statusOutlining,
    writing: t.writeV2.statusWriting,
    expanding: t.writeV2.statusExpanding,
    enriching: t.writeV2.statusEnriching,
    editing: t.writeV2.statusEditing,
    quality_check: t.writeV2.statusQualityCheck,
    publishing: t.writeV2.statusPublishing,
    completed: t.writeV2.statusCompleted,
    failed: t.writeV2.statusFailed,
    paused: t.writeV2.statusPaused,
  };
  return map[status] || status;
}

const TERMINAL = new Set(["completed", "failed", "paused"]);

export function BookProgress({ project }: { project: BookV2Project }) {
  const { t } = useLocale();
  const pct = Math.round(project.progress_percentage);
  const isTerminal = TERMINAL.has(project.status);

  return (
    <Card>
      <CardContent className="py-4 space-y-4">
        {/* Status row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {project.status === "completed" ? (
              <CheckCircle className="w-5 h-5" style={{ color: "var(--color-notion-green)" }} strokeWidth={1.5} />
            ) : project.status === "failed" ? (
              <AlertTriangle className="w-5 h-5" style={{ color: "var(--color-notion-red)" }} strokeWidth={1.5} />
            ) : project.status === "paused" ? (
              <Pause className="w-5 h-5" style={{ color: "var(--color-notion-yellow)" }} strokeWidth={1.5} />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--color-notion-blue)" }} />
            )}
            <div>
              <Badge variant={statusBadgeVariant(project.status)}>
                {getStatusLabel(project.status, t)}
              </Badge>
            </div>
          </div>
          <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
            {pct}%
          </span>
        </div>

        {/* Progress bar */}
        <div
          className="h-2 overflow-hidden"
          style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}
        >
          <div
            className="h-full transition-all duration-700"
            style={{
              width: `${pct}%`,
              background: project.status === "failed"
                ? "var(--color-notion-red)"
                : project.status === "completed"
                  ? "var(--color-notion-green)"
                  : "var(--color-notion-blue)",
              borderRadius: "var(--radius-sm)",
            }}
          />
        </div>

        {/* Agent info */}
        {!isTerminal && project.current_agent && (
          <div className="flex items-center justify-between text-xs" style={{ color: "var(--fg-tertiary)" }}>
            <span>
              {t.writeV2.currentAgent}: {(t.writeV2 as any)[AGENT_NAMES[project.current_agent] || ""] || project.current_agent}
            </span>
            {project.current_task && (
              <span className="truncate ml-4 max-w-[50%]">{project.current_task}</span>
            )}
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3 text-center text-xs">
          <div>
            <p className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {project.sections_completed}/{project.sections_total}
            </p>
            <p style={{ color: "var(--fg-tertiary)" }}>{t.writeV2.sectionsCompleted}</p>
          </div>
          <div>
            <p className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {Math.round(project.word_progress)}%
            </p>
            <p style={{ color: "var(--fg-tertiary)" }}>{t.writeV2.wordProgress}</p>
          </div>
          <div>
            <p className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {project.expansion_rounds}
            </p>
            <p style={{ color: "var(--fg-tertiary)" }}>{t.writeV2.expansionRounds}</p>
          </div>
        </div>

        {/* Agent timeline */}
        <AgentTimeline currentAgent={project.current_agent} status={project.status} />
      </CardContent>
    </Card>
  );
}

function AgentTimeline({ currentAgent, status }: { currentAgent: string; status: string }) {
  const { t } = useLocale();
  const currentIdx = AGENT_ORDER.indexOf(currentAgent);
  const isTerminal = TERMINAL.has(status);

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-1">
      {AGENT_ORDER.map((agent, idx) => {
        const isDone = isTerminal
          ? status === "completed"
          : currentIdx >= 0 && idx < currentIdx;
        const isCurrent = !isTerminal && agent === currentAgent;
        const label = (t.writeV2 as any)[AGENT_NAMES[agent] || ""] || agent;

        return (
          <div key={agent} className="flex items-center gap-1 shrink-0">
            <div
              className="flex items-center gap-1 px-2 py-1 text-[11px]"
              style={{
                borderRadius: "var(--radius-sm)",
                background: isCurrent
                  ? "var(--accent-blue-bg)"
                  : isDone
                    ? "var(--accent-green-bg)"
                    : "var(--bg-secondary)",
                color: isCurrent
                  ? "var(--color-notion-blue)"
                  : isDone
                    ? "var(--color-notion-green)"
                    : "var(--fg-tertiary)",
                fontWeight: isCurrent ? 600 : 400,
              }}
            >
              {isDone && <CheckCircle className="w-3 h-3" strokeWidth={1.5} />}
              {isCurrent && <Loader2 className="w-3 h-3 animate-spin" />}
              {label}
            </div>
            {idx < AGENT_ORDER.length - 1 && (
              <span className="text-[10px]" style={{ color: "var(--fg-ghost)" }}>&rarr;</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
