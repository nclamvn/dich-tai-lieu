"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldInput, FieldSelect, FieldToggle, FieldSlider, FieldSection } from "./form-fields";
import type { BookWriterSettingsConfig } from "@/lib/api/types";
import { RotateCcw, Save, Check } from "lucide-react";

export function BookWriterPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<BookWriterSettingsConfig>("book_writer");
  const update = useUpdateSettings<BookWriterSettingsConfig>("book_writer");
  const reset = useResetSettings("book_writer");
  const [form, setForm] = useState<BookWriterSettingsConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof BookWriterSettingsConfig>(k: K, v: BookWriterSettingsConfig[K]) =>
    setForm((prev) => (prev ? { ...prev, [k]: v } : prev));

  const handleSave = () => {
    update.mutate(form, {
      onSuccess: () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      },
    });
  };

  const handleReset = () => {
    if (!confirm(t.settings.resetConfirm)) return;
    reset.mutate(undefined, {
      onSuccess: (data) => setForm(data as unknown as BookWriterSettingsConfig),
    });
  };

  const GENRES = [
    { value: "non-fiction", label: "Non-Fiction" },
    { value: "fiction", label: "Fiction" },
    { value: "technical", label: "Technical" },
    { value: "business", label: "Business" },
    { value: "self-help", label: "Self-Help" },
    { value: "academic", label: "Academic" },
    { value: "memoir", label: "Memoir" },
    { value: "guide", label: "Guide" },
  ];

  const FORMATS = ["docx", "markdown", "pdf", "html"];

  const toggleFormat = (fmt: string) => {
    const current = form.default_output_formats;
    if (current.includes(fmt)) {
      if (current.length > 1) set("default_output_formats", current.filter((f) => f !== fmt));
    } else {
      set("default_output_formats", [...current, fmt]);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <FieldSection title="Defaults" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSelect
              label={t.settings.defaultGenre}
              value={form.default_genre}
              onChange={(v) => set("default_genre", v)}
              options={GENRES}
            />
            <FieldSelect
              label={t.settings.defaultLanguage}
              value={form.default_language}
              onChange={(v) => set("default_language", v)}
              options={[
                { value: "en", label: "English" },
                { value: "vi", label: "Vietnamese" },
                { value: "ja", label: "Japanese" },
                { value: "zh", label: "Chinese" },
              ]}
            />
          </div>

          <div>
            <label
              className="block text-sm font-medium mb-1.5"
              style={{ color: "var(--fg-primary)" }}
            >
              {t.settings.defaultFormats}
            </label>
            <div className="flex flex-wrap gap-2">
              {FORMATS.map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => toggleFormat(fmt)}
                  className="px-3 py-1.5 text-xs font-medium transition-colors"
                  style={{
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    background: form.default_output_formats.includes(fmt)
                      ? "var(--color-notion-blue)"
                      : "var(--bg-primary)",
                    color: form.default_output_formats.includes(fmt)
                      ? "white"
                      : "var(--fg-secondary)",
                  }}
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <FieldSection title="Structure" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSlider
              label={t.settings.wordsPerPage}
              value={form.words_per_page}
              onChange={(v) => set("words_per_page", v)}
              min={100}
              max={500}
              step={25}
            />
            <FieldSlider
              label={t.settings.sectionsPerChapter}
              value={form.sections_per_chapter}
              onChange={(v) => set("sections_per_chapter", v)}
              min={1}
              max={10}
            />
          </div>

          <FieldSlider
            label={t.settings.maxExpansionRounds}
            value={form.max_expansion_rounds}
            onChange={(v) => set("max_expansion_rounds", v)}
            min={1}
            max={10}
          />

          <FieldSection title="Pipeline" />

          <FieldToggle
            label={t.settings.enableEnrichment}
            checked={form.enable_enrichment}
            onChange={(v) => set("enable_enrichment", v)}
          />
          <FieldToggle
            label={t.settings.enableQualityCheck}
            checked={form.enable_quality_check}
            onChange={(v) => set("enable_quality_check", v)}
          />
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={handleReset} disabled={reset.isPending}>
          <RotateCcw className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
          {t.settings.reset}
        </Button>
        <Button variant="primary" size="lg" onClick={handleSave} loading={update.isPending} disabled={saved}>
          {saved ? (
            <><Check className="w-4 h-4 mr-1.5" strokeWidth={1.5} />{t.settings.saved}</>
          ) : (
            <><Save className="w-4 h-4 mr-1.5" strokeWidth={1.5} />{t.settings.save}</>
          )}
        </Button>
      </div>
    </div>
  );
}
