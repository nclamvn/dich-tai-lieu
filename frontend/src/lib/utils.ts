import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.001) return "<$0.01";
  if (usd < 0.01) return `$${usd.toFixed(3)}`;
  if (usd < 1000) return `$${usd.toFixed(2)}`;
  return `$${usd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

export function formatDate(ts: string | number): string {
  const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function gradeColor(grade: string): string {
  const colors: Record<string, string> = {
    A: "color-notion-green",
    B: "color-notion-blue",
    C: "color-notion-yellow",
    D: "color-notion-orange",
    F: "color-notion-red",
  };
  return colors[grade] || "var(--fg-secondary)";
}

export function statusVariant(
  status: string,
): "default" | "success" | "warning" | "error" | "info" {
  const map: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    completed: "success",
    processing: "info",
    pending: "warning",
    failed: "error",
    cancelled: "default",
  };
  return map[status] || "default";
}

