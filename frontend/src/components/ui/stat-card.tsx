import { Card } from "./card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label: string };
  className?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("px-5 py-4", className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold">{value}</p>
          {trend && (
            <p
              className={cn(
                "mt-1 text-xs",
                trend.value >= 0 ? "text-green-600" : "text-red-600",
              )}
            >
              {trend.value >= 0 ? "\u2191" : "\u2193"} {Math.abs(trend.value)}%{" "}
              {trend.label}
            </p>
          )}
        </div>
        {Icon && (
          <div className="p-2 bg-blue-50 rounded-lg">
            <Icon className="w-5 h-5 text-blue-600" />
          </div>
        )}
      </div>
    </Card>
  );
}
