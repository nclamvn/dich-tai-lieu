"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useCreateJob, useProfiles, useGlossaries, useTranslationEngines } from "@/lib/api/hooks";
import { detectLanguage } from "@/lib/api/client";
import {
  SUPPORTED_LANGUAGES,
  OUTPUT_FORMATS,
  type TranslateRequest,
} from "@/lib/api/types";
import { Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

export default function TranslatePage() {
  const router = useRouter();
  const createJob = useCreateJob();
  const { t } = useLocale();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("vi");
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["docx"]);
  const [profileId, setProfileId] = useState("");
  const [selectedGlossaries, setSelectedGlossaries] = useState<string[]>([]);
  const [engineId, setEngineId] = useState("auto");
  const [detecting, setDetecting] = useState(false);

  const { data: profilesData } = useProfiles();
  const { data: enginesData } = useTranslationEngines();
  const { data: glossaryData } = useGlossaries(sourceLang, targetLang);

  const profileList = profilesData?.profiles || [];
  const glossaryList = glossaryData?.glossaries || [];

  const handleFileSelected = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setDetecting(true);
    try {
      const result = await detectLanguage(selectedFile);
      if (result.language && result.confidence > 0.5) {
        setSourceLang(result.language);
        // Auto-set target language different from source
        if (result.language === "vi") setTargetLang("en");
        else setTargetLang("vi");
      }
    } catch {
      // Detection failed, keep defaults
    } finally {
      setDetecting(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFileSelected(droppedFile);
    },
    [handleFileSelected],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const toggleFormat = (value: string) => {
    setSelectedFormats((prev) => {
      if (prev.includes(value)) {
        // Don't allow empty — keep at least one
        if (prev.length === 1) return prev;
        return prev.filter((f) => f !== value);
      }
      return [...prev, value];
    });
  };

  const handleSubmit = async () => {
    if (!file) return;

    const request: TranslateRequest = {
      source_language: sourceLang,
      target_language: targetLang,
      output_formats: selectedFormats,
      engine_id: engineId !== "auto" ? engineId : undefined,
      profile_id: profileId || undefined,
      glossary_ids:
        selectedGlossaries.length > 0 ? selectedGlossaries : undefined,
    };

    try {
      const job = await createJob.mutateAsync({ file, request });
      router.push(`/jobs/${job.id}`);
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1>{t.translate.title}</h1>
        <p className="mt-2" style={{ color: "var(--fg-secondary)" }}>
          {t.translate.subtitle}
        </p>
      </div>

      {/* File Upload */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <Upload className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            {t.translate.uploadDoc}
          </h3>
        </CardHeader>
        <CardContent>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={cn(
              "border-2 border-dashed p-8 text-center cursor-pointer transition-colors duration-100",
            )}
            style={{
              borderRadius: "var(--radius-lg)",
              borderColor: dragOver
                ? "var(--color-notion-blue)"
                : file
                  ? "var(--color-notion-green)"
                  : "var(--border-hover)",
              background: dragOver
                ? "var(--accent-blue-bg)"
                : file
                  ? "var(--accent-green-bg)"
                  : "transparent",
            }}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.md,.epub"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelected(f);
              }}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8" style={{ color: "var(--color-notion-green)" }} strokeWidth={1.5} />
                <div className="text-left">
                  <p className="font-medium" style={{ color: "var(--fg-primary)" }}>{file.name}</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm" style={{ color: "var(--color-notion-green)" }}>
                      {(file.size / 1024).toFixed(1)} KB — {t.translate.clickToChange}
                    </p>
                    {detecting && (
                      <span className="flex items-center gap-1 text-xs" style={{ color: "var(--color-notion-blue)" }}>
                        <Loader2 className="w-3 h-3 animate-spin" /> {t.translate.detectingLang}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 mx-auto mb-3" style={{ color: "var(--fg-tertiary)" }} strokeWidth={1.25} />
                <p className="font-medium" style={{ color: "var(--fg-primary)" }}>
                  {t.translate.dropFile}
                </p>
                <p className="text-sm mt-1" style={{ color: "var(--fg-tertiary)" }}>
                  {t.translate.fileTypes}
                </p>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Translation Settings */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            {t.translate.settings}
          </h3>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Language Selection */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-end">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.translate.sourceLang}
                {detecting && (
                  <span className="ml-2 text-xs font-normal" style={{ color: "var(--color-notion-blue)" }}>
                    {t.translate.autoDetecting}
                  </span>
                )}
              </label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="w-full"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>

            <ArrowRight className="w-5 h-5 mb-2" style={{ color: "var(--fg-ghost)" }} strokeWidth={1.5} />

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.translate.targetLang}
              </label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Output Format — Multi-select */}
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
              {t.translate.outputFormats}
            </label>
            <div className="flex gap-2 flex-wrap">
              {OUTPUT_FORMATS.map((f) => {
                const isSelected = selectedFormats.includes(f.value);
                return (
                  <button
                    key={f.value}
                    onClick={() => toggleFormat(f.value)}
                    className="px-3 py-1.5 text-sm transition-colors duration-100"
                    style={{
                      borderRadius: "var(--radius-sm)",
                      border: `1px solid ${isSelected ? "var(--color-notion-blue)" : "var(--border-default)"}`,
                      background: isSelected ? "var(--accent-blue-bg)" : "transparent",
                      color: isSelected ? "var(--color-notion-blue)" : "var(--fg-secondary)",
                      fontWeight: isSelected ? 500 : 400,
                    }}
                  >
                    {isSelected ? "\u2713 " : ""}{f.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Engine Selector */}
          {enginesData && enginesData.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                <span className="inline-flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
                  {t.translate.engine}
                </span>
              </label>
              <select
                value={engineId}
                onChange={(e) => setEngineId(e.target.value)}
                className="w-full"
              >
                <option value="auto">{t.translate.engineAuto}</option>
                {enginesData.map((eng) => (
                  <option key={eng.id} value={eng.id} disabled={!eng.available}>
                    {eng.offline ? "\uD83C\uDFE0" : "\u2601\uFE0F"} {eng.name}
                    {!eng.available ? ` (${t.translate.engineUnavailable})` : ""}
                  </option>
                ))}
              </select>
              {engineId !== "auto" && (() => {
                const sel = enginesData.find((e) => e.id === engineId);
                if (!sel) return null;
                return (
                  <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
                    {sel.cost_per_token === 0 ? t.translate.engineFree : t.translate.enginePaid}
                    {" \u00B7 "}
                    {sel.languages_count} {t.translate.engineLangs}
                    {sel.quality && <> {" \u00B7 "} {t.translate.engineQuality}: {sel.quality}</>}
                    {sel.offline && <> {" \u00B7 "} {t.translate.engineOffline}</>}
                  </p>
                );
              })()}
            </div>
          )}

          {/* Profile */}
          {profileList.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.translate.profile}
              </label>
              <select
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                className="w-full"
              >
                <option value="">{t.translate.profileAuto}</option>
                {profileList.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.description}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Glossaries */}
          {glossaryList.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--fg-primary)" }}>
                {t.translate.glossaries} ({sourceLang}&rarr;{targetLang})
              </label>
              <div className="space-y-1.5">
                {glossaryList.map((g) => (
                  <label
                    key={g.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedGlossaries.includes(g.id)}
                      onChange={(e) => {
                        setSelectedGlossaries((prev) =>
                          e.target.checked
                            ? [...prev, g.id]
                            : prev.filter((id) => id !== g.id),
                        );
                      }}
                    />
                    <span style={{ color: "var(--fg-primary)" }}>{g.name}</span>
                    <span style={{ color: "var(--fg-tertiary)" }}>
                      ({g.entry_count} {t.translate.terms})
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={!file}
          loading={createJob.isPending}
        >
          <Upload className="w-4 h-4 mr-2" strokeWidth={1.5} />
          {t.translate.startTranslation}
        </Button>
      </div>

      {createJob.isError && (
        <p className="text-sm" style={{ color: "var(--color-notion-red)" }}>
          {t.translate.error}: {(createJob.error as Error).message}
        </p>
      )}
    </div>
  );
}
