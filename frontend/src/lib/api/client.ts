/**
 * Type-safe API client for AI Publisher Pro backend.
 *
 * Uses fetch with automatic error handling + JSON parsing.
 * All endpoints match backend routes from Sprint 1-14.
 */

import type {
  TranslationJob,
  TranslateRequest,
  JobOutput,
  Glossary,
  GlossaryListItem,
  GlossaryEntry,
  CostOverview,
  ProviderCost,
  PublishingProfile,
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

// ─── Translation Jobs ───

export const jobs = {
  async create(
    file: File,
    request: TranslateRequest,
  ): Promise<TranslationJob> {
    const formData = new FormData();
    formData.append("file", file);
    Object.entries(request).forEach(([key, value]) => {
      if (value !== undefined) {
        formData.append(
          key,
          Array.isArray(value) ? JSON.stringify(value) : String(value),
        );
      }
    });

    const res = await fetch(`${API_BASE}/api/v2/translate`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new ApiError(res.status, data?.detail || "Upload failed", data);
    }

    return res.json();
  },

  async get(jobId: string): Promise<TranslationJob> {
    return apiFetch(`/api/v2/jobs/${jobId}`);
  },

  async list(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ jobs: TranslationJob[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return apiFetch(`/api/v2/jobs${qs ? `?${qs}` : ""}`);
  },

  async delete(jobId: string): Promise<void> {
    await apiFetch(`/api/v2/jobs/${jobId}`, { method: "DELETE" });
  },

  async getOutputs(jobId: string): Promise<{ outputs: JobOutput[] }> {
    return apiFetch(`/api/v2/jobs/${jobId}/outputs`);
  },

  getDownloadUrl(jobId: string, filename: string): string {
    return `${API_BASE}/api/v2/jobs/${jobId}/outputs/${filename}`;
  },

  async getPreview(jobId: string): Promise<{ preview: string }> {
    return apiFetch(`/api/v2/jobs/${jobId}/preview`);
  },
};

// ─── Glossaries ───

export const glossaries = {
  async list(
    sourceLang?: string,
    targetLang?: string,
  ): Promise<{ glossaries: GlossaryListItem[] }> {
    const params = new URLSearchParams();
    if (sourceLang) params.set("source_lang", sourceLang);
    if (targetLang) params.set("target_lang", targetLang);
    const qs = params.toString();
    return apiFetch(`/api/v2/glossaries${qs ? `?${qs}` : ""}`);
  },

  async get(id: string): Promise<{ glossary: Glossary }> {
    return apiFetch(`/api/v2/glossaries/${id}`);
  },

  async create(data: {
    name: string;
    source_language: string;
    target_language: string;
    project?: string;
  }): Promise<{ glossary: Glossary }> {
    return apiFetch("/api/v2/glossaries", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async delete(id: string): Promise<void> {
    await apiFetch(`/api/v2/glossaries/${id}`, { method: "DELETE" });
  },

  async addEntry(
    glossaryId: string,
    entry: {
      source_term: string;
      target_term: string;
      context?: string;
      notes?: string;
      domain?: string;
    },
  ): Promise<{ entry: GlossaryEntry }> {
    return apiFetch(`/api/v2/glossaries/${glossaryId}/entries`, {
      method: "POST",
      body: JSON.stringify(entry),
    });
  },

  async removeEntry(glossaryId: string, entryId: string): Promise<void> {
    await apiFetch(`/api/v2/glossaries/${glossaryId}/entries/${entryId}`, {
      method: "DELETE",
    });
  },

  async search(
    glossaryId: string,
    query: string,
  ): Promise<{ entries: GlossaryEntry[] }> {
    return apiFetch(
      `/api/v2/glossaries/${glossaryId}/search?q=${encodeURIComponent(query)}`,
    );
  },

  async importEntries(
    glossaryId: string,
    entries: Array<{ source_term: string; target_term: string }>,
  ): Promise<{ imported: number }> {
    return apiFetch(`/api/v2/glossaries/${glossaryId}/import`, {
      method: "POST",
      body: JSON.stringify({ entries }),
    });
  },

  async exportEntries(glossaryId: string): Promise<{
    glossary_name: string;
    language_pair: string;
    entries: GlossaryEntry[];
  }> {
    return apiFetch(`/api/v2/glossaries/${glossaryId}/export`);
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

  async estimate(params: {
    pages?: number;
    language_pair?: string;
    provider?: string;
  }): Promise<{ estimated_cost_usd: number; provider: string }> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) searchParams.set(k, String(v));
    });
    return apiFetch(`/api/dashboard/estimate?${searchParams}`);
  },

  async getCheapest(): Promise<ProviderCost | { provider: null }> {
    return apiFetch("/api/dashboard/cheapest");
  },

  async getBestValue(): Promise<ProviderCost | { provider: null }> {
    return apiFetch("/api/dashboard/best-value");
  },
};

// ─── Profiles ───

export const profiles = {
  async list(): Promise<{ profiles: PublishingProfile[] }> {
    try {
      return await apiFetch("/api/v2/profiles");
    } catch {
      // Fallback: profiles may be frontend-only for now
      return { profiles: [] };
    }
  },

  async get(id: string): Promise<{ profile: PublishingProfile }> {
    return apiFetch(`/api/v2/profiles/${id}`);
  },
};
