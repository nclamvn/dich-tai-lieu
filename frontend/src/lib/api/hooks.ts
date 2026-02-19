/**
 * React Query hooks for all API endpoints.
 * Provides caching, polling, optimistic updates, and WebSocket real-time progress.
 */
"use client";

import { useEffect, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobs, glossaries, dashboard, profiles, bookWriter, bookWriterV2, engines, settingsApi, tm, batch, editor } from "./client";
import type { TranslateRequest, CreateBookRequest, ApproveOutlineRequest, BookV2CreateRequest, TMSegment, DraftUploadResponse, DraftAnalysisResponse } from "./types";

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

// ─── Engines ───

export function useTranslationEngines() {
  return useQuery({
    queryKey: ["translation-engines"],
    queryFn: () => engines.list(),
    staleTime: 30_000,
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

// ─── Book Writer v2 (9-agent pipeline) ───

const BOOK_V2_WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .replace(/^http/, "ws") + "/api/v2/books-v2";

const BOOK_V2_TERMINAL = new Set(["completed", "failed", "paused"]);

export function useBookV2Projects(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["book-v2-projects", page, pageSize],
    queryFn: () => bookWriterV2.list(page, pageSize),
    refetchInterval: 10_000,
  });
}

export function useBookV2Project(projectId: string | null) {
  return useQuery({
    queryKey: ["book-v2-project", projectId],
    queryFn: () => bookWriterV2.get(projectId!, true),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || BOOK_V2_TERMINAL.has(status)) return false;
      return 5_000;
    },
  });
}

export function useBookV2StructurePreview(targetPages: number | null) {
  return useQuery({
    queryKey: ["book-v2-structure", targetPages],
    queryFn: () => bookWriterV2.previewStructure(targetPages!),
    enabled: !!targetPages && targetPages >= 50,
    staleTime: 60_000,
  });
}

export function useCreateBookV2() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: BookV2CreateRequest) => bookWriterV2.create(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book-v2-projects"] });
    },
  });
}

export function useDeleteBookV2() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => bookWriterV2.delete(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book-v2-projects"] });
    },
  });
}

export function usePauseBookV2() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => bookWriterV2.pause(projectId),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ["book-v2-project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["book-v2-projects"] });
    },
  });
}

export function useUploadDraftV2() {
  return useMutation({
    mutationFn: (file: File) => bookWriterV2.uploadDraft(file),
  });
}

export function useAnalyzeDraftV2() {
  return useMutation({
    mutationFn: (file: File) => bookWriterV2.analyzeDraft(file),
  });
}

export function useBookV2Content(projectId: string | null) {
  return useQuery({
    queryKey: ["book-v2-content", projectId],
    queryFn: () => bookWriterV2.getContent(projectId!),
    enabled: !!projectId,
    staleTime: 5 * 60_000,
  });
}

export function useBookV2ReaderContent(projectId: string | null) {
  return useQuery({
    queryKey: ["book-v2-reader", projectId],
    queryFn: () => bookWriterV2.getReaderContent(projectId!),
    enabled: !!projectId,
    staleTime: 5 * 60_000,
  });
}

/**
 * Real-time progress for Book Writer v2 via WebSocket.
 * Connects to /api/v2/books-v2/{id}/ws.
 * Updates React Query cache on progress events.
 */
export function useBookV2WebSocket(projectId: string | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const pingTimer = useRef<ReturnType<typeof setInterval>>(undefined);

  const connect = useCallback(() => {
    if (!projectId) return;

    try {
      const ws = new WebSocket(`${BOOK_V2_WS_BASE}/${projectId}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30_000);
      };

      ws.onmessage = (evt) => {
        if (evt.data === "pong") return;

        try {
          const msg = JSON.parse(evt.data);
          // Progress update from pipeline
          queryClient.setQueryData(["book-v2-project", projectId], (old: any) => {
            if (!old) return old;
            return {
              ...old,
              current_agent: msg.agent || old.current_agent,
              current_task: msg.message || old.current_task,
              progress_percentage: msg.percentage ?? old.progress_percentage,
            };
          });

          // If percentage is 100, invalidate for final state
          if (msg.percentage >= 100) {
            queryClient.invalidateQueries({ queryKey: ["book-v2-project", projectId] });
            queryClient.invalidateQueries({ queryKey: ["book-v2-projects"] });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        clearInterval(pingTimer.current);
        reconnectTimer.current = setTimeout(connect, 3_000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket not available
    }
  }, [projectId, queryClient]);

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

// ─── Settings ───

export function useAllSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.getAll,
  });
}

export function useSettingsSection<T = Record<string, unknown>>(section: string) {
  return useQuery({
    queryKey: ["settings", section],
    queryFn: () => settingsApi.getSection<T>(section),
  });
}

export function useUpdateSettings<T = Record<string, unknown>>(section: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: T) => settingsApi.updateSection(section, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", section] });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}

export function useResetSettings(section: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => settingsApi.resetSection(section),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", section] });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
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

// ─── Translation Memory ───

export function useTMs(params?: {
  source_language?: string;
  target_language?: string;
  domain?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: ["tms", params],
    queryFn: () => tm.list(params),
  });
}

export function useTM(tmId: string | null) {
  return useQuery({
    queryKey: ["tm", tmId],
    queryFn: () => tm.get(tmId!),
    enabled: !!tmId,
  });
}

export function useTMSegments(tmId: string | null, params?: {
  page?: number;
  limit?: number;
  search?: string;
}) {
  return useQuery({
    queryKey: ["tm-segments", tmId, params],
    queryFn: () => tm.listSegments(tmId!, params),
    enabled: !!tmId,
  });
}

export function useTMStats(tmId: string | null) {
  return useQuery({
    queryKey: ["tm-stats", tmId],
    queryFn: () => tm.getStats(tmId!),
    enabled: !!tmId,
  });
}

export function useCreateTM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tm.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tms"] }),
  });
}

export function useDeleteTM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tmId: string) => tm.delete(tmId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tms"] }),
  });
}

export function useAddTMSegment(tmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { source_text: string; target_text: string; quality_score?: number }) =>
      tm.addSegment(tmId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tm-segments", tmId] });
      qc.invalidateQueries({ queryKey: ["tm", tmId] });
    },
  });
}

export function useDeleteTMSegment(tmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (segmentId: string) => tm.deleteSegment(tmId, segmentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tm-segments", tmId] });
      qc.invalidateQueries({ queryKey: ["tm", tmId] });
    },
  });
}

export function useImportTM(tmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => tm.importFile(tmId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tm-segments", tmId] });
      qc.invalidateQueries({ queryKey: ["tm", tmId] });
    },
  });
}

export function useTMLookup() {
  return useMutation({
    mutationFn: ({ tmIds, sourceText, minSimilarity }: {
      tmIds: string[];
      sourceText: string;
      minSimilarity?: number;
    }) => tm.lookup(tmIds, sourceText, minSimilarity),
  });
}

// ─── Batch Processing ───

export function useBatches() {
  return useQuery({
    queryKey: ["batches"],
    queryFn: batch.list,
    refetchInterval: 10_000,
  });
}

export function useBatchStatus(batchId: string | null) {
  return useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => batch.getStatus(batchId!),
    enabled: !!batchId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed" || status === "cancelled") return false;
      return 3_000;
    },
  });
}

export function useCreateBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ files, sourceLang, targetLang, outputFormats, profileId }: {
      files: File[];
      sourceLang: string;
      targetLang: string;
      outputFormats?: string[];
      profileId?: string;
    }) => batch.create(files, sourceLang, targetLang, outputFormats, profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["batches"] }),
  });
}

export function useStartBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => batch.start(batchId),
    onSuccess: (_, batchId) => qc.invalidateQueries({ queryKey: ["batch", batchId] }),
  });
}

export function useCancelBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => batch.cancel(batchId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["batches"] }),
  });
}

export function useDeleteBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => batch.delete(batchId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["batches"] }),
  });
}

// ─── Editor / CAT Tool ───

export function useEditorSegments(jobId: string | null) {
  return useQuery({
    queryKey: ["editor-segments", jobId],
    queryFn: () => editor.getSegments(jobId!),
    enabled: !!jobId,
  });
}

export function useUpdateEditorSegment(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ chunkId, translatedText }: { chunkId: string; translatedText: string }) =>
      editor.updateSegment(jobId, chunkId, translatedText),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["editor-segments", jobId] }),
  });
}

export function useRegenerateDocument(jobId: string) {
  return useMutation({
    mutationFn: () => editor.regenerate(jobId),
  });
}
