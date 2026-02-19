"use client";

/**
 * Reusable form field components for Settings panels.
 * Uses CSS variables (Notion theme) — no shadcn dependency.
 */

import { cn } from "@/lib/utils";

// ── Text / Number Input ──

export function FieldInput({
  label,
  hint,
  type = "text",
  value,
  onChange,
  disabled,
  min,
  max,
  step,
  placeholder,
}: {
  label: string;
  hint?: string;
  type?: "text" | "number" | "password";
  value: string | number;
  onChange: (v: string | number) => void;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
}) {
  return (
    <div>
      <label
        className="block text-sm font-medium mb-1.5"
        style={{ color: "var(--fg-primary)" }}
      >
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) =>
          onChange(type === "number" ? Number(e.target.value) : e.target.value)
        }
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm"
        style={{
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-default)",
          background: disabled ? "var(--bg-secondary)" : "var(--bg-primary)",
          color: disabled ? "var(--fg-tertiary)" : "var(--fg-primary)",
        }}
      />
      {hint && (
        <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

// ── Select ──

export function FieldSelect({
  label,
  value,
  onChange,
  options,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  hint?: string;
}) {
  return (
    <div>
      <label
        className="block text-sm font-medium mb-1.5"
        style={{ color: "var(--fg-primary)" }}
      >
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm"
        style={{
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-default)",
          background: "var(--bg-primary)",
          color: "var(--fg-primary)",
        }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {hint && (
        <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

// ── Toggle / Switch ──

export function FieldToggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1 min-w-0 mr-4">
        <span className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
          {label}
        </span>
        {description && (
          <p className="text-xs mt-0.5" style={{ color: "var(--fg-tertiary)" }}>
            {description}
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors",
        )}
        style={{
          background: checked ? "var(--color-notion-blue)" : "var(--bg-tertiary)",
        }}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-4 w-4 rounded-full shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0.5",
          )}
          style={{
            background: "white",
            marginTop: "2px",
          }}
        />
      </button>
    </div>
  );
}

// ── Slider (number with range) ──

export function FieldSlider({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  hint,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  hint?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
          {label}
        </label>
        <span className="text-xs font-mono" style={{ color: "var(--fg-secondary)" }}>
          {value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{ background: "var(--bg-tertiary)", accentColor: "var(--color-notion-blue)" }}
      />
      {hint && (
        <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

// ── Section divider ──

export function FieldSection({ title }: { title: string }) {
  return (
    <div className="pt-3 pb-1">
      <h4
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--fg-tertiary)" }}
      >
        {title}
      </h4>
    </div>
  );
}
