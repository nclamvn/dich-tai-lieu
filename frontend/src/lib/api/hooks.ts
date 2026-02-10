/**
 * React Query hooks for all API endpoints.
 * Provides caching, polling, optimistic updates, and WebSocket real-time progress.
 */
"use client";

import { useEffect, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobs, glossaries, dashboard, profiles, bookWriter } from "./client";
import type { TranslateRequest, CreateBookRequest, ApproveOutlineRequest } from "./types";

const WS_URL =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .replace(/^http/, "ws") + "/ws";

// ─── WebSocket ───

/**
 * Hook for real-time job progress via WebSocket.
 * Updates React Query cache on each `job_progress` event.
 * Falls back to polling if WebSocket disconnects.
 */
export function useJobWebSocket(jobId: string | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(() => {
    if (!jobId) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ action: "subscribe", job_id: jobId }));
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.event === "job_progress" && data.job_id === jobId) {
            // Update the React Query cache with latest progress
            queryClient.setQueryData(["job", jobId], (old: any) => {
              if (!old) return old;
              return {
                ...old,
                progress: data.progress,
                current_stage: data.stage,
                status: data.status,
              };
            });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        // Reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3_000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket not available, fall back to polling
    }
  }, [jobId, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);
}

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
      if (status === "processing" || status === "pending") return 10_000;
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

// ─── Reader ───

export function useReaderContent(jobId: string | null) {
  return useQuery({
    queryKey: ["reader-content", jobId],
    queryFn: () => jobs.getReaderContent(jobId!),
    enabled: !!jobId,
    staleTime: 5 * 60_000,
  });
}

// ─── Book Writer WebSocket ───

const BOOK_WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .replace(/^http/, "ws") + "/api/v2/books";

/**
 * Real-time book pipeline progress via WebSocket.
 *
 * Connects to WS /api/v2/books/{bookId}/ws and handles:
 * - status_change → update status + progress in cache
 * - chapter_progress → update progress fields in cache
 * - pipeline_complete → invalidate to get final state
 * - error → set error in cache
 *
 * Falls back to polling (useBookProject refetchInterval) when WS unavailable.
 */
export function useBookWebSocket(bookId: string | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const pingTimer = useRef<ReturnType<typeof setInterval>>(undefined);

  const connect = useCallback(() => {
    if (!bookId) return;

    try {
      const ws = new WebSocket(`${BOOK_WS_BASE}/${bookId}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send ping every 30s to keep alive
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30_000);
      };

      ws.onmessage = (evt) => {
        if (evt.data === "pong") return;

        try {
          const msg = JSON.parse(evt.data);
          const event = msg.event;
          const data = msg.data || {};

          if (event === "status_change") {
            queryClient.setQueryData(["book-project", bookId], (old: any) => {
              if (!old) return old;
              return {
                ...old,
                status: data.status || old.status,
                error: data.error || old.error,
                progress: data.progress
                  ? { ...old.progress, ...data.progress }
                  : old.progress,
              };
            });
          }

          if (event === "chapter_progress") {
            queryClient.setQueryData(["book-project", bookId], (old: any) => {
              if (!old) return old;
              return {
                ...old,
                progress: {
                  ...old.progress,
                  current_agent: data.agent || old.progress?.current_agent,
                  current_chapter: data.chapter ?? old.progress?.current_chapter,
                  total_chapters: data.total ?? old.progress?.total_chapters,
                  chapters_written:
                    data.agent === "writer"
                      ? (data.chapters_done ?? old.progress?.chapters_written)
                      : old.progress?.chapters_written,
                  chapters_enriched:
                    data.agent === "enricher"
                      ? (data.chapters_done ?? old.progress?.chapters_enriched)
                      : old.progress?.chapters_enriched,
                  chapters_edited:
                    data.agent === "editor"
                      ? (data.chapters_done ?? old.progress?.chapters_edited)
                      : old.progress?.chapters_edited,
                },
              };
            });
          }

          if (event === "chapter_complete") {
            // Refetch to get updated chapter content
            queryClient.invalidateQueries({ queryKey: ["book-project", bookId] });
          }

          if (event === "pipeline_complete") {
            // Full refetch for final state (output files, etc.)
            queryClient.invalidateQueries({ queryKey: ["book-project", bookId] });
            queryClient.invalidateQueries({ queryKey: ["book-projects"] });
          }

          if (event === "error") {
            queryClient.setQueryData(["book-project", bookId], (old: any) => {
              if (!old) return old;
              return {
                ...old,
                status: "failed",
                error: data.message || data.error || "Unknown error",
              };
            });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        clearInterval(pingTimer.current);
        // Reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3_000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket not available, fall back to polling
    }
  }, [bookId, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      clearInterval(pingTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);
}

// ─── Book Writer ───

export function useBookProjects() {
  return useQuery({
    queryKey: ["book-projects"],
    queryFn: () => bookWriter.list(),
    refetchInterval: 10_000,
  });
}

const BOOK_TERMINAL_STATUSES = new Set(["outline_ready", "complete", "failed", "paused"]);

export function useBookProject(bookId: string | null) {
  return useQuery({
    queryKey: ["book-project", bookId],
    queryFn: () => bookWriter.get(bookId!),
    enabled: !!bookId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || BOOK_TERMINAL_STATUSES.has(status)) return false;
      return 5_000;
    },
  });
}

export function useCreateBook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateBookRequest) => bookWriter.create(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book-projects"] });
    },
  });
}

export function useApproveOutline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bookId, request }: { bookId: string; request: ApproveOutlineRequest }) =>
      bookWriter.approve(bookId, request),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["book-project", vars.bookId] });
      queryClient.invalidateQueries({ queryKey: ["book-projects"] });
    },
  });
}

export function useBookReaderContent(bookId: string | null) {
  return useQuery({
    queryKey: ["book-reader-content", bookId],
    queryFn: () => bookWriter.getReaderContent(bookId!),
    enabled: !!bookId,
    staleTime: 5 * 60_000,
  });
}

export function useDeleteBook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bookId: string) => bookWriter.delete(bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book-projects"] });
    },
  });
}

// ─── Profiles ───

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: profiles.list,
  });
}
