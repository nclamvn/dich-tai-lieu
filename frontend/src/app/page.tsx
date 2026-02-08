"use client";

import Link from "next/link";
import {
  Upload,
  BarChart3,
  BookOpen,
  Shield,
  Route,
  CheckCircle,
  LayoutGrid,
  FileText,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: Shield,
    title: "Extraction Quality Score",
    desc: "6-signal quality grading (A-F) with auto-retry",
    color: "text-blue-500",
  },
  {
    icon: Route,
    title: "Smart Provider Routing",
    desc: "QAPR selects optimal AI provider per language",
    color: "text-purple-500",
  },
  {
    icon: CheckCircle,
    title: "Consistency Check",
    desc: "Cross-chunk terminology and style validation",
    color: "text-green-500",
  },
  {
    icon: LayoutGrid,
    title: "Layout DNA 2.0",
    desc: "Preserves tables, formulas, headings, lists",
    color: "text-orange-500",
  },
  {
    icon: FileText,
    title: "Multi-Format Output",
    desc: "DOCX, PDF, EPUB 3.0 with full layout",
    color: "text-red-500",
  },
  {
    icon: BookOpen,
    title: "Custom Glossaries",
    desc: "Ensure consistent terminology across documents",
    color: "text-teal-500",
  },
];

const PIPELINE_STEPS = [
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
    <div className="max-w-4xl mx-auto space-y-12 py-8">
      {/* Hero */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">
          AI Publisher Pro
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Translate and publish documents with AI-powered quality intelligence.
          15 sprints, 19 service modules, 1,328 tests — production-grade.
        </p>
        <div className="flex justify-center gap-3">
          <Link href="/translate">
            <Button size="lg">
              <Upload className="w-5 h-5 mr-2" />
              Start Translating
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary" size="lg">
              <BarChart3 className="w-5 h-5 mr-2" />
              View Dashboard
            </Button>
          </Link>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FEATURES.map(({ icon: Icon, title, desc, color }) => (
          <Card key={title} className="p-5 hover:shadow-md transition-shadow">
            <Icon className={`w-6 h-6 ${color} mb-3`} />
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-slate-500 mt-1">{desc}</p>
          </Card>
        ))}
      </div>

      {/* Pipeline Visualization */}
      <Card className="p-6 bg-slate-900 text-white">
        <h3 className="font-semibold text-lg mb-4">Translation Pipeline</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm font-mono">
          {PIPELINE_STEPS.map((step, i) => (
            <span key={step} className="contents">
              {i > 0 && (
                <span className="text-slate-500">&rarr;</span>
              )}
              <span className="bg-slate-800 px-2.5 py-1 rounded text-blue-300">
                {step}
              </span>
            </span>
          ))}
        </div>
      </Card>
    </div>
  );
}
