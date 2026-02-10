"use client";

import { BookOpen, Clock, FileText, Layers } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";
import type { BookV2StructurePreview } from "@/lib/api/types";

export function StructurePreview({ data }: { data: BookV2StructurePreview }) {
  const { t } = useLocale();

  const stats = [
    { label: t.writeV2.parts, value: data.num_parts, icon: Layers },
    { label: t.writeV2.chapters, value: data.total_chapters, icon: BookOpen },
    { label: t.writeV2.sections, value: data.total_sections, icon: FileText },
    {
      label: t.writeV2.estimatedTime,
      value: `${data.estimated_time_minutes} ${t.writeV2.minutes}`,
      icon: Clock,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <h3
          className="text-[15px] font-semibold flex items-center gap-2"
          style={{ color: "var(--fg-primary)" }}
        >
          <Layers className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
          {t.writeV2.structurePreview}
        </h3>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="p-3 text-center"
              style={{
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <Icon
                className="w-4 h-4 mx-auto mb-1"
                style={{ color: "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              <p
                className="text-lg font-semibold"
                style={{ color: "var(--fg-primary)" }}
              >
                {value}
              </p>
              <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
                {label}
              </p>
            </div>
          ))}
        </div>

        <div
          className="mt-4 grid grid-cols-2 gap-3 text-sm"
          style={{ color: "var(--fg-secondary)" }}
        >
          <div className="flex justify-between">
            <span>{t.writeV2.contentWords}:</span>
            <span className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {data.content_words.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span>{t.writeV2.targetPages}:</span>
            <span className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {data.content_pages}
            </span>
          </div>
          <div className="flex justify-between">
            <span>{t.writeV2.wordsPerChapter}:</span>
            <span className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {data.words_per_chapter.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span>{t.writeV2.wordsPerSection}:</span>
            <span className="font-medium" style={{ color: "var(--fg-primary)" }}>
              {data.words_per_section.toLocaleString()}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
