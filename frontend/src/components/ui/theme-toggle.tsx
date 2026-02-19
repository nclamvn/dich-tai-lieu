"use client";

import { useTheme } from "@/lib/theme";
import { Sun, Moon } from "lucide-react";

interface ThemeToggleProps {
  collapsed?: boolean;
}

export function ThemeToggle({ collapsed }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const Icon = theme === "dark" ? Sun : Moon;

  return (
    <button
      onClick={toggleTheme}
      title={theme === "dark" ? "Light mode" : "Dark mode"}
      className="flex items-center justify-center transition-colors duration-100"
      style={{
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--border-default)",
        color: "var(--fg-secondary)",
        padding: collapsed ? "5px" : "4px 7px",
      }}
    >
      <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
    </button>
  );
}
