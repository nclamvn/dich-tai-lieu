"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import type { ReaderTheme, ReaderFont, ReaderFontSize } from "@/lib/api/types";

interface ReaderSettings {
  theme: ReaderTheme;
  font: ReaderFont;
  fontSize: ReaderFontSize;
  sidebarOpen: boolean;
  fullscreen: boolean;
}

interface ReaderContextValue extends ReaderSettings {
  setTheme: (t: ReaderTheme) => void;
  setFont: (f: ReaderFont) => void;
  setFontSize: (s: ReaderFontSize) => void;
  toggleSidebar: () => void;
  toggleFullscreen: () => void;
  increaseFontSize: () => void;
  decreaseFontSize: () => void;
}

const ReaderContext = createContext<ReaderContextValue | null>(null);

const STORAGE_KEY = "aipub-reader-settings";

const DEFAULTS: ReaderSettings = {
  theme: "light",
  font: "serif",
  fontSize: 2,
  sidebarOpen: true,
  fullscreen: false,
};

export function ReaderProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<ReaderSettings>(() => {
    if (typeof window === "undefined") return DEFAULTS;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? { ...DEFAULTS, ...JSON.parse(saved) } : DEFAULTS;
    } catch {
      return DEFAULTS;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          theme: settings.theme,
          font: settings.font,
          fontSize: settings.fontSize,
          sidebarOpen: settings.sidebarOpen,
        }),
      );
    } catch {
      /* ignore */
    }
  }, [settings]);

  const update = useCallback((partial: Partial<ReaderSettings>) => {
    setSettings((prev) => ({ ...prev, ...partial }));
  }, []);

  const value: ReaderContextValue = {
    ...settings,
    setTheme: (theme) => update({ theme }),
    setFont: (font) => update({ font }),
    setFontSize: (fontSize) => update({ fontSize }),
    toggleSidebar: () =>
      setSettings((prev) => ({ ...prev, sidebarOpen: !prev.sidebarOpen })),
    toggleFullscreen: () =>
      setSettings((prev) => ({ ...prev, fullscreen: !prev.fullscreen })),
    increaseFontSize: () =>
      setSettings((prev) => ({
        ...prev,
        fontSize: Math.min(4, prev.fontSize + 1) as ReaderFontSize,
      })),
    decreaseFontSize: () =>
      setSettings((prev) => ({
        ...prev,
        fontSize: Math.max(0, prev.fontSize - 1) as ReaderFontSize,
      })),
  };

  return (
    <ReaderContext.Provider value={value}>{children}</ReaderContext.Provider>
  );
}

export function useReaderSettings() {
  const ctx = useContext(ReaderContext);
  if (!ctx) throw new Error("useReaderSettings must be inside ReaderProvider");
  return ctx;
}
