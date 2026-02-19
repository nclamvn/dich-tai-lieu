/**
 * Hook for managing screenplay projects list
 */

import { useState, useEffect, useCallback } from 'react';
import { ScreenplayProject } from '@/lib/screenplay/types';
import { listProjects, deleteProject } from '@/lib/screenplay/api';

interface UseProjectsOptions {
  pageSize?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { pageSize = 10, autoRefresh = false, refreshInterval = 30000 } = options;

  const [projects, setProjects] = useState<ScreenplayProject[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listProjects(page, pageSize);
      setProjects(response.projects);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (!autoRefresh) return;

    const hasInProgress = projects.some((p) =>
      ['analyzing', 'writing', 'visualizing', 'rendering'].includes(p.status)
    );

    if (!hasInProgress) return;

    const interval = setInterval(fetchProjects, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, projects, fetchProjects]);

  const remove = useCallback(async (id: string) => {
    try {
      await deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
      throw err;
    }
  }, []);

  return {
    projects,
    total,
    page,
    pageSize,
    loading,
    error,
    setPage,
    refresh: fetchProjects,
    remove,
  };
}
