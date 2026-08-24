"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ImagePlus } from "lucide-react";
import { coverTemplates } from "@/lib/api/client";
import type { CoverTemplate } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export interface CoverSelection {
  coverTemplate?: string;
  coverImage?: string;
}

/**
 * Cover template picker. Loads the catalog from /api/cover-templates, shows a
 * real rendered preview per template (previews == exported cover), and lets the
 * user pick a template, choose "no cover", or upload their own image.
 */
export function CoverPicker({
  value,
  onChange,
}: {
  value: CoverSelection;
  onChange: (v: CoverSelection) => void;
}) {
  const [templates, setTemplates] = useState<CoverTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let alive = true;
    coverTemplates
      .list()
      .then((t) => alive && setTemplates(t))
      .catch(() => alive && setError("Không tải được danh sách mẫu bìa."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const noneSelected = !value.coverTemplate && !value.coverImage;

  const pickTemplate = (id: string) => {
    setUploadPreview(null);
    onChange({
      coverTemplate: value.coverTemplate === id ? undefined : id,
      coverImage: undefined,
    });
  };

  const pickNone = () => {
    setUploadPreview(null);
    onChange({});
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    setError(null);
    try {
      const path = await coverTemplates.upload(f);
      setUploadPreview(URL.createObjectURL(f));
      onChange({ coverTemplate: undefined, coverImage: path });
    } catch {
      setError("Tải ảnh bìa thất bại.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const cardBase =
    "relative rounded-lg border overflow-hidden aspect-[5/8] transition-colors duration-100 cursor-pointer";
  const tick = (
    <span
      className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full grid place-items-center"
      style={{ background: "var(--color-notion-blue, #2f6bff)", color: "#fff" }}
    >
      <Check className="w-3.5 h-3.5" strokeWidth={2.5} />
    </span>
  );

  const selectedName =
    value.coverImage
      ? "Ảnh bìa tự tải lên"
      : value.coverTemplate
        ? (templates.find((tp) => tp.id === value.coverTemplate)?.name || value.coverTemplate)
        : null;

  return (
    <div>
      <p className="text-[13px] mb-2.5">
        <span style={{ color: "var(--fg-tertiary)" }}>Bìa sẽ xuất: </span>
        <span
          className="font-medium"
          style={{ color: selectedName ? "var(--color-notion-blue)" : "var(--fg-secondary)" }}
        >
          {selectedName || "Không dùng bìa"}
        </span>
      </p>
      {error && (
        <p className="text-sm mb-2" style={{ color: "var(--color-notion-red, #e5484d)" }}>
          {error}
        </p>
      )}
      {loading ? (
        <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>
          Đang tải mẫu bìa…
        </p>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
          {/* No cover */}
          {/* The no-cover tile is deliberately UNLIKE a template: dashed ghost
              with a plain label. The old styling gave it the same confident
              blue border + tick as a selected template, so the DEFAULT state
              (no cover chosen) read as "a cover is selected" — and users
              shipped jobs believing a cover was on. */}
          <button
            type="button"
            onClick={pickNone}
            className={cn(cardBase, "flex items-center justify-center text-xs font-medium")}
            style={{
              borderStyle: "dashed",
              borderColor: noneSelected ? "var(--fg-tertiary)" : "var(--border-hover)",
              color: noneSelected ? "var(--fg-primary)" : "var(--fg-tertiary)",
              background: "transparent",
            }}
          >
            Không bìa
          </button>

          {/* Templates */}
          {templates.map((tpl) => {
            const sel = value.coverTemplate === tpl.id;
            return (
              <button
                key={tpl.id}
                type="button"
                onClick={() => pickTemplate(tpl.id)}
                title={tpl.description}
                className={cardBase}
                style={{ borderColor: sel ? "var(--color-notion-blue, #2f6bff)" : "var(--border-hover)" }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={coverTemplates.previewUrl(tpl.id)}
                  alt={tpl.name}
                  loading="lazy"
                  className="w-full h-full object-cover"
                />
                <span
                  className="absolute bottom-0 left-0 right-0 text-[11px] py-0.5 text-center truncate"
                  style={{ background: "rgba(0,0,0,.55)", color: "#fff" }}
                >
                  {tpl.name}
                </span>
                {sel && tick}
              </button>
            );
          })}

          {/* Upload your own */}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className={cn(cardBase, "border-dashed flex flex-col items-center justify-center gap-1 text-xs")}
            style={{
              borderColor: value.coverImage ? "var(--color-notion-blue, #2f6bff)" : "var(--border-hover)",
              color: "var(--fg-secondary)",
            }}
          >
            {uploadPreview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={uploadPreview} alt="Ảnh bìa" className="absolute inset-0 w-full h-full object-cover" />
            ) : (
              <>
                <ImagePlus className="w-5 h-5" strokeWidth={1.5} />
                <span>{uploading ? "Đang tải…" : "Ảnh của bạn"}</span>
              </>
            )}
            {value.coverImage && tick}
          </button>

          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={onUpload}
          />
        </div>
      )}
      <p className="text-xs mt-2" style={{ color: "var(--fg-tertiary)" }}>
        Tựa sách &amp; tác giả tự điền từ tài liệu khi xuất. Bìa áp cho PDF, DOCX và EPUB.
      </p>
    </div>
  );
}
