"use client";

import { useLocale } from "@/lib/i18n";
import { SettingsTabs } from "@/components/settings";

export default function SettingsPage() {
  const { t } = useLocale();

  return (
    <div className="space-y-6">
      <div>
        <h1>{t.settings.title}</h1>
        <p className="mt-2" style={{ color: "var(--fg-secondary)" }}>
          {t.settings.subtitle}
        </p>
      </div>

      <SettingsTabs />
    </div>
  );
}
