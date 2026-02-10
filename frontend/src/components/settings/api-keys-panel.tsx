"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldInput, FieldSection } from "./form-fields";
import type { ApiKeySettingsConfig } from "@/lib/api/types";
import { RotateCcw, Save, Check, ShieldAlert } from "lucide-react";

export function ApiKeysPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<ApiKeySettingsConfig>("api_keys");
  const update = useUpdateSettings<ApiKeySettingsConfig>("api_keys");
  const reset = useResetSettings("api_keys");
  const [form, setForm] = useState<ApiKeySettingsConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof ApiKeySettingsConfig>(k: K, v: ApiKeySettingsConfig[K]) =>
    setForm((prev) => (prev ? { ...prev, [k]: v } : prev));

  const handleSave = () => {
    update.mutate(form, {
      onSuccess: (data) => {
        setForm(data as unknown as ApiKeySettingsConfig);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      },
    });
  };

  const handleReset = () => {
    if (!confirm(t.settings.resetConfirm)) return;
    reset.mutate(undefined, {
      onSuccess: (data) => setForm(data as unknown as ApiKeySettingsConfig),
    });
  };

  return (
    <div className="space-y-4">
      {/* Warning banner */}
      <div
        className="flex items-start gap-3 px-4 py-3 text-sm"
        style={{
          borderRadius: "var(--radius-md)",
          background: "var(--accent-yellow-bg)",
          color: "var(--color-notion-yellow)",
          border: "1px solid var(--accent-yellow-bg)",
        }}
      >
        <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0" strokeWidth={1.5} />
        <span>{t.settings.apiKeysWarning}</span>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <FieldSection title="AI Providers" />

          <FieldInput
            label={t.settings.openaiKey}
            type="password"
            value={form.openai_api_key}
            onChange={(v) => set("openai_api_key", String(v))}
            placeholder="sk-..."
          />
          <FieldInput
            label={t.settings.anthropicKey}
            type="password"
            value={form.anthropic_api_key}
            onChange={(v) => set("anthropic_api_key", String(v))}
            placeholder="sk-ant-..."
          />
          <FieldInput
            label={t.settings.googleKey}
            type="password"
            value={form.google_api_key}
            onChange={(v) => set("google_api_key", String(v))}
            placeholder="AIza..."
          />

          <FieldSection title="OCR / Vision" />

          <FieldInput
            label={t.settings.mathpixId}
            value={form.mathpix_app_id}
            onChange={(v) => set("mathpix_app_id", String(v))}
          />
          <FieldInput
            label={t.settings.mathpixKey}
            type="password"
            value={form.mathpix_app_key}
            onChange={(v) => set("mathpix_app_key", String(v))}
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
