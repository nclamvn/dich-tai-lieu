import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label: string };
  accentColor?: string;
  className?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  accentColor,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn("p-5", className)}
      style={{
        background: "var(--bg-primary)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-default)",
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p
            className="text-[12px] uppercase tracking-wider font-medium"
            style={{ color: "var(--fg-tertiary)" }}
          >
            {label}
          </p>
          <p
            className="mt-2 text-2xl font-semibold tabular-nums"
            style={{ color: "var(--fg-primary)" }}
          >
            {value}
          </p>
          {trend && (
            <p
              className="mt-1 text-xs"
              style={{
                color:
                  trend.value >= 0
                    ? "var(--color-notion-green)"
                    : "var(--color-notion-red)",
              }}
            >
              {trend.value >= 0 ? "\u2191" : "\u2193"}{" "}
              {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        {Icon && (
          <div
            className="w-8 h-8 flex items-center justify-center"
            style={{
              borderRadius: "var(--radius-md)",
              background: accentColor
                ? `${accentColor}12`
                : "var(--bg-secondary)",
            }}
          >
            <Icon
              className="w-4 h-4"
              strokeWidth={1.5}
              style={{ color: accentColor || "var(--fg-icon)" }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
