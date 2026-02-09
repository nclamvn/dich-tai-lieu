"use client";

import Link from "next/link";
import {
  Shield,
  Route,
  CheckCircle,
  LayoutGrid,
  FileText,
  BookOpen,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: Shield,
    title: "Extraction Quality Score",
    desc: "6-signal quality grading (A\u2013F) with auto-retry when extraction falls below threshold.",
  },
  {
    icon: Route,
    title: "Smart Provider Routing",
    desc: "QAPR selects the optimal AI provider per language pair and document type.",
  },
  {
    icon: CheckCircle,
    title: "Consistency Check",
    desc: "Cross-chunk validation catches terminology, proper name, style, and number inconsistencies.",
  },
  {
    icon: LayoutGrid,
    title: "Layout DNA 2.0",
    desc: "Structural analysis preserves tables, formulas, headings, lists, and code blocks.",
  },
  {
    icon: FileText,
    title: "Multi-Format Output",
    desc: "Generate DOCX, PDF, or EPUB 3.0 \u2014 each layout-aware and publication-ready.",
  },
  {
    icon: BookOpen,
    title: "Custom Glossaries",
    desc: "Define terminology per language pair. Automatically fed into translation and consistency checks.",
  },
];

const PIPELINE = [
  "Extract",
  "EQS",
  "LayoutDNA",
  "OCR",
  "Route",
  "TM Lookup",
  "Chunk",
  "Translate",
  "Consistency",
  "Output",
];

export default function HomePage() {
  return (
    <div className="space-y-20 pb-12">
      {/* Hero */}
      <section className="pt-8 md:pt-16">
        <h1 className="max-w-[640px]">
          Translate &amp; publish with quality intelligence
        </h1>
        <p
          className="mt-6 text-lg leading-relaxed max-w-[520px]"
          style={{ color: "var(--fg-secondary)" }}
        >
          Upload a document, choose your language pair, and let the pipeline
          handle extraction, translation, quality scoring, and output — all in
          one workflow.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/translate">
            <Button size="lg">
              Start Translating
              <ArrowRight className="w-4 h-4 ml-2" strokeWidth={1.5} />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary" size="lg">
              View Dashboard
            </Button>
          </Link>
        </div>
      </section>

      {/* Pipeline */}
      <section>
        <div
          className="px-6 py-5 overflow-x-auto"
          style={{
            background: "var(--bg-secondary)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <div
            className="flex items-center gap-2 text-[13px] whitespace-nowrap"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {PIPELINE.map((step, i) => (
              <span key={step} className="flex items-center gap-2">
                {i > 0 && (
                  <span style={{ color: "var(--fg-ghost)" }}>&rarr;</span>
                )}
                <span
                  className="px-2.5 py-1"
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--fg-primary)",
                  }}
                >
                  {step}
                </span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section>
        <h2>How it works</h2>
        <p
          className="mb-10 max-w-[480px]"
          style={{ color: "var(--fg-secondary)" }}
        >
          Each document passes through a 10-stage pipeline with four automated
          quality intelligence layers.
        </p>

        <div
          className="grid grid-cols-1 md:grid-cols-2 gap-px overflow-hidden"
          style={{
            background: "var(--border-default)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border-default)",
          }}
        >
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="p-6 transition-colors duration-100"
              style={{ background: "var(--bg-primary)" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "var(--bg-primary)")
              }
            >
              <Icon
                className="w-5 h-5 mb-3"
                style={{ color: "var(--fg-icon)" }}
                strokeWidth={1.5}
              />
              <h3
                className="text-[15px] font-semibold mb-1.5"
                style={{ color: "var(--fg-primary)" }}
              >
                {title}
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className="flex flex-wrap gap-10 text-center md:text-left">
        {[
          { number: "1,328", label: "Tests passing" },
          { number: "19", label: "Service modules" },
          { number: "15", label: "Sprints shipped" },
          { number: "0", label: "Breaking changes" },
        ].map(({ number, label }) => (
          <div key={label}>
            <p
              className="text-[2.5rem] leading-none"
              style={{
                fontFamily: "var(--font-display)",
                color: "var(--fg-primary)",
              }}
            >
              {number}
            </p>
            <p
              className="mt-1 text-sm"
              style={{ color: "var(--fg-tertiary)" }}
            >
              {label}
            </p>
          </div>
        ))}
      </section>

      {/* Quote */}
      <section
        className="py-1 max-w-[520px]"
        style={{
          borderLeft: "3px solid var(--fg-ghost)",
          paddingLeft: "1.25rem",
        }}
      >
        <p
          className="text-xl italic leading-relaxed"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--fg-primary)",
          }}
        >
          &ldquo;The best way to predict the future is to invent it.&rdquo;
        </p>
        <p
          className="mt-2 text-sm"
          style={{ color: "var(--fg-tertiary)" }}
        >
          Alan Kay, computing pioneer
        </p>
      </section>
    </div>
  );
}
