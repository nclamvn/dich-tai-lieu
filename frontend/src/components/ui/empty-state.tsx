import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-20 text-center",
        className,
      )}
    >
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center mb-5"
        style={{ background: "var(--bg-secondary)" }}
      >
        <Icon
          className="w-7 h-7"
          style={{ color: "var(--fg-tertiary)" }}
          strokeWidth={1.25}
        />
      </div>
      <h3
        className="font-medium text-base"
        style={{ color: "var(--fg-primary)" }}
      >
        {title}
      </h3>
      {description && (
        <p
          className="mt-1.5 text-sm max-w-[320px] leading-relaxed"
          style={{ color: "var(--fg-tertiary)" }}
        >
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
