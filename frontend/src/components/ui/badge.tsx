import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "success"
    | "warning"
    | "error"
    | "info"
    | "purple"
    | "orange";
}

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  default: {
    background: "var(--bg-tertiary)",
    color: "var(--fg-secondary)",
  },
  success: {
    background: "var(--accent-green-bg)",
    color: "var(--color-notion-green)",
  },
  warning: {
    background: "var(--accent-yellow-bg)",
    color: "var(--color-notion-yellow)",
  },
  error: {
    background: "var(--accent-red-bg)",
    color: "var(--color-notion-red)",
  },
  info: {
    background: "var(--accent-blue-bg)",
    color: "var(--color-notion-blue)",
  },
  purple: {
    background: "var(--accent-purple-bg)",
    color: "var(--color-notion-purple)",
  },
  orange: {
    background: "var(--accent-orange-bg)",
    color: "var(--color-notion-orange)",
  },
};

export function Badge({
  variant = "default",
  className,
  children,
  style,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-[7px] py-[2px] text-[11px] font-medium leading-[18px]",
        className,
      )}
      style={{
        borderRadius: "var(--radius-sm)",
        ...VARIANT_STYLES[variant],
        ...style,
      }}
      {...props}
    >
      {children}
    </span>
  );
}
