"use client";

import { useIllustrationPlan } from "@/lib/api/hooks";
import { Badge } from "@/components/ui/badge";
import type { ImagePlacement, GalleryGroup, LayoutMode } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n";

interface IllustrationPlanViewerProps {
  projectId: string;
}

const LAYOUT_BADGE: Record<string, "default" | "info" | "success" | "warning"> = {
  full_page: "default",
  inline: "info",
  float_top: "success",
  gallery: "warning",
  margin: "default",
};

export function IllustrationPlanViewer({ projectId }: IllustrationPlanViewerProps) {
  const { t } = useLocale();
  const { data: plan, isLoading, error } = useIllustrationPlan(projectId);
  const tw = t.writeV2;

  if (isLoading) {
    return (
      <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>
        {tw.loadingPlan}
      </p>
    );
  }

  if (error || !plan) {
    return (
      <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>
        {tw.noPlanYet}
      </p>
    );
  }

  // Group placements by chapter
  const byChapter = new Map<number, ImagePlacement[]>();
  for (const p of plan.placements) {
    const list = byChapter.get(p.chapter_index) || [];
    list.push(p);
    byChapter.set(p.chapter_index, list);
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3
          className="text-sm font-semibold"
          style={{ color: "var(--fg-primary)" }}
        >
          {tw.illustrationPlan}
        </h3>
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="info">{plan.total_placed} {tw.placed}</Badge>
          {plan.total_unmatched > 0 && (
            <Badge variant="warning">{plan.total_unmatched} {tw.unmatched}</Badge>
          )}
        </div>
      </div>

      {/* Per-chapter view */}
      {Array.from(byChapter.entries())
        .sort(([a], [b]) => a - b)
        .map(([chIdx, placements]) => (
          <div
            key={chIdx}
            className="rounded-md p-3 space-y-2"
            style={{ border: "1px solid var(--border-default)" }}
          >
            <h4
              className="text-sm font-medium"
              style={{ color: "var(--fg-primary)" }}
            >
              {tw.chapter} {chIdx + 1}
            </h4>
            <div className="space-y-1.5">
              {placements.map((p, i) => (
                <div
                  key={`${p.image_id}-${i}`}
                  className="flex items-center gap-3 text-xs rounded-md p-2"
                  style={{ background: "var(--bg-secondary)" }}
                >
                  <div className="flex-1 min-w-0">
                    <p
                      className="font-medium truncate"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {p.caption || p.image_id}
                    </p>
                    <p style={{ color: "var(--fg-tertiary)" }}>
                      {tw.section} {p.section_index + 1} | {tw.relevance}: {(p.relevance_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <Badge variant={LAYOUT_BADGE[p.layout_mode] || "default"}>
                    {p.layout_mode}
                  </Badge>
                  <span
                    className="whitespace-nowrap"
                    style={{ color: "var(--fg-tertiary)" }}
                  >
                    {p.size}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

      {/* Galleries */}
      {plan.galleries.length > 0 && (
        <div
          className="rounded-md p-3 space-y-2"
          style={{ border: "1px solid var(--border-default)" }}
        >
          <h4
            className="text-sm font-medium"
            style={{ color: "var(--fg-primary)" }}
          >
            {tw.galleries}
          </h4>
          {plan.galleries.map((g) => (
            <div
              key={g.group_id}
              className="text-xs rounded-md p-2"
              style={{ background: "var(--accent-yellow-bg, var(--bg-secondary))" }}
            >
              <p className="font-medium" style={{ color: "var(--fg-primary)" }}>
                {g.title}
              </p>
              <p style={{ color: "var(--fg-secondary)" }}>
                {tw.chapter} {g.chapter_index + 1} | {g.image_ids.length} {tw.images}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Unmatched warnings */}
      {plan.unmatched_image_ids.length > 0 && (
        <div
          className="rounded-md p-3 text-xs"
          style={{
            background: "var(--accent-red-bg)",
            border: "1px solid var(--color-notion-red)",
          }}
        >
          <p className="font-medium" style={{ color: "var(--color-notion-red)" }}>
            {plan.unmatched_image_ids.length} {tw.unmatchedWarning}
          </p>
          <p className="mt-1" style={{ color: "var(--fg-secondary)" }}>
            {tw.unmatchedHint}
          </p>
        </div>
      )}
    </div>
  );
}
