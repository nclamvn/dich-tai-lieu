"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { PenTool, Eye, Upload, FileText, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";
import { useCreateBookV2, useBookV2StructurePreview, useUploadDraftV2, useAnalyzeDraftV2 } from "@/lib/api/hooks";
import { SUPPORTED_LANGUAGES } from "@/lib/api/types";
import type { BookV2Genre, BookV2OutputFormat, DraftAnalysisResponse } from "@/lib/api/types";
import { StructurePreview } from "./structure-preview";

const GENRES: { value: BookV2Genre; labelKey: string }[] = [
  { value: "non-fiction", labelKey: "genreNonFiction" },
  { value: "fiction", labelKey: "genreFiction" },
  { value: "technical", labelKey: "genreTechnical" },
  { value: "business", labelKey: "genreBusiness" },
  { value: "self-help", labelKey: "genreSelfHelp" },
  { value: "academic", labelKey: "genreAcademic" },
  { value: "memoir", labelKey: "genreMemoir" },
  { value: "guide", labelKey: "genreGuide" },
];

const FORMAT_OPTIONS: { value: BookV2OutputFormat; label: string }[] = [
  { value: "docx", label: "Word (.docx)" },
  { value: "markdown", label: "Markdown (.md)" },
  { value: "html", label: "HTML (.html)" },
  { value: "pdf", label: "PDF (.pdf)" },
];

const PAGE_OPTIONS = [50, 100, 150, 200, 300, 500, 750, 1000];

type CreateMode = "scratch" | "draft";

export function BookCreateForm() {
  const router = useRouter();
  const { t } = useLocale();
  const createBook = useCreateBookV2();
  const uploadDraft = useUploadDraftV2();
  const analyzeDraft = useAnalyzeDraftV2();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<CreateMode>("scratch");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [targetPages, setTargetPages] = useState(200);
  const [genre, setGenre] = useState<BookV2Genre>("non-fiction");
  const [audience, setAudience] = useState("");
  const [authorName, setAuthorName] = useState("AI Publisher Pro");
  const [language, setLanguage] = useState("en");
  const [outputFormats, setOutputFormats] = useState<BookV2OutputFormat[]>(["docx", "markdown"]);
  const [showPreview, setShowPreview] = useState(false);

  // Draft state
  const [draftFileId, setDraftFileId] = useState<string | null>(null);
  const [draftFileName, setDraftFileName] = useState<string | null>(null);
  const [draftAnalysis, setDraftAnalysis] = useState<DraftAnalysisResponse | null>(null);

  const { data: preview, isLoading: previewLoading } = useBookV2StructurePreview(
    showPreview ? targetPages : null,
  );

  const canSubmit =
    title.trim().length >= 1 &&
    description.trim().length >= 10 &&
    (mode === "scratch" || draftFileId);

  const toggleFormat = (fmt: BookV2OutputFormat) => {
    setOutputFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt],
    );
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // Upload the file
      const uploadResult = await uploadDraft.mutateAsync(file);
      setDraftFileId(uploadResult.file_id);
      setDraftFileName(uploadResult.filename);

      // Analyze the draft
      const analysis = await analyzeDraft.mutateAsync(file);
      setDraftAnalysis(analysis);
    } catch {
      // Error handled by mutation state
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    try {
      const project = await createBook.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        target_pages: targetPages,
        genre,
        audience: audience.trim() || undefined,
        author_name: authorName.trim() || undefined,
        language,
        output_formats: outputFormats.length > 0 ? outputFormats : ["docx"],
        ...(mode === "draft" && draftFileId
          ? { continue_from_draft: true, draft_file_id: draftFileId }
          : {}),
      });
      router.push(`/write-v2/${project.id}`);
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode("scratch")}
          className="flex-1 px-4 py-3 text-left transition-all duration-100"
          style={{
            border: mode === "scratch"
              ? "2px solid var(--color-notion-blue)"
              : "2px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            background: mode === "scratch" ? "var(--accent-blue-bg)" : "var(--bg-secondary)",
            cursor: "pointer",
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <PenTool className="w-4 h-4" style={{ color: mode === "scratch" ? "var(--color-notion-blue)" : "var(--fg-icon)" }} strokeWidth={1.5} />
            <span
              className="text-sm font-medium"
              style={{ color: mode === "scratch" ? "var(--color-notion-blue)" : "var(--fg-primary)" }}
            >
              {t.writeV2.modeFromScratch}
            </span>
          </div>
          <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
            {t.writeV2.modeFromScratchDesc}
          </p>
        </button>
        <button
          onClick={() => setMode("draft")}
          className="flex-1 px-4 py-3 text-left transition-all duration-100"
          style={{
            border: mode === "draft"
              ? "2px solid var(--color-notion-blue)"
              : "2px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            background: mode === "draft" ? "var(--accent-blue-bg)" : "var(--bg-secondary)",
            cursor: "pointer",
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Upload className="w-4 h-4" style={{ color: mode === "draft" ? "var(--color-notion-blue)" : "var(--fg-icon)" }} strokeWidth={1.5} />
            <span
              className="text-sm font-medium"
              style={{ color: mode === "draft" ? "var(--color-notion-blue)" : "var(--fg-primary)" }}
            >
              {t.writeV2.modeFromDraft}
            </span>
          </div>
          <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
            {t.writeV2.modeFromDraftDesc}
          </p>
        </button>
      </div>

      <Card>
        <CardHeader>
          <h3
            className="text-[15px] font-semibold flex items-center gap-2"
            style={{ color: "var(--fg-primary)" }}
          >
            <PenTool className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            {t.writeV2.newBook}
          </h3>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Draft Upload (only in draft mode) */}
          {mode === "draft" && (
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.uploadDraft}
              </label>
              <div
                className="flex items-center gap-3 p-3"
                style={{
                  border: "2px dashed var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--bg-secondary)",
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.docx"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  loading={uploadDraft.isPending || analyzeDraft.isPending}
                >
                  <Upload className="w-4 h-4 mr-1.5" strokeWidth={1.5} />
                  {t.writeV2.chooseDraftFile}
                </Button>
                {draftFileName ? (
                  <span className="flex items-center gap-1.5 text-sm" style={{ color: "var(--color-notion-green)" }}>
                    <Check className="w-4 h-4" strokeWidth={2} />
                    {draftFileName}
                  </span>
                ) : (
                  <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
                    {t.writeV2.uploadDraftHint}
                  </span>
                )}
              </div>

              {(uploadDraft.isError || analyzeDraft.isError) && (
                <p className="text-xs mt-1" style={{ color: "var(--color-notion-red)" }}>
                  {((uploadDraft.error || analyzeDraft.error) as Error)?.message}
                </p>
              )}

              {/* Draft Analysis Result */}
              {draftAnalysis && (
                <div
                  className="mt-3 p-3 space-y-2"
                  style={{
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-default)",
                  }}
                >
                  <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
                    {t.writeV2.draftAnalysis}
                  </p>
                  <div className="flex gap-4 text-xs" style={{ color: "var(--fg-secondary)" }}>
                    <span>{draftAnalysis.total_chapters} {t.writeV2.draftChapters}</span>
                    <span>{draftAnalysis.total_words.toLocaleString()} {t.writeV2.draftWords}</span>
                  </div>
                  {draftAnalysis.chapters.length > 0 && (
                    <div className="space-y-1 mt-2">
                      {draftAnalysis.chapters.map((ch, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 text-xs"
                          style={{ color: "var(--fg-secondary)" }}
                        >
                          <FileText className="w-3 h-3 flex-shrink-0" strokeWidth={1.5} />
                          <span className="truncate">{ch.title}</span>
                          <span className="ml-auto flex-shrink-0" style={{ color: "var(--fg-tertiary)" }}>
                            {ch.word_count.toLocaleString()} {t.writeV2.words}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
              {t.writeV2.bookTitle}
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t.writeV2.bookTitlePlaceholder}
              className="w-full"
              maxLength={200}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
              {t.writeV2.description}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t.writeV2.descriptionPlaceholder}
              rows={4}
              className="w-full resize-y"
              style={{ minHeight: "100px" }}
              maxLength={5000}
            />
          </div>

          {/* Row: Target Pages, Genre, Language */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.targetPages}
              </label>
              <select
                value={targetPages}
                onChange={(e) => {
                  setTargetPages(Number(e.target.value));
                  setShowPreview(false);
                }}
                className="w-full"
              >
                {PAGE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n} {t.writeV2.pages}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.genre}
              </label>
              <select value={genre} onChange={(e) => setGenre(e.target.value as BookV2Genre)} className="w-full">
                {GENRES.map(({ value, labelKey }) => (
                  <option key={value} value={value}>
                    {(t.writeV2 as any)[labelKey] || value}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.language}
              </label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full">
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Audience + Author */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.audience}
              </label>
              <input
                type="text"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder={t.writeV2.audiencePlaceholder}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.writeV2.authorName}
              </label>
              <input
                type="text"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          {/* Output Formats */}
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
              {t.writeV2.outputFormats}
            </label>
            <div className="flex flex-wrap gap-2">
              {FORMAT_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => toggleFormat(value)}
                  className="px-3 py-1.5 text-sm transition-all duration-100"
                  style={{
                    border: outputFormats.includes(value)
                      ? "2px solid var(--color-notion-blue)"
                      : "2px solid var(--border-default)",
                    borderRadius: "var(--radius-md)",
                    background: outputFormats.includes(value) ? "var(--accent-blue-bg)" : "transparent",
                    color: outputFormats.includes(value) ? "var(--color-notion-blue)" : "var(--fg-secondary)",
                    cursor: "pointer",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Preview + Submit row */}
      <div className="flex justify-between items-center">
        <Button
          variant="secondary"
          onClick={() => setShowPreview(!showPreview)}
          loading={previewLoading}
        >
          <Eye className="w-4 h-4 mr-2" strokeWidth={1.5} />
          {t.writeV2.previewStructure}
        </Button>
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={!canSubmit}
          loading={createBook.isPending}
        >
          <PenTool className="w-4 h-4 mr-2" strokeWidth={1.5} />
          {t.writeV2.createBook}
        </Button>
      </div>

      {createBook.isError && (
        <p className="text-sm" style={{ color: "var(--color-notion-red)" }}>
          {(createBook.error as Error).message}
        </p>
      )}

      {/* Structure Preview */}
      {showPreview && preview && <StructurePreview data={preview} />}
    </div>
  );
}
