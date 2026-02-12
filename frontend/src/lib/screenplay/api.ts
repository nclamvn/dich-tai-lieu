/**
 * Screenplay Studio API Client
 */

import {
  ScreenplayProject,
  ProjectListResponse,
  CostEstimate,
  GenerationProgress,
  CreateProjectInput,
  UpdateProjectInput,
  ProjectTier,
  VideoProvider,
} from './types';

const API_BASE = '/api/screenplay';

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// Projects CRUD
export async function listProjects(
  page: number = 1,
  pageSize: number = 10
): Promise<ProjectListResponse> {
  const data = await fetchAPI<{ items: ScreenplayProject[]; total: number; page: number; page_size: number }>(
    `/projects?page=${page}&page_size=${pageSize}`
  );
  return { projects: data.items, total: data.total, page: data.page, page_size: data.page_size };
}

export async function getProject(id: string): Promise<ScreenplayProject> {
  return fetchAPI(`/projects/${id}`);
}

export async function createProject(
  input: CreateProjectInput
): Promise<ScreenplayProject> {
  return fetchAPI('/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProject(
  id: string,
  input: UpdateProjectInput
): Promise<ScreenplayProject> {
  return fetchAPI(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function deleteProject(id: string): Promise<void> {
  await fetchAPI(`/projects/${id}`, { method: 'DELETE' });
}

// Generation
export async function startAnalysis(id: string): Promise<GenerationProgress> {
  return fetchAPI(`/projects/${id}/analyze`, { method: 'POST' });
}

export async function startGeneration(id: string): Promise<GenerationProgress> {
  return fetchAPI(`/projects/${id}/generate`, { method: 'POST' });
}

export async function startVisualization(id: string): Promise<GenerationProgress> {
  return fetchAPI(`/projects/${id}/visualize`, { method: 'POST' });
}

export async function startVideoRendering(
  id: string,
  provider?: VideoProvider
): Promise<GenerationProgress> {
  const body = provider ? JSON.stringify({ provider }) : undefined;
  return fetchAPI(`/projects/${id}/render`, {
    method: 'POST',
    body,
  });
}

export async function getProgress(id: string): Promise<GenerationProgress> {
  return fetchAPI(`/projects/${id}/progress`);
}

// Cost Estimation
export async function estimateCost(
  sourceLength: number,
  tier: ProjectTier,
  provider?: VideoProvider
): Promise<CostEstimate> {
  return fetchAPI('/estimate-cost', {
    method: 'POST',
    body: JSON.stringify({
      source_text_length: sourceLength,
      tier,
      video_provider: provider,
    }),
  });
}

// Content Retrieval
export async function getScreenplay(id: string): Promise<{
  title: string;
  author: string;
  scenes: unknown[];
  total_pages: number;
}> {
  return fetchAPI(`/projects/${id}/screenplay`);
}

// Export URLs
export function getFountainUrl(id: string): string {
  return `${API_BASE}/projects/${id}/export/fountain`;
}

export function getPdfUrl(id: string): string {
  return `${API_BASE}/projects/${id}/export/pdf`;
}

export function getStoryboardPdfUrl(id: string): string {
  return `${API_BASE}/projects/${id}/export/storyboard-pdf`;
}

export function getVideoUrl(id: string): string {
  return `${API_BASE}/projects/${id}/export/video`;
}

// Providers Info
export async function getProviders(): Promise<{
  tiers: Record<string, unknown>;
  video_providers: Record<string, unknown>;
}> {
  return fetchAPI('/providers');
}
