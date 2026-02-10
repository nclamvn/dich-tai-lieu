"use client";

import { BookOpen } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";
import { useBookV2Projects, useDeleteBookV2 } from "@/lib/api/hooks";
import { BookCardV2 } from "./book-card";

export function BookListV2() {
  const { t } = useLocale();
  const { data, isLoading } = useBookV2Projects();
  const deleteBook = useDeleteBookV2();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 skeleton" style={{ borderRadius: "var(--radius-md)" }} />
        ))}
      </div>
    );
  }

  const projects = data?.items || [];

  if (projects.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <BookOpen
            className="w-8 h-8 mx-auto mb-3"
            style={{ color: "var(--fg-icon)" }}
            strokeWidth={1.5}
          />
          <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
            {t.writeV2.emptyTitle}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
            {t.writeV2.emptyDesc}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold" style={{ color: "var(--fg-primary)" }}>
        {t.writeV2.yourProjects}
        <span className="ml-2 text-sm font-normal" style={{ color: "var(--fg-tertiary)" }}>
          ({data?.total || projects.length})
        </span>
      </h2>
      {projects.map((project) => (
        <BookCardV2
          key={project.id}
          project={project}
          onDelete={(id) => deleteBook.mutate(id)}
        />
      ))}
    </div>
  );
}
