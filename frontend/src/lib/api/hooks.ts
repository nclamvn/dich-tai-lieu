/**
 * React Query hooks for all API endpoints.
 * Provides caching, polling, optimistic updates.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobs, glossaries, dashboard, profiles } from "./client";
import type { TranslateRequest } from "./types";

// ─── Jobs ───

export function useJobs(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: () => jobs.list(params),
    refetchInterval: 10_000,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "processing" || status === "pending") return 3_000;
      return false;
    },
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      request,
    }: {
      file: File;
      request: TranslateRequest;
    }) => jobs.create(file, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobs.delete(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useBulkDeleteJobs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobIds: string[]) => jobs.bulkDelete(jobIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

// ─── Glossaries ───

export function useGlossaries(sourceLang?: string, targetLang?: string) {
  return useQuery({
    queryKey: ["glossaries", sourceLang, targetLang],
    queryFn: () => glossaries.list(sourceLang, targetLang),
  });
}

export function useGlossary(id: string | null) {
  return useQuery({
    queryKey: ["glossary", id],
    queryFn: () => glossaries.get(id!),
    enabled: !!id,
  });
}

export function useCreateGlossary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: glossaries.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["glossaries"] }),
  });
}

export function useDeleteGlossary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: glossaries.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["glossaries"] }),
  });
}

export function useAddGlossaryEntry(glossaryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entry: {
      source_term: string;
      target_term: string;
      context?: string;
    }) => glossaries.addEntry(glossaryId, entry),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["glossary", glossaryId] }),
  });
}

export function useRemoveGlossaryEntry(glossaryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      glossaries.removeEntry(glossaryId, entryId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["glossary", glossaryId] }),
  });
}

export function useImportGlossaryEntries(glossaryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      entries: Array<{ source_term: string; target_term: string }>,
    ) => glossaries.importEntries(glossaryId, entries),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["glossary", glossaryId] }),
  });
}

// ─── Dashboard ───

export function useCostOverview() {
  return useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: dashboard.getOverview,
    refetchInterval: 60_000,
  });
}

export function useProviderCosts() {
  return useQuery({
    queryKey: ["dashboard-providers"],
    queryFn: dashboard.getProviders,
  });
}

export function useLanguagePairCosts() {
  return useQuery({
    queryKey: ["dashboard-lang-pairs"],
    queryFn: dashboard.getLanguagePairs,
  });
}

// ─── Profiles ───

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: profiles.list,
  });
}
