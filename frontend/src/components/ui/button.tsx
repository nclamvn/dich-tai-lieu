import { cn } from "@/lib/utils";
import { forwardRef } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const VARIANT_CLASSES: Record<string, string> = {
  primary: "text-white",
  secondary: "",
  ghost: "",
  danger: "text-white",
};

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  primary: {
    background: "var(--color-notion-blue)",
    boxShadow:
      "inset 0 0 0 1px rgba(15,15,15,0.1), 0 1px 2px rgba(15,15,15,0.1)",
  },
  secondary: {
    background: "var(--bg-primary)",
    color: "var(--fg-primary)",
    boxShadow: "var(--shadow-sm)",
  },
  ghost: {
    background: "transparent",
    color: "var(--fg-secondary)",
  },
  danger: {
    background: "var(--color-notion-red)",
    boxShadow: "inset 0 0 0 1px rgba(15,15,15,0.1)",
  },
};

const SIZE_CLASSES: Record<string, string> = {
  sm: "px-2.5 py-1 text-[12px]",
  md: "px-3 py-1.5 text-[13px]",
  lg: "px-4 py-2 text-[14px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading,
      className,
      children,
      disabled,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-medium",
          "transition-all duration-100",
          "disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none",
          "select-none whitespace-nowrap",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        style={{
          borderRadius: "var(--radius-sm)",
          ...VARIANT_STYLES[variant],
        }}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
