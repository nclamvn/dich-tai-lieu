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
  engine_id?: string;
  profile_id?: string;
  glossary_ids?: string[];
}

// ─── Translation Engines ───

export interface TranslationEngine {
  id: string;
  name: string;
  available: boolean;
  status: "available" | "unavailable" | "loading" | "error";
  languages_count: number;
  offline?: boolean;
  cost_per_token?: number;
  cost_per_1k_tokens?: number;
  quality?: string;
  size_gb?: number;
  model?: string;
  error?: string;
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

export type InputMode = "seeds" | "messy_draft" | "enrich" | "continue_draft";
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

// ─── Book Writer v2 (9-agent pipeline) ───

export type BookV2Genre =
  | "non-fiction" | "fiction" | "technical" | "business"
  | "self-help" | "academic" | "memoir" | "guide";

export type BookV2OutputFormat = "docx" | "markdown" | "pdf" | "html";

export type BookV2Status =
  | "created" | "analyzing" | "architecting" | "outlining"
  | "writing" | "expanding" | "enriching" | "editing"
  | "quality_check" | "publishing" | "completed" | "failed" | "paused";

export interface BookV2CreateRequest {
  title: string;
  description: string;
  target_pages?: number;
  subtitle?: string;
  genre?: BookV2Genre;
  audience?: string;
  author_name?: string;
  language?: string;
  output_formats?: BookV2OutputFormat[];
  words_per_page?: number;
  sections_per_chapter?: number;
  continue_from_draft?: boolean;
  draft_file_id?: string;
}

export interface DraftChapterInfo {
  chapter_number: number;
  title: string;
  word_count: number;
}

export interface DraftAnalysisResponse {
  file_id: string;
  filename: string;
  total_chapters: number;
  total_words: number;
  chapters: DraftChapterInfo[];
}

export interface DraftUploadResponse {
  file_id: string;
  filename: string;
  size: number;
}

export interface BookV2Project {
  id: string;
  status: string;
  current_agent: string;
  current_task: string;
  sections_completed: number;
  sections_total: number;
  progress_percentage: number;
  word_progress: number;
  expansion_rounds: number;
  blueprint?: BookV2Blueprint;
  output_files: Record<string, string>;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  errors: Array<{ message: string; agent?: string; timestamp?: string }>;
}

export interface BookV2Blueprint {
  title: string;
  subtitle?: string;
  author: string;
  genre: string;
  language: string;
  target_pages: number;
  actual_pages: number;
  target_words: number;
  actual_words: number;
  completion: number;
  parts: BookV2Part[];
  total_chapters: number;
  total_sections: number;
}

export interface BookV2Part {
  id: string;
  number: number;
  title: string;
  word_count: BookV2WordCount;
  chapters: BookV2Chapter[];
  is_complete: boolean;
  progress: number;
}

export interface BookV2Chapter {
  id: string;
  number: number;
  title: string;
  part_id: string;
  word_count: BookV2WordCount;
  sections: BookV2Section[];
  is_complete: boolean;
  progress: number;
  introduction_preview?: string;
  summary_preview?: string;
  key_takeaways: string[];
}

export interface BookV2Section {
  id: string;
  number: number;
  title: string;
  chapter_id: string;
  word_count: BookV2WordCount;
  status: string;
  content_preview?: string;
  expansion_attempts: number;
}

export interface BookV2WordCount {
  target: number;
  actual: number;
  completion: number;
  remaining: number;
  is_complete: boolean;
}

export interface BookV2ListResponse {
  items: BookV2Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface BookV2StructurePreview {
  target_pages: number;
  content_pages: number;
  content_words: number;
  num_parts: number;
  total_chapters: number;
  chapters_per_part: number;
  total_sections: number;
  words_per_chapter: number;
  words_per_section: number;
  estimated_time_minutes: number;
}

export interface BookV2Content {
  title: string;
  subtitle?: string;
  author: string;
  parts: Array<{
    number: number;
    title: string;
    introduction: string;
    chapters: Array<{
      number: number;
      title: string;
      introduction: string;
      sections: Array<{
        number: number;
        title: string;
        content: string;
        word_count: number;
      }>;
      summary: string;
      key_takeaways: string[];
    }>;
  }>;
  word_count: number;
  page_count: number;
}

export interface BookV2ReaderContent {
  title: string;
  author: string;
  chapters: Array<{
    number: number;
    title: string;
    content: string;
  }>;
}

// ─── Settings ───

export interface GeneralSettings {
  app_name: string;
  source_lang: string;
  target_lang: string;
  quality_mode: string;
  provider: string;
  model: string;
  theme: string;
  locale: string;
}

export interface TranslationSettingsConfig {
  concurrency: number;
  chunk_size: number;
  context_window: number;
  max_retries: number;
  retry_delay: number;
  cache_enabled: boolean;
  chunk_cache_enabled: boolean;
  chunk_cache_ttl_days: number;
  checkpoint_enabled: boolean;
  checkpoint_interval: number;
  tm_enabled: boolean;
  tm_fuzzy_threshold: number;
  glossary_enabled: boolean;
  quality_validation: boolean;
  quality_threshold: number;
}

export interface BookWriterSettingsConfig {
  default_genre: string;
  default_language: string;
  default_output_formats: string[];
  words_per_page: number;
  sections_per_chapter: number;
  max_expansion_rounds: number;
  enable_enrichment: boolean;
  enable_quality_check: boolean;
}

export interface ApiKeySettingsConfig {
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  mathpix_app_id: string;
  mathpix_app_key: string;
}

export interface ExportSettingsConfig {
  default_format: string;
  enable_beautification: boolean;
  enable_advanced_book_layout: boolean;
  streaming_enabled: boolean;
  streaming_batch_size: number;
  max_upload_size_mb: number;
}

export interface AdvancedSettingsConfig {
  security_mode: string;
  session_auth_enabled: boolean;
  api_key_auth_enabled: boolean;
  csrf_enabled: boolean;
  rate_limit: string;
  database_backend: string;
  use_ast_pipeline: boolean;
  cleanup_upload_retention_days: number;
  cleanup_output_retention_days: number;
  cleanup_temp_max_age_hours: number;
  debug_mode: boolean;
}

export interface AllSettings {
  general: GeneralSettings;
  translation: TranslationSettingsConfig;
  book_writer: BookWriterSettingsConfig;
  api_keys: ApiKeySettingsConfig;
  export: ExportSettingsConfig;
  advanced: AdvancedSettingsConfig;
}

// ─── Translation Memory ───

export interface TMItem {
  id: string;
  name: string;
  description?: string;
  source_language: string;
  target_language: string;
  domain: string;
  segment_count: number;
  total_words: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TMListResponse {
  tms: TMItem[];
  total: number;
}

export interface TMSegment {
  id: string;
  tm_id: string;
  source_text: string;
  target_text: string;
  quality_score: number;
  source_type: "ai" | "human" | "verified";
  context_before?: string;
  context_after?: string;
  project_name?: string;
  notes?: string;
  source_length: number;
  usage_count: number;
  last_used_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TMSegmentListResponse {
  segments: TMSegment[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface TMMatch {
  segment_id: string;
  source_text: string;
  target_text: string;
  similarity: number;
  match_type: "exact" | "near_exact" | "fuzzy" | "no_match";
  quality_score: number;
  source_type: string;
  tm_id: string;
  tm_name: string;
}

export interface TMLookupResponse {
  matches: TMMatch[];
  best_match?: TMMatch;
  match_count: number;
}

export interface TMStats {
  tm_id: string;
  tm_name: string;
  segment_count: number;
  total_words: number;
  source_language: string;
  target_language: string;
  domain: string;
  created_at: string;
  updated_at: string;
}

// ─── Batch Processing ───

export interface BatchFile {
  file_id: string;
  filename: string;
  status: string;
  progress: number;
  job_id?: string;
  error?: string;
}

export interface BatchJob {
  batch_id: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  total_files: number;
  completed_files: number;
  failed_files: number;
  overall_progress: number;
  current_file?: string;
  files: BatchFile[];
  source_language: string;
  target_language: string;
  profile_id: string;
  output_formats: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  zip_available: boolean;
}

export interface BatchListResponse {
  batches: BatchJob[];
  total: number;
}

// ─── Editor / CAT Tool ───

export interface EditorSegment {
  chunk_id: string;
  index: number;
  source: string;
  translated: string;
  quality_score: number;
  is_edited: boolean;
  warnings: string[];
}

export interface EditorJob {
  job_id: string;
  segments: EditorSegment[];
  completion_percentage: number;
  can_export: boolean;
}

// ─── Output Formats ───

export const OUTPUT_FORMATS = [
  { value: "docx", label: "Word (.docx)" },
  { value: "pdf", label: "PDF (.pdf)" },
  { value: "epub", label: "EPUB (.epub)" },
  { value: "markdown", label: "Markdown (.md)" },
  { value: "txt", label: "Plain Text (.txt)" },
];
