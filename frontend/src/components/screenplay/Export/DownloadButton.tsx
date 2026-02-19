"use client";

interface DownloadButtonProps {
  href: string;
  label: string;
  icon?: string;
  disabled?: boolean;
}

export function DownloadButton({
  href,
  label,
  icon,
  disabled = false,
}: DownloadButtonProps) {
  return (
    <a
      href={disabled ? undefined : href}
      className={`screenplay-download-btn ${disabled ? "disabled" : ""}`}
      download
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => {
        if (disabled) e.preventDefault();
      }}
    >
      {icon && <span className="screenplay-download-icon">{icon}</span>}
      <span>{label}</span>
    </a>
  );
}
