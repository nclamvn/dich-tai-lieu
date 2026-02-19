"use client";

import { useReaderSettings } from "./reader-context";
import type { ReaderTheme } from "@/lib/api/types";

interface ReaderProgressProps {
  globalProgress: number;
}

const BAR_BG: Record<ReaderTheme, string> = {
  light: "var(--border-default)",
  sepia: "rgba(95,75,50,0.15)",
  dark: "rgba(255,255,255,0.2)",
};

const FILL_COLOR: Record<ReaderTheme, string> = {
  light: "var(--color-notion-blue)",
  sepia: "rgba(95,75,50,0.4)",
  dark: "rgba(255,255,255,0.45)",
};

export function ReaderProgress({ globalProgress }: ReaderProgressProps) {
  const { theme } = useReaderSettings();

  return (
    <div
      className="h-[2px] w-full shrink-0"
      style={{ backgroundColor: BAR_BG[theme] }}
    >
      <div
        className="h-full"
        style={{
          width: `${globalProgress}%`,
          backgroundColor: FILL_COLOR[theme],
          transition: "width 300ms ease-out",
        }}
      />
    </div>
  );
}
