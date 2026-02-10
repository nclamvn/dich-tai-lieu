"use client";

import { Settings } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";

export default function SettingsPage() {
  const { t } = useLocale();

  return (
    <div className="space-y-6">
      <h1>{t.settings.title}</h1>

      <Card>
        <CardHeader>
          <h2 className="font-semibold flex items-center gap-2 text-[15px]">
            <Settings
              className="w-4 h-4"
              style={{ color: "var(--fg-icon)" }}
              strokeWidth={1.5}
            />
            {t.settings.apiConfig}
          </h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label
              className="block text-sm font-medium mb-1.5"
              style={{ color: "var(--fg-primary)" }}
            >
              {t.settings.backendUrl}
            </label>
            <input
              type="text"
              defaultValue={
                process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
              }
              disabled
              className="w-full px-3 py-2 text-sm"
              style={{
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-default)",
                background: "var(--bg-secondary)",
                color: "var(--fg-secondary)",
              }}
            />
            <p
              className="text-xs mt-1"
              style={{ color: "var(--fg-tertiary)" }}
            >
              {t.settings.backendUrlHint}
            </p>
          </div>

          <div>
            <label
              className="block text-sm font-medium mb-1.5"
              style={{ color: "var(--fg-primary)" }}
            >
              {t.settings.version}
            </label>
            <p
              className="text-sm"
              style={{ color: "var(--fg-secondary)" }}
            >
              {t.settings.versionInfo}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
