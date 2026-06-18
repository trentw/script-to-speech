import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type {
  SilentClipsResponse,
  SilentClipsScanProgress,
} from '../../types/review';

/**
 * Hook for fetching silent clips for a project, with live scan progress.
 *
 * Features:
 * - Auto-fetches cached silent clips (populated by generation or a completed scan)
 * - refresh() starts a background scan; progress is polled and exposed as
 *   `scanProgress` / `isScanning`
 * - Also surfaces an in-flight scan started by an audio generation run, and
 *   pops results in automatically when any tracked scan completes
 *
 * @param projectName Project to read/scan (null disables the hook)
 * @param enabled When false, stops scan-progress polling (e.g. before voice
 *   casting is complete). Defaults to true.
 */
export const useSilentClips = (
  projectName: string | null,
  enabled: boolean = true
) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.silentClips(projectName || ''),
    queryFn: async (): Promise<SilentClipsResponse> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }

      const response = await apiService.getSilentClips(projectName);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    // Backend caches results, so reasonable stale time
    staleTime: 30 * 1000, // 30 seconds

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Refetch on window focus
    refetchOnWindowFocus: true,

    // Auto-fetch when project name is available
    enabled: !!projectName,

    // Retry with exponential backoff
    retry: (failureCount, error) => {
      // Don't retry 404s - project not found
      if (
        error.message?.includes('not found') ||
        error.message?.includes('404')
      ) {
        return false;
      }
      return failureCount < 2;
    },

    // Retry delay
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });

  // Poll scan progress. Polls slowly while idle so a scan started elsewhere
  // (e.g. an audio generation run) is detected, and fast while one is running.
  const progressQuery = useQuery({
    queryKey: queryKeys.silentClipsScan(projectName || ''),
    queryFn: async (): Promise<SilentClipsScanProgress> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }
      const response = await apiService.getSilentClipsScanProgress(projectName);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!projectName && enabled,
    staleTime: 0,
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 500 : 2000),
    refetchIntervalInBackground: false,
    retry: false,
  });

  // When a tracked scan transitions running -> completed, pop in fresh results.
  // When it fails, surface the error.
  const prevStatusRef = useRef<SilentClipsScanProgress['status'] | undefined>(
    undefined
  );
  const [scanError, setScanError] = useState<string | null>(null);

  useEffect(() => {
    const status = progressQuery.data?.status;
    const prev = prevStatusRef.current;
    prevStatusRef.current = status;

    if (prev === 'running' && status === 'completed') {
      setScanError(null);
      if (projectName) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.silentClips(projectName),
        });
      }
    } else if (prev === 'running' && status === 'failed') {
      setScanError(progressQuery.data?.error ?? 'Silence scan failed');
    }
  }, [
    progressQuery.data?.status,
    progressQuery.data?.error,
    projectName,
    queryClient,
  ]);

  // Start a background scan. Progress is reflected via the poll above.
  const refresh = useCallback(async () => {
    if (!projectName) return;

    setScanError(null);
    const response = await apiService.startSilentClipsScan(projectName);
    if (response.error) {
      setScanError(response.error);
      return;
    }
    // Seed the progress cache so the UI reflects "running" immediately and the
    // poll switches to its fast interval.
    if (response.data) {
      queryClient.setQueryData(
        queryKeys.silentClipsScan(projectName),
        response.data
      );
      prevStatusRef.current = response.data.status;
    }
  }, [projectName, queryClient]);

  const isScanning = progressQuery.data?.status === 'running';

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error || (scanError ? new Error(scanError) : null),
    refresh,
    isScanning,
    scanProgress: progressQuery.data?.progress ?? 0,
  };
};
