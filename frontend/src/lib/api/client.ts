/**
 * Type-safe API client for AI Publisher Pro backend.
 *
 * Endpoints matched to actual backend routes (verified 2026-02-09).
 */

import type {
  TranslationJob,
  TranslateRequest,
  TranslationEngine,
  ReaderContent,
  Glossary,
  GlossaryListItem,
  GlossaryEntry,
  CostOverview,
  ProviderCost,
  PublishingProfile,
  BookProject,
  BookListItem,
  BookChapter,
  CreateBookRequest,
  ApproveOutlineRequest,
  BookV2CreateRequest,
  BookV2Project,
  BookV2ListResponse,
  BookV2StructurePreview,
  BookV2Content,
  BookV2ReaderContent,
  DraftUploadResponse,
  DraftAnalysisResponse,
  AllSettings,
  TMItem,
  TMListResponse,
  TMSegment,
  TMSegmentListResponse,
  TMLookupResponse,
  TMStats,
  BatchJob,
  BatchListResponse,
  EditorJob,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Base Fetch ───

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(
      res.status,
      data?.detail || `API error: ${res.status}`,
      data,
    );
  }

  return res.json();
}

// ─── Translation Engines ───

export const engines = {
  async list(): Promise<TranslationEngine[]> {
    return apiFetch<TranslationEngine[]>("/api/engines");
  },
};

// ─── Language Detection ───

export async function detectLanguage(
  file: File,
): Promise<{ language: string; confidence: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v2/detect-language`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new ApiError(res.status, "Language detection failed");
  }

  return res.json();
}

// ─── Translation Jobs ───

// Map V2 status to frontend status
function mapV2Status(status: string): TranslationJob["status"] {
  switch (status) {
    case "running":
    case "vision_reading":
    case "extracting_dna":
    case "chunking":
    case "translating":
    case "assembling":
    case "converting":
    case "verifying":
      return "processing";
    case "complete":
      return "completed";
    case "cancelled":
      return "cancelled";
    default:
      return status as TranslationJob["status"];
  }
}

function mapV2Job(data: Record<string, unknown>): TranslationJob {
  const outputPaths = (data.output_paths as Record<string, string>) || {};
  return {
    id: (data.job_id as string) || "",
    status: mapV2Status(data.status as string),
    source_language: (data.source_language as string) || "",
    target_language: (data.target_language as string) || "",
    source_filename: (data.source_file as string) || "",
    output_format: ((data.output_formats as string[]) || ["docx"])[0],
    created_at: (data.created_at as string) || "",
    updated_at: (data.completed_at as string) || (data.created_at as string) || "",
    progress: (data.progress as number) || 0,
    error: (data.error as string) || undefined,
    _outputPaths: outputPaths,
    _qualityScore: data.quality_score as number | undefined,
    _qualityLevel: data.quality_level as string | undefined,
    _currentStage: data.current_stage as string | undefined,
  };
}

export const jobs = {
  async create(
    file: File,
    request: TranslateRequest,
  ): Promise<TranslationJob> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_language", request.source_language);
    formData.append("target_language", request.target_language);
    formData.append(
      "output_formats",
      request.output_formats ? request.output_formats.join(",") : "docx",
    );
    if (request.profile_id) formData.append("profile_id", request.profile_id);
    if (request.engine_id && request.engine_id !== "auto")
      formData.append("engine", request.engine_id);

    const res = await fetch(`${API_BASE}/api/v2/publish`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || "Upload failed", data);
    }

    const data = await res.json();
    // V2 publish returns { job_id, status, source_file, progress (0-100), ... }
    return {
      id: data.job_id,
      status: mapV2Status(data.status),
      source_language: data.source_language || request.source_language,
      target_language: data.target_language || request.target_language,
      source_filename: data.source_file || file.name,
      output_format: (data.output_formats || ["docx"])[0],
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.created_at || new Date().toISOString(),
      progress: data.progress || 0,
      error: data.error || undefined,
    };
  },

  async get(jobId: string): Promise<TranslationJob> {
    const data = await apiFetch<Record<string, unknown>>(
      `/api/v2/jobs/${jobId}`,
    );
    return mapV2Job(data);
  },

  async list(params?: {
    status?: string;
    limit?: number;
  }): Promise<{ jobs: TranslationJob[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();

    // GET /api/v2/jobs returns V2 job list
    const data = await apiFetch<Array<Record<string, unknown>>>(
      `/api/v2/jobs${qs ? `?${qs}` : ""}`,
    );
    const mapped = data.map((d) => mapV2Job(d));
    return {
      jobs: params?.status ? mapped.filter((j) => j.status === params.status) : mapped,
      total: mapped.length,
    };
  },

  async delete(jobId: string): Promise<void> {
    await apiFetch(`/api/v2/jobs`, {
      method: "DELETE",
      body: JSON.stringify([jobId]),
    });
  },

  async bulkDelete(jobIds: string[]): Promise<{ deleted: number }> {
    return apiFetch(`/api/v2/jobs`, {
      method: "DELETE",
      body: JSON.stringify(jobIds),
    });
  },

  getDownloadUrl(jobId: string, format: string): string {
    return `${API_BASE}/api/v2/jobs/${jobId}/download/${format}`;
  },

  async getReaderContent(jobId: string): Promise<ReaderContent> {
    return apiFetch<ReaderContent>(`/api/v2/jobs/${jobId}/reader-content`);
  },

  async download(jobId: string, format: string, filename?: string): Promise<void> {
    // Use fetch + blob for cross-origin downloads
    const res = await fetch(`${API_BASE}/api/v2/jobs/${jobId}/download/${format}`);
    if (!res.ok) throw new ApiError(res.status, "Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    // Content-Disposition not accessible cross-origin, use provided filename
    a.download = filename || res.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1] || `output.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ─── Book Writer ───

export const bookWriter = {
  async create(request: CreateBookRequest): Promise<BookProject> {
    return apiFetch<BookProject>("/api/v2/books/", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  async get(bookId: string): Promise<BookProject> {
    return apiFetch<BookProject>(`/api/v2/books/${bookId}`);
  },

  async list(limit = 20, offset = 0): Promise<BookListItem[]> {
    return apiFetch<BookListItem[]>(`/api/v2/books/?limit=${limit}&offset=${offset}`);
  },

  async approve(bookId: string, request: ApproveOutlineRequest): Promise<BookProject> {
    return apiFetch<BookProject>(`/api/v2/books/${bookId}/approve`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  async delete(bookId: string): Promise<void> {
    await apiFetch(`/api/v2/books/${bookId}`, { method: "DELETE" });
  },

  async getChapter(bookId: string, chapterNum: number): Promise<BookChapter> {
    return apiFetch<BookChapter>(`/api/v2/books/${bookId}/chapters/${chapterNum}`);
  },

  async editChapter(bookId: string, chapterNum: number, content: string): Promise<BookChapter> {
    return apiFetch<BookChapter>(`/api/v2/books/${bookId}/chapters/${chapterNum}`, {
      method: "PUT",
      body: JSON.stringify({ chapter_number: chapterNum, content }),
    });
  },

  async regenerateChapter(bookId: string, chapterNum: number, instructions?: string): Promise<any> {
    return apiFetch(`/api/v2/books/${bookId}/chapters/${chapterNum}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ chapter_number: chapterNum, instructions }),
    });
  },

  async uploadDraft(file: File): Promise<{ file_id: string; filename: string; size: number }> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/v2/books/upload-draft`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || res.statusText, data);
    }
    return res.json();
  },

  async getReaderContent(bookId: string): Promise<ReaderContent> {
    return apiFetch<ReaderContent>(`/api/v2/books/${bookId}/reader-content`);
  },

  getDownloadUrl(bookId: string, format: string = "docx"): string {
    return `${API_BASE}/api/v2/books/${bookId}/download/${format}`;
  },
};

// ─── Book Writer v2 (9-agent pipeline) ───

export const bookWriterV2 = {
  async create(request: BookV2CreateRequest): Promise<BookV2Project> {
    return apiFetch<BookV2Project>("/api/v2/books-v2/", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  async get(projectId: string, includeBlueprint = false): Promise<BookV2Project> {
    const qs = includeBlueprint ? "?include_blueprint=true" : "";
    return apiFetch<BookV2Project>(`/api/v2/books-v2/${projectId}${qs}`);
  },

  async list(page = 1, pageSize = 20, status?: string): Promise<BookV2ListResponse> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.set("status", status);
    return apiFetch<BookV2ListResponse>(`/api/v2/books-v2/?${params}`);
  },

  async delete(projectId: string): Promise<void> {
    await apiFetch(`/api/v2/books-v2/${projectId}`, { method: "DELETE" });
  },

  async previewStructure(targetPages: number): Promise<BookV2StructurePreview> {
    return apiFetch<BookV2StructurePreview>(
      `/api/v2/books-v2/preview-structure?target_pages=${targetPages}`,
      { method: "POST" },
    );
  },

  async pause(projectId: string): Promise<void> {
    await apiFetch(`/api/v2/books-v2/${projectId}/pause`, { method: "POST" });
  },

  async getContent(projectId: string): Promise<BookV2Content> {
    return apiFetch<BookV2Content>(`/api/v2/books-v2/${projectId}/content`);
  },

  async getReaderContent(projectId: string): Promise<BookV2ReaderContent> {
    return apiFetch<BookV2ReaderContent>(`/api/v2/books-v2/${projectId}/reader-content`);
  },

  getDownloadUrl(projectId: string, format: string = "docx"): string {
    return `${API_BASE}/api/v2/books-v2/${projectId}/download/${format}`;
  },

  async download(projectId: string, format: string, filename?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/v2/books-v2/${projectId}/download/${format}`);
    if (!res.ok) throw new ApiError(res.status, "Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `book.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  async uploadDraft(file: File): Promise<DraftUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/v2/books-v2/upload-draft`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || res.statusText, data);
    }
    return res.json();
  },

  async analyzeDraft(file: File): Promise<DraftAnalysisResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/v2/books-v2/analyze-draft`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || res.statusText, data);
    }
    return res.json();
  },
};

// ─── Settings ───

export const settingsApi = {
  async getAll(): Promise<AllSettings> {
    return apiFetch<AllSettings>("/api/settings/");
  },

  async getSection<T = Record<string, unknown>>(section: string): Promise<T> {
    return apiFetch<T>(`/api/settings/${section}`);
  },

  async updateSection<T = Record<string, unknown>>(section: string, data: T): Promise<T> {
    return apiFetch<T>(`/api/settings/${section}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async resetSection<T = Record<string, unknown>>(section: string): Promise<T> {
    return apiFetch<T>(`/api/settings/${section}/reset`, {
      method: "POST",
    });
  },
};

// ─── Glossaries ───

const GLOSSARY_BASE = "/api/glossary/api/glossary";

export const glossaries = {
  async list(
    sourceLang?: string,
    targetLang?: string,
  ): Promise<{ glossaries: GlossaryListItem[] }> {
    const params = new URLSearchParams();
    if (sourceLang) params.set("source_language", sourceLang);
    if (targetLang) params.set("target_language", targetLang);
    const qs = params.toString();
    const data = await apiFetch<{
      glossaries: Array<Record<string, unknown>>;
      total: number;
    }>(`${GLOSSARY_BASE}/${qs ? `?${qs}` : ""}`);

    return {
      glossaries: data.glossaries.map((g) => ({
        id: g.id as string,
        name: g.name as string,
        language_pair: `${g.source_language}→${g.target_language}`,
        project: (g.domain as string) || "",
        entry_count: (g.term_count as number) || 0,
      })),
    };
  },

  async get(id: string): Promise<{ glossary: Glossary }> {
    const g = await apiFetch<Record<string, unknown>>(
      `${GLOSSARY_BASE}/${id}`,
    );
    const termsData = await apiFetch<{
      terms: Array<Record<string, unknown>>;
      total: number;
    }>(`${GLOSSARY_BASE}/${id}/terms?limit=200`);

    return {
      glossary: {
        id: g.id as string,
        name: g.name as string,
        source_language: g.source_language as string,
        target_language: g.target_language as string,
        language_pair: `${g.source_language}→${g.target_language}`,
        project: (g.domain as string) || "",
        entry_count: (g.term_count as number) || 0,
        entries: termsData.terms.map((t) => ({
          id: t.id as string,
          source_term: t.source_term as string,
          target_term: t.target_term as string,
          context: (t.context as string) || "",
          notes: "",
          domain: (t.part_of_speech as string) || "",
          approved: true,
          created_at: 0,
          updated_at: 0,
        })),
        created_at: 0,
        updated_at: 0,
      },
    };
  },

  async create(data: {
    name: string;
    source_language: string;
    target_language: string;
    project?: string;
  }): Promise<{ glossary: Glossary }> {
    const g = await apiFetch<Record<string, unknown>>(`${GLOSSARY_BASE}/`, {
      method: "POST",
      body: JSON.stringify({
        name: data.name,
        source_language: data.source_language,
        target_language: data.target_language,
        domain: data.project || "general",
      }),
    });
    return {
      glossary: {
        id: g.id as string,
        name: g.name as string,
        source_language: g.source_language as string,
        target_language: g.target_language as string,
        language_pair: `${g.source_language}→${g.target_language}`,
        project: (g.domain as string) || "",
        entry_count: 0,
        entries: [],
        created_at: 0,
        updated_at: 0,
      },
    };
  },

  async delete(id: string): Promise<void> {
    await apiFetch(`${GLOSSARY_BASE}/${id}`, { method: "DELETE" });
  },

  async addEntry(
    glossaryId: string,
    entry: {
      source_term: string;
      target_term: string;
      context?: string;
    },
  ): Promise<{ entry: GlossaryEntry }> {
    const t = await apiFetch<Record<string, unknown>>(
      `${GLOSSARY_BASE}/${glossaryId}/terms`,
      {
        method: "POST",
        body: JSON.stringify(entry),
      },
    );
    return {
      entry: {
        id: t.id as string,
        source_term: t.source_term as string,
        target_term: t.target_term as string,
        context: (t.context as string) || "",
        notes: "",
        domain: (t.part_of_speech as string) || "",
        approved: true,
        created_at: 0,
        updated_at: 0,
      },
    };
  },

  async removeEntry(glossaryId: string, entryId: string): Promise<void> {
    await apiFetch(`${GLOSSARY_BASE}/${glossaryId}/terms/${entryId}`, {
      method: "DELETE",
    });
  },

  async importEntries(
    glossaryId: string,
    entries: Array<{ source_term: string; target_term: string }>,
  ): Promise<{ imported: number }> {
    const data = await apiFetch<{ added: number }>(
      `${GLOSSARY_BASE}/${glossaryId}/terms/bulk`,
      {
        method: "POST",
        body: JSON.stringify({ terms: entries, skip_duplicates: true }),
      },
    );
    return { imported: data.added };
  },

  async exportEntries(glossaryId: string): Promise<{
    glossary_name: string;
    language_pair: string;
    entries: GlossaryEntry[];
  }> {
    // Export returns a file download, so we use terms list instead
    const termsData = await apiFetch<{
      terms: Array<Record<string, unknown>>;
    }>(`${GLOSSARY_BASE}/${glossaryId}/terms?limit=1000`);

    return {
      glossary_name: glossaryId,
      language_pair: "",
      entries: termsData.terms.map((t) => ({
        id: t.id as string,
        source_term: t.source_term as string,
        target_term: t.target_term as string,
        context: (t.context as string) || "",
        notes: "",
        domain: (t.part_of_speech as string) || "",
        approved: true,
        created_at: 0,
        updated_at: 0,
      })),
    };
  },
};

// ─── Dashboard ───

export const dashboard = {
  async getOverview(): Promise<CostOverview> {
    return apiFetch("/api/dashboard/overview");
  },

  async getProviders(): Promise<ProviderCost[]> {
    return apiFetch("/api/dashboard/providers");
  },

  async getLanguagePairs(): Promise<Record<string, number>> {
    return apiFetch("/api/dashboard/language-pairs");
  },
};

// ─── Profiles ───

export const profiles = {
  async list(): Promise<{ profiles: PublishingProfile[] }> {
    try {
      const data = await apiFetch<{
        profiles: Array<Record<string, unknown>>;
      }>("/api/v2/profiles");
      return {
        profiles: data.profiles.map((p) => ({
          id: p.id as string,
          name: p.name as string,
          description: (p.description as string) || "",
          source_language: "",
          target_language: "",
          language_pair: "",
          translation: {
            preferred_provider: "",
            routing_mode: "auto",
            glossary_ids: [],
            preserve_formatting: true,
            formality: "neutral",
          },
          output: {
            format: (p.output_format as string) || "docx",
            page_size: "A4",
            font_family: "",
            font_size: 12,
            line_spacing: 1.5,
            margins: { top: 1, bottom: 1, left: 1, right: 1 },
            include_toc: false,
            include_cover: false,
            cover_image: "",
          },
          created_at: 0,
          updated_at: 0,
        })),
      };
    } catch {
      return { profiles: [] };
    }
  },

  async get(id: string): Promise<{ profile: PublishingProfile }> {
    return apiFetch(`/api/v2/profiles/${id}`);
  },
};

// ─── Translation Memory ───

export const tm = {
  async list(params?: {
    source_language?: string;
    target_language?: string;
    domain?: string;
    search?: string;
  }): Promise<TMListResponse> {
    const sp = new URLSearchParams();
    if (params?.source_language) sp.set("source_language", params.source_language);
    if (params?.target_language) sp.set("target_language", params.target_language);
    if (params?.domain) sp.set("domain", params.domain);
    if (params?.search) sp.set("search", params.search);
    const qs = sp.toString();
    return apiFetch<TMListResponse>(`/api/tm/${qs ? `?${qs}` : ""}`);
  },

  async get(tmId: string): Promise<TMItem> {
    return apiFetch<TMItem>(`/api/tm/${tmId}`);
  },

  async create(data: {
    name: string;
    description?: string;
    source_language?: string;
    target_language?: string;
    domain?: string;
  }): Promise<TMItem> {
    return apiFetch<TMItem>("/api/tm/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async update(tmId: string, data: {
    name?: string;
    description?: string;
    domain?: string;
  }): Promise<TMItem> {
    return apiFetch<TMItem>(`/api/tm/${tmId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async delete(tmId: string): Promise<void> {
    await apiFetch(`/api/tm/${tmId}`, { method: "DELETE" });
  },

  async listSegments(tmId: string, params?: {
    page?: number;
    limit?: number;
    search?: string;
    sort?: string;
    order?: string;
  }): Promise<TMSegmentListResponse> {
    const sp = new URLSearchParams();
    if (params?.page) sp.set("page", String(params.page));
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.search) sp.set("search", params.search);
    if (params?.sort) sp.set("sort", params.sort);
    if (params?.order) sp.set("order", params.order);
    const qs = sp.toString();
    return apiFetch<TMSegmentListResponse>(`/api/tm/${tmId}/segments${qs ? `?${qs}` : ""}`);
  },

  async addSegment(tmId: string, data: {
    source_text: string;
    target_text: string;
    quality_score?: number;
    source_type?: string;
  }): Promise<TMSegment> {
    return apiFetch<TMSegment>(`/api/tm/${tmId}/segments`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateSegment(tmId: string, segmentId: string, data: {
    target_text?: string;
    quality_score?: number;
    source_type?: string;
  }): Promise<TMSegment> {
    return apiFetch<TMSegment>(`/api/tm/${tmId}/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteSegment(tmId: string, segmentId: string): Promise<void> {
    await apiFetch(`/api/tm/${tmId}/segments/${segmentId}`, { method: "DELETE" });
  },

  async lookup(tmIds: string[], sourceText: string, minSimilarity = 0.75): Promise<TMLookupResponse> {
    return apiFetch<TMLookupResponse>("/api/tm/lookup", {
      method: "POST",
      body: JSON.stringify({ tm_ids: tmIds, source_text: sourceText, min_similarity: minSimilarity }),
    });
  },

  async getStats(tmId: string): Promise<TMStats> {
    return apiFetch<TMStats>(`/api/tm/${tmId}/stats`);
  },

  async importFile(tmId: string, file: File): Promise<{ status: string; added: number; skipped: number }> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/tm/${tmId}/import`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || "Import failed", data);
    }
    return res.json();
  },

  getExportUrl(tmId: string, format: string = "json"): string {
    return `${API_BASE}/api/tm/${tmId}/export?format=${format}`;
  },
};

// ─── Batch Processing ───

export const batch = {
  async create(
    files: File[],
    sourceLang: string,
    targetLang: string,
    outputFormats: string[] = ["docx"],
    profileId?: string,
  ): Promise<BatchJob> {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    formData.append("source_language", sourceLang);
    formData.append("target_language", targetLang);
    formData.append("output_formats", outputFormats.join(","));
    if (profileId) formData.append("profile_id", profileId);

    const res = await fetch(`${API_BASE}/api/v2/batch/create`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || "Batch create failed", data);
    }
    return res.json();
  },

  async start(batchId: string): Promise<BatchJob> {
    return apiFetch<BatchJob>(`/api/v2/batch/${batchId}/start`, { method: "POST" });
  },

  async getStatus(batchId: string): Promise<BatchJob> {
    return apiFetch<BatchJob>(`/api/v2/batch/${batchId}/status`);
  },

  async cancel(batchId: string): Promise<void> {
    await apiFetch(`/api/v2/batch/${batchId}/cancel`, { method: "POST" });
  },

  async list(): Promise<BatchListResponse> {
    return apiFetch<BatchListResponse>("/api/v2/batch/");
  },

  async delete(batchId: string): Promise<void> {
    await apiFetch(`/api/v2/batch/${batchId}`, { method: "DELETE" });
  },

  getDownloadUrl(batchId: string): string {
    return `${API_BASE}/api/v2/batch/${batchId}/download`;
  },

  async download(batchId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/v2/batch/${batchId}/download`);
    if (!res.ok) throw new ApiError(res.status, "Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch_${batchId}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ─── Editor / CAT Tool ───

export const editor = {
  async getSegments(jobId: string): Promise<EditorJob> {
    return apiFetch<EditorJob>(`/editor/jobs/${jobId}/segments`);
  },

  async updateSegment(jobId: string, chunkId: string, translatedText: string): Promise<{ status: string }> {
    return apiFetch(`/editor/jobs/${jobId}/segments/${chunkId}`, {
      method: "PATCH",
      body: JSON.stringify({ translated_text: translatedText }),
    });
  },

  async regenerate(jobId: string): Promise<{ status: string; message: string }> {
    return apiFetch(`/editor/jobs/${jobId}/regenerate`, { method: "POST" });
  },
};
