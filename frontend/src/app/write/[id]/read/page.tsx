"use client";

import { use } from "react";
import { ReaderLayout } from "@/components/reader/reader-layout";
import { useBookReaderContent, useBookProject } from "@/lib/api/hooks";
import { bookWriter } from "@/lib/api/client";
import { FileText, BookOpen, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";

export default function BookReaderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: content, isLoading, error } = useBookReaderContent(id);
  const { data: book } = useBookProject(id);
  const { t } = useLocale();

  const downloadUrl = book?.status === "complete"
    ? bookWriter.getDownloadUrl(id, "docx")
    : undefined;

  if (isLoading) {
    return (
      <div
        className="h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center">
          <BookOpen
            className="w-10 h-10 mx-auto mb-4 animate-pulse"
            style={{ color: "var(--fg-ghost)" }}
            strokeWidth={1.25}
          />
          <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>
            {t.reader.preparingDoc}
          </p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div
        className="h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center max-w-[320px]">
          <AlertTriangle
            className="w-10 h-10 mx-auto mb-4"
            style={{ color: "var(--color-notion-yellow)" }}
            strokeWidth={1.25}
          />
          <h2
            className="text-xl mb-2"
            style={{
              color: "var(--fg-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            {t.reader.unableToLoad}
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--fg-tertiary)" }}>
            {book?.status !== "complete"
              ? t.reader.jobNotCompleted
              : t.reader.contentNotLoaded}
          </p>
          <Link
            href={`/write/${id}`}
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded no-underline"
            style={{
              background: "var(--bg-secondary)",
              color: "var(--fg-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            {t.write.backToBooks}
          </Link>
        </div>
      </div>
    );
  }

  if (content.chapters.length === 0) {
    return (
      <div
        className="h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center max-w-[320px]">
          <FileText
            className="w-10 h-10 mx-auto mb-4"
            style={{ color: "var(--fg-ghost)" }}
            strokeWidth={1.25}
          />
          <h2
            className="text-xl mb-2"
            style={{
              color: "var(--fg-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            {t.reader.noContent}
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--fg-tertiary)" }}>
            {t.reader.emptyDoc}
          </p>
          <Link
            href={`/write/${id}`}
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded no-underline"
            style={{
              background: "var(--bg-secondary)",
              color: "var(--fg-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            {t.write.backToBooks}
          </Link>
        </div>
      </div>
    );
  }

  return <ReaderLayout content={content} downloadUrl={downloadUrl} />;
}
