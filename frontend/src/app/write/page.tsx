"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  PenTool,
  BookOpen,
  Loader2,
  Trash2,
  Lightbulb,
  FileEdit,
  Sparkles,
  Upload,
  X,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCreateBook, useBookProjects, useDeleteBook } from "@/lib/api/hooks";
import { bookWriter } from "@/lib/api/client";
import { SUPPORTED_LANGUAGES } from "@/lib/api/types";
import type { BookListItem, InputMode } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

function statusBadgeVariant(
  status: string,
): "default" | "success" | "warning" | "error" | "info" {
  const map: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
    analyzing: "info",
    architecting: "info",
    outlining: "info",
    outline_ready: "warning",
    writing: "info",
    enriching: "info",
    editing: "info",
    compiling: "info",
    complete: "success",
    failed: "error",
  };
  return map[status] || "default";
}

const ACTIVE_STATUSES = new Set([
  "analyzing", "architecting", "outlining", "writing", "enriching", "editing", "compiling",
]);

const MODE_CONFIG: { mode: InputMode; icon: typeof Lightbulb; color: string }[] = [
  { mode: "seeds", icon: Lightbulb, color: "var(--color-notion-yellow)" },
  { mode: "messy_draft", icon: FileEdit, color: "var(--color-notion-blue)" },
  { mode: "enrich", icon: Sparkles, color: "var(--color-notion-green)" },
];

export default function WritePage() {
  const router = useRouter();
  const createBook = useCreateBook();
  const deleteBook = useDeleteBook();
  const { data: projects } = useBookProjects();
  const { t } = useLocale();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [inputMode, setInputMode] = useState<InputMode>("seeds");
  const [ideas, setIdeas] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [draftFile, setDraftFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("vi");
  const [targetPages, setTargetPages] = useState(200);
  const [styleNotes, setStyleNotes] = useState("");
  const [uploading, setUploading] = useState(false);

  const modeLabels: Partial<Record<InputMode, { label: string; desc: string }>> = {
    seeds: { label: t.write.modeSeeds, desc: t.write.modeSeedsDesc },
    messy_draft: { label: t.write.modeMessyDraft, desc: t.write.modeMessyDraftDesc },
    enrich: { label: t.write.modeEnrich, desc: t.write.modeEnrichDesc },
  };

  const canSubmit = () => {
    if (inputMode === "seeds") {
      return ideas.trim().length >= 10;
    }
    return draftContent.trim().length >= 10 || draftFile !== null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["txt", "md", "docx"].includes(ext || "")) {
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      return;
    }
    setDraftFile(file);
  };

  const handleSubmit = async () => {
    if (!canSubmit()) return;

    try {
      let fileId: string | undefined;

      // Upload file if selected
      if (draftFile && inputMode !== "seeds") {
        setUploading(true);
        try {
          const result = await bookWriter.uploadDraft(draftFile);
          fileId = result.file_id;
        } finally {
          setUploading(false);
        }
      }

      const book = await createBook.mutateAsync({
        input_mode: inputMode,
        ideas: inputMode === "seeds" ? ideas.trim() : undefined,
        draft_content: inputMode !== "seeds" && draftContent.trim() ? draftContent.trim() : undefined,
        draft_file_id: fileId,
        language,
        target_pages: targetPages,
        output_formats: ["docx"],
        custom_instructions: styleNotes.trim() || undefined,
      });
      router.push(`/write/${book.id}`);
    } catch {
      // Error handled by mutation state
    }
  };

  const bookList: BookListItem[] = projects || [];

  return (
    <div className="space-y-8">
      <div>
        <h1>{t.write.title}</h1>
        <p className="mt-2" style={{ color: "var(--fg-secondary)" }}>
          {t.write.subtitle}
        </p>
      </div>

      {/* Input Mode Tabs */}
      <div
        className="grid grid-cols-3 gap-3"
      >
        {MODE_CONFIG.map(({ mode, icon: Icon, color }) => (
          <button
            key={mode}
            onClick={() => setInputMode(mode)}
            className="p-4 text-left transition-all duration-150"
            style={{
              border: inputMode === mode ? `2px solid ${color}` : "2px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              background: inputMode === mode ? "var(--bg-secondary)" : "var(--bg-primary)",
              cursor: "pointer",
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon
                className="w-4 h-4"
                style={{ color: inputMode === mode ? color : "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              <span
                className="text-sm font-semibold"
                style={{ color: inputMode === mode ? color : "var(--fg-primary)" }}
              >
                {modeLabels[mode]?.label}
              </span>
            </div>
            <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
              {modeLabels[mode]?.desc}
            </p>
          </button>
        ))}
      </div>

      {/* Create Form */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <PenTool className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            {inputMode === "seeds" ? t.write.seedsLabel : t.write.draftLabel}
          </h3>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Seeds mode: ideas textarea */}
          {inputMode === "seeds" && (
            <textarea
              value={ideas}
              onChange={(e) => setIdeas(e.target.value)}
              placeholder={t.write.seedsPlaceholder}
              rows={5}
              className="w-full resize-y"
              style={{ minHeight: "120px" }}
            />
          )}

          {/* Draft modes: draft textarea + file upload */}
          {inputMode !== "seeds" && (
            <>
              <textarea
                value={draftContent}
                onChange={(e) => setDraftContent(e.target.value)}
                placeholder={t.write.draftPlaceholder}
                rows={8}
                className="w-full resize-y"
                style={{ minHeight: "160px" }}
              />

              {/* File upload area */}
              <div
                className="p-4"
                style={{
                  border: "2px dashed var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--bg-secondary)",
                }}
              >
                {draftFile ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4" style={{ color: "var(--color-notion-blue)" }} strokeWidth={1.5} />
                      <div>
                        <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                          {draftFile.name}
                        </p>
                        <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
                          {(draftFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setDraftFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                      className="p-1"
                      style={{ borderRadius: "var(--radius-sm)" }}
                    >
                      <X className="w-4 h-4" style={{ color: "var(--fg-tertiary)" }} />
                    </button>
                  </div>
                ) : (
                  <div className="text-center">
                    <Upload
                      className="w-6 h-6 mx-auto mb-2"
                      style={{ color: "var(--fg-icon)" }}
                      strokeWidth={1.5}
                    />
                    <p className="text-sm" style={{ color: "var(--fg-secondary)" }}>
                      {t.write.uploadLabel}
                    </p>
                    <p className="text-xs mt-1 mb-3" style={{ color: "var(--fg-tertiary)" }}>
                      {t.write.uploadHint}
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
                      {t.write.uploadBtn}
                    </Button>
                    <p className="text-xs mt-2" style={{ color: "var(--fg-tertiary)" }}>
                      {t.write.uploadOr}
                    </p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>
            </>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.write.languageLabel}
              </label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full">
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.write.targetPagesLabel}
              </label>
              <select
                value={targetPages}
                onChange={(e) => setTargetPages(Number(e.target.value))}
                className="w-full"
              >
                {[50, 100, 150, 200, 300, 500].map((n) => (
                  <option key={n} value={n}>
                    {n} {t.write.pages}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.write.styleNotesLabel}
              </label>
              <input
                type="text"
                value={styleNotes}
                onChange={(e) => setStyleNotes(e.target.value)}
                placeholder={t.write.styleNotesPlaceholder}
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={!canSubmit()}
          loading={createBook.isPending || uploading}
        >
          <PenTool className="w-4 h-4 mr-2" strokeWidth={1.5} />
          {t.write.createBook}
        </Button>
      </div>

      {createBook.isError && (
        <p className="text-sm" style={{ color: "var(--color-notion-red)" }}>
          {(createBook.error as Error).message}
        </p>
      )}

      {/* Project List */}
      {bookList.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold" style={{ color: "var(--fg-primary)" }}>
            {t.write.yourProjects}
          </h2>
          {bookList.map((book) => (
            <Link key={book.id} href={`/write/${book.id}`} className="block no-underline">
              <Card hover>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <BookOpen
                        className="w-5 h-5 shrink-0"
                        style={{ color: "var(--fg-icon)" }}
                        strokeWidth={1.5}
                      />
                      <div className="min-w-0">
                        <p className="font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                          {book.title || `Book #${book.id.slice(0, 8)}`}
                        </p>
                        <p className="text-xs mt-0.5" style={{ color: "var(--fg-tertiary)" }}>
                          {book.chapter_count > 0 && `${book.chapter_count} ${t.write.chapters}`}
                          {book.total_words > 0 &&
                            ` \u00B7 ${book.total_words.toLocaleString()} ${t.write.words}`}
                          {book.created_at && ` \u00B7 ${formatDate(book.created_at)}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={statusBadgeVariant(book.status)}>
                        {ACTIVE_STATUSES.has(book.status) && (
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        )}
                        {book.status.replace("_", " ")}
                      </Badge>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          deleteBook.mutate(book.id);
                        }}
                        className="p-1 transition-colors duration-100"
                        style={{ borderRadius: "var(--radius-sm)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <Trash2
                          className="w-3.5 h-3.5"
                          style={{ color: "var(--fg-tertiary)" }}
                          strokeWidth={1.5}
                        />
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        !createBook.isPending && (
          <Card>
            <CardContent className="py-12 text-center">
              <BookOpen
                className="w-8 h-8 mx-auto mb-3"
                style={{ color: "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                {t.write.emptyTitle}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
                {t.write.emptyDesc}
              </p>
            </CardContent>
          </Card>
        )
      )}
    </div>
  );
}
