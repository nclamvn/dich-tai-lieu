"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import {
  Settings,
  Languages,
  BookOpen,
  Key,
  Download,
  Wrench,
} from "lucide-react";
import { GeneralPanel } from "./general-panel";
import { TranslationPanel } from "./translation-panel";
import { BookWriterPanel } from "./book-writer-panel";
import { ApiKeysPanel } from "./api-keys-panel";
import { ExportPanel } from "./export-panel";
import { AdvancedPanel } from "./advanced-panel";

const TAB_ICONS = {
  general: Settings,
  translation: Languages,
  bookWriter: BookOpen,
  apiKeys: Key,
  export: Download,
  advanced: Wrench,
} as const;

type TabKey = keyof typeof TAB_ICONS;

const TABS: TabKey[] = ["general", "translation", "bookWriter", "apiKeys", "export", "advanced"];

const TAB_PANELS: Record<TabKey, React.ComponentType> = {
  general: GeneralPanel,
  translation: TranslationPanel,
  bookWriter: BookWriterPanel,
  apiKeys: ApiKeysPanel,
  export: ExportPanel,
  advanced: AdvancedPanel,
};

export function SettingsTabs() {
  const [activeTab, setActiveTab] = useState<TabKey>("general");
  const { t } = useLocale();
  const Panel = TAB_PANELS[activeTab];

  return (
    <div className="flex flex-col md:flex-row gap-6">
      {/* Tab list — horizontal on mobile, vertical on desktop */}
      <nav className="md:w-48 shrink-0 flex md:flex-col gap-0.5 overflow-x-auto md:overflow-visible pb-2 md:pb-0 border-b md:border-b-0 md:border-r"
        style={{ borderColor: "var(--border-default)" }}
      >
        <div className="flex md:flex-col gap-0.5 md:pr-4">
          {TABS.map((tab) => {
            const Icon = TAB_ICONS[tab];
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 text-sm whitespace-nowrap",
                  "transition-colors duration-100",
                )}
                style={{
                  borderRadius: "var(--radius-sm)",
                  background: isActive ? "var(--bg-active)" : "transparent",
                  color: isActive ? "var(--fg-primary)" : "var(--fg-secondary)",
                  fontWeight: isActive ? 500 : 400,
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = "var(--bg-hover)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = "transparent";
                }}
              >
                <Icon
                  className="w-4 h-4 shrink-0"
                  style={{ color: isActive ? "var(--fg-primary)" : "var(--fg-icon)" }}
                  strokeWidth={1.5}
                />
                {t.settings.tabs[tab]}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Panel content */}
      <div className="flex-1 min-w-0">
        <Panel />
      </div>
    </div>
  );
}
