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

// ─── Reader ───

export interface ReaderRegion {
  type: "text" | "heading" | "table" | "formula" | "list" | "image" | "code";
  content?: string;
  style?: string;
  level?: number;
  html?: string;
  caption?: string;
  latex?: string;
  display_text?: string;
  inline?: boolean;
  items?: string[];
  ordered?: boolean;
  alt_text?: string;
}

export interface ReaderChapter {
  id: string;
  title: string;
  regions: ReaderRegion[];
}

export interface ReaderContent {
  job_id: string;
  title: string;
  source_language: string;
  target_language: string;
  chapters: ReaderChapter[];
  metadata: {
    total_chapters: number;
    total_words: number;
    total_regions: number;
    tables: number;
    formulas: number;
    has_layout_dna: boolean;
    content_source?: string;
  };
  quality: {
    eqs_grade?: string;
    eqs_score?: number;
    consistency_score?: number;
    consistency_passed?: boolean;
    provider?: string;
    routing_mode?: string;
  };
}

export type ReaderTheme = "light" | "dark" | "sepia";
export type ReaderFont = "serif" | "sans";
export type ReaderFontSize = 0 | 1 | 2 | 3 | 4;

// ─── Output Formats ───

// ─── Book Writer ───

export type InputMode = "seeds" | "messy_draft" | "enrich";
export type Genre = "fiction" | "non_fiction" | "self_help" | "technical" | "academic" | "memoir" | "business" | "children" | "poetry" | "other";
export type OutputFormat = "docx" | "epub" | "pdf" | "markdown" | "txt";

export type BookStatus =
  | "created" | "analyzing" | "analysis_ready"
  | "architecting" | "outlining" | "outline_ready"
  | "writing" | "enriching" | "editing"
  | "compiling" | "complete" | "failed" | "paused";

export interface CreateBookRequest {
  title?: string;
  input_mode: InputMode;
  ideas?: string;
  draft_content?: string;
  draft_file_id?: string;
  language: string;
  target_pages: number;
  genre?: string;
  tone?: string;
  model?: string;
  output_formats: OutputFormat[];
  custom_instructions?: string;
  reference_style?: string;
}

export interface PipelineProgress {
  status: BookStatus;
  current_agent: string;
  current_chapter: number;
  total_chapters: number;
  chapters_written: number;
  chapters_enriched: number;
  chapters_edited: number;
  total_words: number;
  elapsed_seconds: number;
  estimated_remaining_seconds: number;
  total_tokens_in: number;
  total_tokens_out: number;
  estimated_cost_usd: number;
}

export interface AnalysisReport {
  input_mode: InputMode;
  genre: string;
  detected_language: string;
  target_audience: string;
  core_thesis: string;
  tone: string;
  strengths: string[];
  gaps: string[];
  estimated_chapters: number;
  estimated_words: number;
  key_themes: string[];
  voice_profile: string;
  recommendations: string[];
}

export interface ChapterOutlineSection {
  section_id: string;
  title: string;
  content_brief: string;
  word_target: number;
  includes: string[];
  source_material?: string;
  is_from_user: boolean;
}

export interface ChapterOutline {
  chapter_number: number;
  title: string;
  summary: string;
  word_target: number;
  opening_hook: string;
  closing_hook: string;
  sections: ChapterOutlineSection[];
  transition_from_previous: string;
  transition_to_next: string;
}

export interface BookChapter {
  chapter_number: number;
  title: string;
  status: string;
  content: string;
  enriched_content?: string;
  edited_content?: string;
  final_content?: string;
  summary: string;
  word_count: number;
  user_edits?: string;
}

export interface BookProject {
  id: string;
  created_at: string;
  updated_at: string;
  title?: string;
  status: BookStatus;
  input_mode: InputMode;
  progress: PipelineProgress;
  analysis?: AnalysisReport;
  blueprint?: any;
  outlines: ChapterOutline[];
  chapters: BookChapter[];
  chapter_count: number;
  total_words: number;
  output_files: Array<{ format: string; path: string; filename: string }>;
  error?: string;
}

export interface BookListItem {
  id: string;
  title?: string;
  status: BookStatus;
  input_mode: InputMode;
  created_at: string;
  updated_at: string;
  chapter_count: number;
  total_words: number;
}

export interface ApproveOutlineRequest {
  approved: boolean;
  chapter_adjustments?: Record<number, Record<string, any>>;
  custom_notes?: string;
}

// ─── Output Formats ───

export const OUTPUT_FORMATS = [
  { value: "docx", label: "Word (.docx)" },
  { value: "pdf", label: "PDF (.pdf)" },
  { value: "epub", label: "EPUB (.epub)" },
  { value: "markdown", label: "Markdown (.md)" },
  { value: "txt", label: "Plain Text (.txt)" },
];
