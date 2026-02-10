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
import { useLocale } from "@/lib/i18n";

const FEATURE_KEYS = [
  { icon: Shield, key: "eqs" as const },
  { icon: Route, key: "routing" as const },
  { icon: CheckCircle, key: "consistency" as const },
  { icon: LayoutGrid, key: "layout" as const },
  { icon: FileText, key: "multiFormat" as const },
  { icon: BookOpen, key: "glossaries" as const },
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
  const { t } = useLocale();

  const STATS = [
    { number: "1,328", label: t.landing.stats.testsPassing },
    { number: "19", label: t.landing.stats.serviceModules },
    { number: "15", label: t.landing.stats.sprintsShipped },
    { number: "0", label: t.landing.stats.breakingChanges },
  ];

  return (
    <div className="space-y-20 pb-12">
      {/* Hero */}
      <section className="pt-8 md:pt-16">
        <h1 className="max-w-[640px]">
          {t.landing.title}
        </h1>
        <p
          className="mt-6 text-lg leading-relaxed max-w-[520px]"
          style={{ color: "var(--fg-secondary)" }}
        >
          {t.landing.subtitle}
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/translate">
            <Button size="lg">
              {t.landing.startBtn}
              <ArrowRight className="w-4 h-4 ml-2" strokeWidth={1.5} />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary" size="lg">
              {t.landing.viewDashboard}
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
        <h2>{t.landing.howItWorks}</h2>
        <p
          className="mb-10 max-w-[480px]"
          style={{ color: "var(--fg-secondary)" }}
        >
          {t.landing.howItWorksDesc}
        </p>

        <div
          className="grid grid-cols-1 md:grid-cols-2 gap-px overflow-hidden"
          style={{
            background: "var(--border-default)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border-default)",
          }}
        >
          {FEATURE_KEYS.map(({ icon: Icon, key }) => (
            <div
              key={key}
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
                {t.landing.features[key]}
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {t.landing.features[`${key}Desc` as keyof typeof t.landing.features]}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className="flex flex-wrap gap-10 text-center md:text-left">
        {STATS.map(({ number, label }) => (
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
          &ldquo;{t.landing.quote}&rdquo;
        </p>
        <p
          className="mt-2 text-sm"
          style={{ color: "var(--fg-tertiary)" }}
        >
          {t.landing.quoteAuthor}
        </p>
      </section>
    </div>
  );
}
