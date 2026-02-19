"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldInput, FieldToggle, FieldSlider, FieldSection } from "./form-fields";
import type { TranslationSettingsConfig } from "@/lib/api/types";
import { RotateCcw, Save, Check } from "lucide-react";

export function TranslationPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<TranslationSettingsConfig>("translation");
  const update = useUpdateSettings<TranslationSettingsConfig>("translation");
  const reset = useResetSettings("translation");
  const [form, setForm] = useState<TranslationSettingsConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3, 4].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof TranslationSettingsConfig>(k: K, v: TranslationSettingsConfig[K]) =>
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
      onSuccess: (data) => setForm(data as unknown as TranslationSettingsConfig),
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <FieldSection title="Performance" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSlider
              label={t.settings.concurrency}
              value={form.concurrency}
              onChange={(v) => set("concurrency", v)}
              min={1}
              max={20}
              hint={t.settings.concurrencyHint}
            />
            <FieldInput
              label={t.settings.chunkSize}
              type="number"
              value={form.chunk_size}
              onChange={(v) => set("chunk_size", Number(v))}
              min={500}
              max={10000}
              hint={t.settings.chunkSizeHint}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldInput
              label={t.settings.contextWindow}
              type="number"
              value={form.context_window}
              onChange={(v) => set("context_window", Number(v))}
              min={0}
              max={3000}
            />
            <FieldInput
              label={t.settings.maxRetries}
              type="number"
              value={form.max_retries}
              onChange={(v) => set("max_retries", Number(v))}
              min={1}
              max={20}
            />
          </div>

          <FieldInput
            label={t.settings.retryDelay}
            type="number"
            value={form.retry_delay}
            onChange={(v) => set("retry_delay", Number(v))}
            min={1}
            max={30}
          />

          <FieldSection title="Caching" />

          <FieldToggle
            label={t.settings.cacheEnabled}
            checked={form.cache_enabled}
            onChange={(v) => set("cache_enabled", v)}
          />
          <FieldToggle
            label={t.settings.chunkCacheEnabled}
            checked={form.chunk_cache_enabled}
            onChange={(v) => set("chunk_cache_enabled", v)}
          />
          <FieldInput
            label={t.settings.chunkCacheTtl}
            type="number"
            value={form.chunk_cache_ttl_days}
            onChange={(v) => set("chunk_cache_ttl_days", Number(v))}
            min={1}
          />
          <FieldToggle
            label={t.settings.checkpointEnabled}
            checked={form.checkpoint_enabled}
            onChange={(v) => set("checkpoint_enabled", v)}
          />
          <FieldInput
            label={t.settings.checkpointInterval}
            type="number"
            value={form.checkpoint_interval}
            onChange={(v) => set("checkpoint_interval", Number(v))}
            min={1}
          />

          <FieldSection title="Quality" />

          <FieldToggle
            label={t.settings.tmEnabled}
            checked={form.tm_enabled}
            onChange={(v) => set("tm_enabled", v)}
          />
          <FieldSlider
            label={t.settings.tmThreshold}
            value={form.tm_fuzzy_threshold}
            onChange={(v) => set("tm_fuzzy_threshold", v)}
            min={0.5}
            max={1.0}
            step={0.05}
          />
          <FieldToggle
            label={t.settings.glossaryEnabled}
            checked={form.glossary_enabled}
            onChange={(v) => set("glossary_enabled", v)}
          />
          <FieldToggle
            label={t.settings.qualityValidation}
            checked={form.quality_validation}
            onChange={(v) => set("quality_validation", v)}
          />
          <FieldSlider
            label={t.settings.qualityThreshold}
            value={form.quality_threshold}
            onChange={(v) => set("quality_threshold", v)}
            min={0}
            max={1}
            step={0.05}
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
