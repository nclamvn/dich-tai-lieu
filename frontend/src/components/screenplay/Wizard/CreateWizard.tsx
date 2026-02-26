"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Globe, ChevronDown, Check, Upload, FileText, Loader2, X, PenLine, Image, Clapperboard, Trophy } from "lucide-react";
import {
  CreateProjectInput,
  ProjectTier,
  VideoProvider,
  Language,
} from "@/lib/screenplay/types";
import {
  TIER_INFO,
  VIDEO_PROVIDERS,
  SUPPORTED_LANGUAGES,
  MAX_SOURCE_LENGTH,
  MIN_SOURCE_LENGTH,
} from "@/lib/screenplay/constants";
import { createProject, estimateCost, extractTextFromFile } from "@/lib/screenplay/api";
import type { CostEstimate } from "@/lib/screenplay/types";

type Step = "source" | "settings" | "review";

const TIER_ICONS: Record<string, React.ElementType> = {
  free: PenLine,
  standard: Image,
  pro: Clapperboard,
  director: Trophy,
};

function LanguageSelect({
  value,
  onChange,
}: {
  value: Language;
  onChange: (lang: Language) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = SUPPORTED_LANGUAGES.find((l) => l.code === value);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="screenplay-form-group">
      <label>Language</label>
      <div ref={ref} className="sp-lang-select">
        <button
          type="button"
          className="sp-lang-trigger"
          onClick={() => setOpen(!open)}
        >
          <Globe size={16} className="sp-lang-icon" />
          <span>{selected?.name}</span>
          <ChevronDown
            size={14}
            className={`sp-lang-chevron ${open ? "sp-lang-chevron-open" : ""}`}
          />
        </button>
        {open && (
          <div className="sp-lang-dropdown">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                className={`sp-lang-option ${
                  lang.code === value ? "sp-lang-option-active" : ""
                }`}
                onClick={() => {
                  onChange(lang.code);
                  setOpen(false);
                }}
              >
                <Globe size={14} />
                <span>{lang.name}</span>
                {lang.code === value && (
                  <Check size={14} className="sp-lang-check" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function CreateWizard() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("source");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [input, setInput] = useState<CreateProjectInput>({
    title: "",
    source_text: "",
    language: "en",
    tier: "free",
  });

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const result = await extractTextFromFile(file);
      setInput((prev) => ({
        ...prev,
        source_text: result.text,
        title: prev.title || file.name.replace(/\.[^.]+$/, ""),
      }));
      setUploadedFile(result.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract text");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, []);

  const sourceLength = input.source_text.length;
  const isSourceValid =
    sourceLength >= MIN_SOURCE_LENGTH && sourceLength <= MAX_SOURCE_LENGTH;

  const handleTierChange = useCallback(
    async (tier: ProjectTier) => {
      setInput((prev) => ({ ...prev, tier }));
      if (sourceLength > 0) {
        try {
          const estimate = await estimateCost(
            sourceLength,
            tier,
            tier === "pro" || tier === "director"
              ? input.video_provider || "runway"
              : undefined
          );
          setCostEstimate(estimate);
        } catch {
          // Cost estimation is optional
        }
      }
    },
    [sourceLength, input.video_provider]
  );

  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      const project = await createProject(input);
      router.push(`/screenplay/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
      setSubmitting(false);
    }
  }, [input, router]);

  return (
    <div className="screenplay-wizard">
      <div className="screenplay-wizard-steps">
        {(["source", "settings", "review"] as Step[]).map((s, i) => (
          <div
            key={s}
            className={`screenplay-wizard-step ${
              s === step
                ? "active"
                : (["source", "settings", "review"] as Step[]).indexOf(step) > i
                  ? "completed"
                  : ""
            }`}
          >
            <span className="screenplay-step-number">{i + 1}</span>
            <span className="screenplay-step-label">
              {s === "source" ? "Source" : s === "settings" ? "Settings" : "Review"}
            </span>
          </div>
        ))}
      </div>

      {error && (
        <div className="screenplay-error-banner">
          <p>{error}</p>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {step === "source" && (
        <div className="screenplay-wizard-panel">
          <h2>Source Material</h2>
          <p>Paste your story, novel, or source text below.</p>

          <div className="screenplay-form-group">
            <label htmlFor="title">Project Title</label>
            <input
              id="title"
              type="text"
              className="screenplay-input"
              placeholder="My Screenplay"
              value={input.title}
              onChange={(e) =>
                setInput((prev) => ({ ...prev, title: e.target.value }))
              }
            />
          </div>

          <div className="screenplay-form-group">
            <label htmlFor="source">Source Text</label>
            <div className="sp-upload-zone">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileUpload}
                className="sp-upload-hidden"
              />
              <button
                type="button"
                className="sp-upload-btn"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? (
                  <Loader2 size={14} className="sp-upload-spinner" />
                ) : (
                  <Upload size={14} />
                )}
                <span>{uploading ? "Extracting..." : "Upload PDF / DOCX / TXT"}</span>
              </button>
              {uploadedFile && (
                <span className="sp-upload-file">
                  <FileText size={14} />
                  <span>{uploadedFile}</span>
                  <button
                    type="button"
                    className="sp-upload-clear"
                    onClick={() => {
                      setUploadedFile(null);
                      setInput((prev) => ({ ...prev, source_text: "" }));
                    }}
                  >
                    <X size={12} />
                  </button>
                </span>
              )}
            </div>
            <textarea
              id="source"
              className="screenplay-textarea"
              rows={12}
              placeholder="Paste your story or novel text here, or upload a file above..."
              value={input.source_text}
              onChange={(e) =>
                setInput((prev) => ({ ...prev, source_text: e.target.value }))
              }
            />
            <div className="screenplay-char-count">
              <span
                className={
                  isSourceValid ? "screenplay-valid" : "screenplay-invalid"
                }
              >
                {sourceLength.toLocaleString()} characters
              </span>
              <span>
                ({MIN_SOURCE_LENGTH.toLocaleString()} -{" "}
                {MAX_SOURCE_LENGTH.toLocaleString()})
              </span>
            </div>
          </div>

          <LanguageSelect
            value={input.language}
            onChange={(lang) =>
              setInput((prev) => ({ ...prev, language: lang }))
            }
          />

          <div className="screenplay-wizard-actions">
            <button
              className="screenplay-btn screenplay-btn-primary"
              disabled={!input.title || !isSourceValid}
              onClick={() => setStep("settings")}
            >
              Next: Settings
            </button>
          </div>
        </div>
      )}

      {step === "settings" && (
        <div className="screenplay-wizard-panel">
          <h2>Project Settings</h2>

          <div className="screenplay-tier-grid">
            {(Object.entries(TIER_INFO) as [ProjectTier, typeof TIER_INFO[ProjectTier]][]).map(
              ([key, info]) => (
                <div
                  key={key}
                  className={`screenplay-tier-card ${
                    input.tier === key ? "selected" : ""
                  } screenplay-tier-${info.color}`}
                  onClick={() => handleTierChange(key)}
                >
                  <div className="screenplay-tier-icon">
                    {(() => {
                      const TierIcon = TIER_ICONS[key];
                      return TierIcon ? <TierIcon size={32} strokeWidth={1.5} /> : null;
                    })()}
                  </div>
                  <h3>{info.name}</h3>
                  <p>{info.description}</p>
                  <ul>
                    {info.features.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </div>
              )
            )}
          </div>

          {(input.tier === "pro" || input.tier === "director") && (
            <div className="screenplay-form-group">
              <label>Video Provider</label>
              <div className="screenplay-provider-grid">
                {(
                  Object.entries(VIDEO_PROVIDERS) as [
                    VideoProvider,
                    typeof VIDEO_PROVIDERS[VideoProvider],
                  ][]
                ).map(([key, info]) => (
                  <div
                    key={key}
                    className={`screenplay-provider-card ${
                      input.video_provider === key ? "selected" : ""
                    }`}
                    onClick={() =>
                      setInput((prev) => ({ ...prev, video_provider: key }))
                    }
                  >
                    <h4>{info.name}</h4>
                    <p>{info.description}</p>
                    <span className="screenplay-provider-cost">
                      ${info.cost_per_second}/sec
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="screenplay-wizard-actions">
            <button
              className="screenplay-btn"
              onClick={() => setStep("source")}
            >
              Back
            </button>
            <button
              className="screenplay-btn screenplay-btn-primary"
              onClick={() => setStep("review")}
            >
              Next: Review
            </button>
          </div>
        </div>
      )}

      {step === "review" && (
        <div className="screenplay-wizard-panel">
          <h2>Review & Create</h2>

          <div className="screenplay-review-summary">
            <div className="screenplay-review-row">
              <span>Title</span>
              <span>{input.title}</span>
            </div>
            <div className="screenplay-review-row">
              <span>Source Length</span>
              <span>{sourceLength.toLocaleString()} characters</span>
            </div>
            <div className="screenplay-review-row">
              <span>Language</span>
              <span>
                {SUPPORTED_LANGUAGES.find((l) => l.code === input.language)?.name}
              </span>
            </div>
            <div className="screenplay-review-row">
              <span>Tier</span>
              <span>{TIER_INFO[input.tier].name}</span>
            </div>
            {input.video_provider && (
              <div className="screenplay-review-row">
                <span>Video Provider</span>
                <span>{VIDEO_PROVIDERS[input.video_provider].name}</span>
              </div>
            )}
            {costEstimate && (
              <>
                <div className="screenplay-review-row">
                  <span>Estimated Scenes</span>
                  <span>{costEstimate.estimated_scenes}</span>
                </div>
                <div className="screenplay-review-row screenplay-review-total">
                  <span>Estimated Cost</span>
                  <span>${costEstimate.costs.total.toFixed(2)}</span>
                </div>
              </>
            )}
          </div>

          <div className="screenplay-wizard-actions">
            <button
              className="screenplay-btn"
              onClick={() => setStep("settings")}
            >
              Back
            </button>
            <button
              className="screenplay-btn screenplay-btn-primary"
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? "Creating..." : "Create Project"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
