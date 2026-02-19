"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldInput, FieldSelect, FieldSection } from "./form-fields";
import type { GeneralSettings } from "@/lib/api/types";
import { RotateCcw, Save, Check } from "lucide-react";

export function GeneralPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<GeneralSettings>("general");
  const update = useUpdateSettings<GeneralSettings>("general");
  const reset = useResetSettings("general");
  const [form, setForm] = useState<GeneralSettings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof GeneralSettings>(k: K, v: GeneralSettings[K]) =>
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
      onSuccess: (data) => setForm(data as unknown as GeneralSettings),
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <FieldInput
            label={t.settings.appName}
            value={form.app_name}
            onChange={(v) => set("app_name", String(v))}
          />

          <FieldSection title="Language & Provider" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSelect
              label={t.settings.sourceLang}
              value={form.source_lang}
              onChange={(v) => set("source_lang", v)}
              options={[
                { value: "en", label: "English" },
                { value: "vi", label: "Vietnamese" },
                { value: "ja", label: "Japanese" },
                { value: "zh", label: "Chinese" },
                { value: "ko", label: "Korean" },
                { value: "fr", label: "French" },
                { value: "de", label: "German" },
                { value: "es", label: "Spanish" },
              ]}
            />
            <FieldSelect
              label={t.settings.targetLang}
              value={form.target_lang}
              onChange={(v) => set("target_lang", v)}
              options={[
                { value: "vi", label: "Vietnamese" },
                { value: "en", label: "English" },
                { value: "ja", label: "Japanese" },
                { value: "zh", label: "Chinese" },
                { value: "ko", label: "Korean" },
                { value: "fr", label: "French" },
                { value: "de", label: "German" },
                { value: "es", label: "Spanish" },
              ]}
            />
          </div>

          <FieldSelect
            label={t.settings.qualityMode}
            value={form.quality_mode}
            onChange={(v) => set("quality_mode", v)}
            options={[
              { value: "fast", label: t.settings.qualityFast },
              { value: "balanced", label: t.settings.qualityBalanced },
              { value: "quality", label: t.settings.qualityQuality },
            ]}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSelect
              label={t.settings.providerLabel}
              value={form.provider}
              onChange={(v) => set("provider", v)}
              options={[
                { value: "openai", label: "OpenAI" },
                { value: "anthropic", label: "Anthropic" },
              ]}
            />
            <FieldInput
              label={t.settings.modelLabel}
              value={form.model}
              onChange={(v) => set("model", String(v))}
              placeholder="gpt-4o-mini"
            />
          </div>

          <FieldSection title="Interface" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldSelect
              label={t.settings.themeLabel}
              value={form.theme}
              onChange={(v) => set("theme", v)}
              options={[
                { value: "system", label: "System" },
                { value: "light", label: "Light" },
                { value: "dark", label: "Dark" },
              ]}
            />
            <FieldSelect
              label={t.settings.localeLabel}
              value={form.locale}
              onChange={(v) => set("locale", v)}
              options={[
                { value: "en", label: "English" },
                { value: "vi", label: "Ti\u1EBFng Vi\u1EC7t" },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={handleReset} disabled={reset.isPending}>
          <RotateCcw className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
          {t.settings.reset}
        </Button>
        <Button
          variant="primary"
          size="lg"
          onClick={handleSave}
          loading={update.isPending}
          disabled={saved}
        >
          {saved ? (
            <>
              <Check className="w-4 h-4 mr-1.5" strokeWidth={1.5} />
              {t.settings.saved}
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-1.5" strokeWidth={1.5} />
              {t.settings.save}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
