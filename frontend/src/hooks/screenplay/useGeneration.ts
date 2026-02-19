/**
 * Hook for tracking generation progress
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { GenerationProgress } from '@/lib/screenplay/types';
import { getProgress } from '@/lib/screenplay/api';

interface UseGenerationOptions {
  pollInterval?: number;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function useGeneration(
  projectId: string | null,
  options: UseGenerationOptions = {}
) {
  const { pollInterval = 2000, onComplete, onError } = options;

  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [isActive, setIsActive] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    if (!projectId) return;

    try {
      const data = await getProgress(projectId);
      setProgress(data);

      if (data.status === 'completed') {
        setIsActive(false);
        onComplete?.();
      } else if (data.status === 'failed') {
        setIsActive(false);
        onError?.(data.message || 'Generation failed');
      }
    } catch (err) {
      console.error('Progress poll error:', err);
    }
  }, [projectId, onComplete, onError]);

  const start = useCallback(() => {
    if (!projectId) return;
    setIsActive(true);
    poll();
  }, [projectId, poll]);

  const stop = useCallback(() => {
    setIsActive(false);
  }, []);

  useEffect(() => {
    if (!isActive || !projectId) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(poll, pollInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, projectId, pollInterval, poll]);

  return { progress, isActive, start, stop };
}
