"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldSelect, FieldToggle, FieldInput, FieldSection } from "./form-fields";
import type { ExportSettingsConfig } from "@/lib/api/types";
import { RotateCcw, Save, Check } from "lucide-react";

export function ExportPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<ExportSettingsConfig>("export");
  const update = useUpdateSettings<ExportSettingsConfig>("export");
  const reset = useResetSettings("export");
  const [form, setForm] = useState<ExportSettingsConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof ExportSettingsConfig>(k: K, v: ExportSettingsConfig[K]) =>
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
      onSuccess: (data) => setForm(data as unknown as ExportSettingsConfig),
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <FieldSection title="Output" />

          <FieldSelect
            label={t.settings.defaultFormat}
            value={form.default_format}
            onChange={(v) => set("default_format", v)}
            options={[
              { value: "docx", label: "Word (.docx)" },
              { value: "pdf", label: "PDF (.pdf)" },
              { value: "epub", label: "EPUB (.epub)" },
              { value: "markdown", label: "Markdown (.md)" },
              { value: "txt", label: "Plain Text (.txt)" },
            ]}
          />

          <FieldToggle
            label={t.settings.enableBeautification}
            description="3-stage pipeline: sanitize, style, polish"
            checked={form.enable_beautification}
            onChange={(v) => set("enable_beautification", v)}
          />
          <FieldToggle
            label={t.settings.enableBookLayout}
            description="Cover page, TOC, page numbers, headers (experimental)"
            checked={form.enable_advanced_book_layout}
            onChange={(v) => set("enable_advanced_book_layout", v)}
          />

          <FieldSection title="Streaming" />

          <FieldToggle
            label={t.settings.streamingEnabled}
            description="Memory-efficient batch processing"
            checked={form.streaming_enabled}
            onChange={(v) => set("streaming_enabled", v)}
          />
          <FieldInput
            label={t.settings.streamingBatchSize}
            type="number"
            value={form.streaming_batch_size}
            onChange={(v) => set("streaming_batch_size", Number(v))}
            min={10}
            max={1000}
          />

          <FieldSection title="Uploads" />

          <FieldInput
            label={t.settings.maxUploadSize}
            type="number"
            value={form.max_upload_size_mb}
            onChange={(v) => set("max_upload_size_mb", Number(v))}
            min={1}
            max={500}
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
