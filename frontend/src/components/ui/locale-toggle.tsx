"use client";

import { useLocale } from "@/lib/i18n";

interface LocaleToggleProps {
  collapsed?: boolean;
}

export function LocaleToggle({ collapsed }: LocaleToggleProps) {
  const { locale, setLocale } = useLocale();

  // Collapsed: single button showing current lang, click to toggle
  if (collapsed) {
    return (
      <button
        onClick={() => setLocale(locale === "en" ? "vi" : "en")}
        className="text-[11px] font-medium select-none px-1.5 py-1 transition-colors duration-100"
        style={{
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-default)",
          color: "var(--fg-secondary)",
        }}
      >
        {locale === "en" ? "EN" : "VN"}
      </button>
    );
  }

  return (
    <div
      className="inline-flex items-center text-[11px] font-medium select-none"
      style={{
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--border-default)",
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setLocale("en")}
        className="px-2 py-1 transition-colors duration-100"
        style={{
          background:
            locale === "en" ? "var(--fg-primary)" : "transparent",
          color:
            locale === "en" ? "var(--bg-primary)" : "var(--fg-tertiary)",
        }}
      >
        EN
      </button>
      <button
        onClick={() => setLocale("vi")}
        className="px-2 py-1 transition-colors duration-100"
        style={{
          background:
            locale === "vi" ? "var(--fg-primary)" : "transparent",
          color:
            locale === "vi" ? "var(--bg-primary)" : "var(--fg-tertiary)",
        }}
      >
        VN
      </button>
    </div>
  );
}
