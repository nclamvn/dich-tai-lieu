"use client";

import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSettingsSection, useUpdateSettings, useResetSettings } from "@/lib/api/hooks";
import { FieldInput, FieldSelect, FieldToggle, FieldSection } from "./form-fields";
import type { AdvancedSettingsConfig } from "@/lib/api/types";
import { RotateCcw, Save, Check, AlertTriangle } from "lucide-react";

export function AdvancedPanel() {
  const { t } = useLocale();
  const { data, isLoading } = useSettingsSection<AdvancedSettingsConfig>("advanced");
  const update = useUpdateSettings<AdvancedSettingsConfig>("advanced");
  const reset = useResetSettings("advanced");
  const [form, setForm] = useState<AdvancedSettingsConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  if (isLoading || !form) {
    return <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-12 skeleton" />)}</div>;
  }

  const set = <K extends keyof AdvancedSettingsConfig>(k: K, v: AdvancedSettingsConfig[K]) =>
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
      onSuccess: (data) => setForm(data as unknown as AdvancedSettingsConfig),
    });
  };

  return (
    <div className="space-y-4">
      {/* Warning */}
      <div
        className="flex items-start gap-3 px-4 py-3 text-sm"
        style={{
          borderRadius: "var(--radius-md)",
          background: "var(--accent-red-bg)",
          color: "var(--color-notion-red)",
        }}
      >
        <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" strokeWidth={1.5} />
        <span>These settings affect system behavior. Change with caution.</span>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <FieldSection title="Security" />

          <FieldSelect
            label={t.settings.securityMode}
            value={form.security_mode}
            onChange={(v) => set("security_mode", v)}
            options={[
              { value: "development", label: "Development" },
              { value: "internal", label: "Internal" },
              { value: "production", label: "Production" },
            ]}
          />

          <FieldToggle
            label={t.settings.sessionAuth}
            checked={form.session_auth_enabled}
            onChange={(v) => set("session_auth_enabled", v)}
          />
          <FieldToggle
            label={t.settings.apiKeyAuth}
            checked={form.api_key_auth_enabled}
            onChange={(v) => set("api_key_auth_enabled", v)}
          />
          <FieldToggle
            label={t.settings.csrfProtection}
            checked={form.csrf_enabled}
            onChange={(v) => set("csrf_enabled", v)}
          />

          <FieldInput
            label={t.settings.rateLimit}
            value={form.rate_limit}
            onChange={(v) => set("rate_limit", String(v))}
            placeholder="60/minute"
          />

          <FieldSection title="Database" />

          <FieldSelect
            label={t.settings.databaseBackend}
            value={form.database_backend}
            onChange={(v) => set("database_backend", v)}
            options={[
              { value: "sqlite", label: "SQLite" },
              { value: "postgresql", label: "PostgreSQL" },
            ]}
          />

          <FieldSection title="Experimental" />

          <FieldToggle
            label={t.settings.astPipeline}
            description="Enhanced PDF export pipeline"
            checked={form.use_ast_pipeline}
            onChange={(v) => set("use_ast_pipeline", v)}
          />
          <FieldToggle
            label={t.settings.debugMode}
            description="Verbose logging and diagnostics"
            checked={form.debug_mode}
            onChange={(v) => set("debug_mode", v)}
          />

          <FieldSection title="Cleanup" />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FieldInput
              label={t.settings.uploadRetention}
              type="number"
              value={form.cleanup_upload_retention_days}
              onChange={(v) => set("cleanup_upload_retention_days", Number(v))}
              min={1}
            />
            <FieldInput
              label={t.settings.outputRetention}
              type="number"
              value={form.cleanup_output_retention_days}
              onChange={(v) => set("cleanup_output_retention_days", Number(v))}
              min={1}
            />
            <FieldInput
              label={t.settings.tempMaxAge}
              type="number"
              value={form.cleanup_temp_max_age_hours}
              onChange={(v) => set("cleanup_temp_max_age_hours", Number(v))}
              min={1}
            />
          </div>
        </CardContent>
      </Card>

      {/* System Info */}
      <Card>
        <CardContent className="space-y-2">
          <FieldSection title="System Info" />
          <div className="grid grid-cols-2 gap-2 text-sm">
            <span style={{ color: "var(--fg-tertiary)" }}>{t.settings.backendUrl}</span>
            <span className="font-mono text-xs" style={{ color: "var(--fg-secondary)" }}>
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </span>
            <span style={{ color: "var(--fg-tertiary)" }}>{t.settings.version}</span>
            <span style={{ color: "var(--fg-secondary)" }}>{t.settings.versionInfo}</span>
          </div>
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
