"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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
import { createProject, estimateCost } from "@/lib/screenplay/api";
import type { CostEstimate } from "@/lib/screenplay/types";

type Step = "source" | "settings" | "review";

export function CreateWizard() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("source");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);

  const [input, setInput] = useState<CreateProjectInput>({
    title: "",
    source_text: "",
    language: "en",
    tier: "free",
  });

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
            <textarea
              id="source"
              className="screenplay-textarea"
              rows={12}
              placeholder="Paste your story or novel text here..."
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

          <div className="screenplay-form-group">
            <label htmlFor="language">Language</label>
            <select
              id="language"
              className="screenplay-select"
              value={input.language}
              onChange={(e) =>
                setInput((prev) => ({
                  ...prev,
                  language: e.target.value as Language,
                }))
              }
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.name}
                </option>
              ))}
            </select>
          </div>

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
                  <div className="screenplay-tier-icon">{info.icon}</div>
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
