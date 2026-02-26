"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X, Sparkles, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUploadImages, useAnalyzeImages, useImageManifest } from "@/lib/api/hooks";
import type { ImageAnalysisResult } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/tiff", "image/bmp"];
const MAX_SIZE = 20 * 1024 * 1024;

interface ImageUploadZoneProps {
  projectId: string;
}

const CATEGORY_VARIANTS: Record<string, "default" | "info" | "success" | "warning"> = {
  photo: "info",
  illustration: "default",
  diagram: "success",
  chart: "warning",
  art: "default",
};

export function ImageUploadZone({ projectId }: ImageUploadZoneProps) {
  const { t } = useLocale();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localFiles, setLocalFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useUploadImages();
  const analyzeMutation = useAnalyzeImages();
  const { data: manifest } = useImageManifest(projectId);

  const validateAndAdd = useCallback((files: FileList | File[]) => {
    setError(null);
    const valid: File[] = [];
    for (const file of Array.from(files)) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError(`Unsupported type: ${file.name}`);
        continue;
      }
      if (file.size > MAX_SIZE) {
        setError(`File too large: ${file.name} (max 20MB)`);
        continue;
      }
      valid.push(file);
    }
    if (valid.length === 0) return;

    setLocalFiles((prev) => [...prev, ...valid]);
    const newPreviews = valid.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...newPreviews]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      validateAndAdd(e.dataTransfer.files);
    },
    [validateAndAdd],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) validateAndAdd(e.target.files);
    },
    [validateAndAdd],
  );

  const removeFile = (idx: number) => {
    URL.revokeObjectURL(previews[idx]);
    setLocalFiles((prev) => prev.filter((_, i) => i !== idx));
    setPreviews((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (localFiles.length === 0) return;
    try {
      await uploadMutation.mutateAsync({ projectId, files: localFiles });
      setLocalFiles([]);
      setPreviews([]);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    }
  };

  const handleAnalyze = async () => {
    try {
      await analyzeMutation.mutateAsync(projectId);
    } catch (err: any) {
      setError(err.message || "Analysis failed");
    }
  };

  const tw = t.writeV2;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        className="rounded-lg p-8 text-center cursor-pointer transition-colors"
        style={{
          border: `2px dashed ${dragOver ? "var(--color-notion-blue)" : "var(--border-default)"}`,
          background: dragOver ? "var(--accent-blue-bg)" : "transparent",
        }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          onChange={handleFileSelect}
        />
        <ImageIcon
          className="w-8 h-8 mx-auto mb-2"
          style={{ color: "var(--fg-tertiary)" }}
          strokeWidth={1.5}
        />
        <p className="text-sm" style={{ color: "var(--fg-secondary)" }}>
          {tw.dropZoneText}
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--fg-tertiary)" }}>
          {tw.dropZoneHint}
        </p>
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm" style={{ color: "var(--color-notion-red)" }}>{error}</p>
      )}

      {/* Local file previews */}
      {localFiles.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              {localFiles.length} {tw.imagesSelected}
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={handleUpload}
              loading={uploadMutation.isPending}
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
              {uploadMutation.isPending ? tw.uploading : tw.upload}
            </Button>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {previews.map((src, i) => (
              <div
                key={i}
                className="relative group rounded overflow-hidden"
                style={{ border: "1px solid var(--border-default)" }}
              >
                <img src={src} alt="" className="w-full h-24 object-cover" />
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                  className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: "var(--color-notion-red)", color: "white" }}
                >
                  <X className="w-3 h-3" strokeWidth={2} />
                </button>
                <p
                  className="text-xs truncate px-1 py-0.5"
                  style={{ color: "var(--fg-tertiary)" }}
                >
                  {localFiles[i].name}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analyzed manifest */}
      {manifest && manifest.images.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
              {manifest.total_images} {tw.analyzedImages}
            </p>
            <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>
              {tw.genreLabel}: {manifest.detected_genre}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {manifest.images.map((img) => (
              <div
                key={img.image_id}
                className="rounded-md p-2.5 text-xs space-y-1"
                style={{
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-secondary)",
                }}
              >
                <p className="font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                  {img.subject}
                </p>
                <p className="truncate" style={{ color: "var(--fg-secondary)" }}>
                  {img.description}
                </p>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Badge variant={CATEGORY_VARIANTS[img.category] || "default"}>
                    {img.category}
                  </Badge>
                  <span style={{ color: "var(--fg-tertiary)" }}>
                    {img.width}x{img.height}
                  </span>
                  <span style={{ color: "var(--fg-tertiary)" }}>
                    Q: {(img.quality_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analyze button (shown after successful upload, before manifest exists) */}
      {!manifest && uploadMutation.isSuccess && (
        <Button
          variant="secondary"
          className="w-full"
          onClick={handleAnalyze}
          loading={analyzeMutation.isPending}
        >
          <Sparkles className="w-4 h-4 mr-2" strokeWidth={1.5} />
          {analyzeMutation.isPending ? tw.analyzingImages : tw.analyzeImages}
        </Button>
      )}
    </div>
  );
}
