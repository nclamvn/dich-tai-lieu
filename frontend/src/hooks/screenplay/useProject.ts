/**
 * Hook for managing a single screenplay project
 */

import { useState, useEffect, useCallback } from 'react';
import { ScreenplayProject, UpdateProjectInput } from '@/lib/screenplay/types';
import {
  getProject,
  updateProject,
  startAnalysis,
  startGeneration,
  startVisualization,
  startVideoRendering,
} from '@/lib/screenplay/api';

interface UseProjectOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useProject(
  id: string | null,
  options: UseProjectOptions = {}
) {
  const { autoRefresh = true, refreshInterval = 3000 } = options;

  const [project, setProject] = useState<ScreenplayProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isProcessing =
    project?.status != null &&
    ['analyzing', 'writing', 'visualizing', 'rendering'].includes(project.status);

  const fetchProject = useCallback(async () => {
    if (!id) {
      setProject(null);
      setLoading(false);
      return;
    }

    try {
      setError(null);
      const data = await getProject(id);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    fetchProject();
  }, [fetchProject]);

  useEffect(() => {
    if (!autoRefresh || !isProcessing) return;

    const interval = setInterval(fetchProject, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, isProcessing, fetchProject]);

  const update = useCallback(
    async (input: UpdateProjectInput) => {
      if (!id) return;
      try {
        const updated = await updateProject(id, input);
        setProject(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update project');
        throw err;
      }
    },
    [id]
  );

  const analyze = useCallback(async () => {
    if (!id) return;
    try {
      await startAnalysis(id);
      await fetchProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
      throw err;
    }
  }, [id, fetchProject]);

  const generate = useCallback(async () => {
    if (!id) return;
    try {
      await startGeneration(id);
      await fetchProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      throw err;
    }
  }, [id, fetchProject]);

  const visualize = useCallback(async () => {
    if (!id) return;
    try {
      await startVisualization(id);
      await fetchProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start visualization');
      throw err;
    }
  }, [id, fetchProject]);

  const renderVideo = useCallback(async () => {
    if (!id || !project) return;
    try {
      await startVideoRendering(id, project.video_provider);
      await fetchProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start video rendering');
      throw err;
    }
  }, [id, project, fetchProject]);

  return {
    project,
    loading,
    error,
    refresh: fetchProject,
    update,
    analyze,
    generate,
    visualize,
    renderVideo,
    isProcessing: !!isProcessing,
  };
}
