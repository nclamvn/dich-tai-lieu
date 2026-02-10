"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useBookV2ReaderContent } from "@/lib/api/hooks";
import { useLocale } from "@/lib/i18n";

export default function BookV2ReadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: content, isLoading, error } = useBookV2ReaderContent(id);
  const { t } = useLocale();
  const [currentChapter, setCurrentChapter] = useState(0);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-8 text-center">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 mx-auto skeleton" />
          <div className="h-4 w-64 mx-auto skeleton" />
          <div className="h-96 skeleton" />
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="max-w-3xl mx-auto py-8 text-center">
        <p style={{ color: "var(--fg-tertiary)" }}>Unable to load book content</p>
        <Link href={`/write-v2/${id}`} className="text-sm mt-2 inline-block" style={{ color: "var(--color-notion-blue)" }}>
          {t.writeV2.backToBooks}
        </Link>
      </div>
    );
  }

  const chapters = content.chapters || [];
  const chapter = chapters[currentChapter];
  const hasPrev = currentChapter > 0;
  const hasNext = currentChapter < chapters.length - 1;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          href={`/write-v2/${id}`}
          className="text-sm flex items-center gap-1 mb-3 no-underline"
          style={{ color: "var(--fg-secondary)" }}
        >
          <ArrowLeft className="w-3 h-3" /> {t.writeV2.backToBooks}
        </Link>
        <h1 className="flex items-center gap-2">
          <BookOpen className="w-6 h-6" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
          {content.title}
        </h1>
        {content.author && (
          <p className="text-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
            by {content.author}
          </p>
        )}
      </div>

      {/* Chapter navigation */}
      <div className="flex items-center justify-between mb-4">
        <select
          value={currentChapter}
          onChange={(e) => setCurrentChapter(Number(e.target.value))}
          className="text-sm max-w-xs"
        >
          {chapters.map((ch, idx) => (
            <option key={idx} value={idx}>
              {ch.title}
            </option>
          ))}
        </select>
        <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
          {currentChapter + 1} / {chapters.length}
        </span>
      </div>

      {/* Content */}
      {chapter && (
        <Card>
          <CardContent className="py-8 px-6 md:px-10">
            <h2
              className="text-xl font-semibold mb-6"
              style={{ color: "var(--fg-primary)" }}
            >
              {chapter.title}
            </h2>
            <div
              className="prose prose-sm max-w-none leading-relaxed"
              style={{ color: "var(--fg-secondary)" }}
              dangerouslySetInnerHTML={{ __html: chapter.content }}
            />
          </CardContent>
        </Card>
      )}

      {/* Prev/Next navigation */}
      <div className="flex justify-between mt-6 mb-12">
        <Button
          variant="secondary"
          disabled={!hasPrev}
          onClick={() => {
            setCurrentChapter((c) => c - 1);
            window.scrollTo(0, 0);
          }}
        >
          <ChevronLeft className="w-4 h-4 mr-1" strokeWidth={1.5} />
          Previous
        </Button>
        <Button
          variant="secondary"
          disabled={!hasNext}
          onClick={() => {
            setCurrentChapter((c) => c + 1);
            window.scrollTo(0, 0);
          }}
        >
          Next
          <ChevronRight className="w-4 h-4 ml-1" strokeWidth={1.5} />
        </Button>
      </div>
    </div>
  );
}
