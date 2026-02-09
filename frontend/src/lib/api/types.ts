/**
 * TypeScript types matching backend API responses.
 * Single source of truth for API contract.
 */

// ─── Core Translation ───

export interface TranslationJob {
  id: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  source_language: string;
  target_language: string;
  source_filename: string;
  output_format: string;
  created_at: string;
  updated_at: string;
  progress: number;
  error?: string;

  // Quality Intelligence (Sprint 8-12)
  eqs?: EQSReport;
  qapr?: QAPRDecision;
  consistency?: ConsistencyReport;
  layout_dna?: LayoutDNAStats;

  // V2 publishing pipeline fields
  _outputPaths?: Record<string, string>;
  _qualityScore?: number;
  _qualityLevel?: string;
  _currentStage?: string;
}

export interface EQSReport {
  score: number;
  grade: string;
  signals: Record<string, number>;
  recommendation: string;
}

export interface QAPRDecision {
  selected_provider: string;
  mode: string;
  reasoning: string;
  candidates: Array<{
    provider: string;
    score: number;
  }>;
}

export interface ConsistencyReport {
  score: number;
  passed: boolean;
  issues: Array<{
    type: string;
    severity: string;
    message: string;
  }>;
}

export interface LayoutDNAStats {
  total_regions: number;
  tables: number;
  formulas: number;
}

export interface TranslateRequest {
  source_language: string;
  target_language: string;
  output_formats?: string[];
  provider?: string;
  profile_id?: string;
  glossary_ids?: string[];
}

export interface JobOutput {
  filename: string;
  format: string;
  size_bytes: number;
  download_url: string;
}

// ─── Glossary ───

export interface GlossaryEntry {
  id: string;
  source_term: string;
  target_term: string;
  context: string;
  notes: string;
  domain: string;
  approved: boolean;
  created_at: number;
  updated_at: number;
}

export interface Glossary {
  id: string;
  name: string;
  source_language: string;
  target_language: string;
  language_pair: string;
  project: string;
  entry_count: number;
  entries: GlossaryEntry[];
  created_at: number;
  updated_at: number;
}

export interface GlossaryListItem {
  id: string;
  name: string;
  language_pair: string;
  project: string;
  entry_count: number;
}

// ─── Dashboard ───

export interface CostOverview {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  avg_cost_per_call: number;
  avg_cost_per_1k_tokens: number;
}

export interface ProviderCost {
  provider: string;
  cost_usd: number;
  calls: number;
  tokens: number;
  avg_quality: number;
}

export interface LanguagePairCost {
  language_pair: string;
  cost_usd: number;
  calls: number;
}

export interface CostEstimate {
  estimated_cost_usd: number;
  provider: string;
  tokens_estimate: number;
}

// ─── Publishing Profiles ───

export interface TranslationSettings {
  preferred_provider: string;
  routing_mode: string;
  glossary_ids: string[];
  preserve_formatting: boolean;
  formality: string;
}

export interface OutputSettings {
  format: string;
  page_size: string;
  font_family: string;
  font_size: number;
  line_spacing: number;
  margins: { top: number; bottom: number; left: number; right: number };
  include_toc: boolean;
  include_cover: boolean;
  cover_image: string;
}

export interface PublishingProfile {
  id: string;
  name: string;
  description: string;
  source_language: string;
  target_language: string;
  language_pair: string;
  translation: TranslationSettings;
  output: OutputSettings;
  created_at: number;
  updated_at: number;
}

// ─── Common ───

export type Language = {
  code: string;
  name: string;
  native_name: string;
};

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: "en", name: "English", native_name: "English" },
  { code: "vi", name: "Vietnamese", native_name: "Tiếng Việt" },
  { code: "ja", name: "Japanese", native_name: "日本語" },
  { code: "zh", name: "Chinese", native_name: "中文" },
  { code: "ko", name: "Korean", native_name: "한국어" },
  { code: "th", name: "Thai", native_name: "ไทย" },
  { code: "fr", name: "French", native_name: "Français" },
  { code: "de", name: "German", native_name: "Deutsch" },
  { code: "es", name: "Spanish", native_name: "Español" },
  { code: "pt", name: "Portuguese", native_name: "Português" },
];

export const OUTPUT_FORMATS = [
  { value: "docx", label: "Word (.docx)" },
  { value: "pdf", label: "PDF (.pdf)" },
  { value: "epub", label: "EPUB (.epub)" },
  { value: "markdown", label: "Markdown (.md)" },
  { value: "txt", label: "Plain Text (.txt)" },
];
