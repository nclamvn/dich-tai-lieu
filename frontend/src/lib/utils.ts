import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  if (usd < 1) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
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
    A: "text-green-600",
    B: "text-blue-600",
    C: "text-yellow-600",
    D: "text-orange-600",
    F: "text-red-600",
  };
  return colors[grade] || "text-gray-600";
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    processing: "bg-blue-100 text-blue-800",
    pending: "bg-yellow-100 text-yellow-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-gray-100 text-gray-800",
  };
  return colors[status] || "bg-gray-100 text-gray-800";
}
