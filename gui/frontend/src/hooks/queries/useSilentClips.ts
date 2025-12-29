import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { SilentClipsResponse } from '../../types/review';

/**
 * Hook for fetching silent clips for a project.
 *
 * Features:
 * - Auto-fetches on mount (backend returns cached data from generation or scans if needed)
 * - Refetches on window focus
 * - Manual refresh via refresh() forces backend rescan (bypasses backend cache)
 */
export const useSilentClips = (projectName: string | null) => {
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const query = useQuery({
    queryKey: queryKeys.silentClips(projectName || ''),
    queryFn: async (): Promise<SilentClipsResponse> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }

      // Normal fetches use backend cache (fast)
      const response = await apiService.getSilentClips(projectName, false);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    // Backend caches results, so reasonable stale time
    staleTime: 30 * 1000, // 30 seconds

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Refetch on window focus (it's fast now - backend caches)
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

  // Manual refresh - forces backend rescan (bypasses backend cache)
  const refresh = useCallback(async () => {
    if (!projectName) return;

    setIsRefreshing(true);
    try {
      // Call API with refresh=true to force backend rescan
      const response = await apiService.getSilentClips(projectName, true);
      if (response.error) {
        throw new Error(response.error);
      }

      // Update TanStack Query cache with fresh data
      queryClient.setQueryData(
        queryKeys.silentClips(projectName),
        response.data
      );
    } finally {
      setIsRefreshing(false);
    }
  }, [projectName, queryClient]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching || isRefreshing,
    error: query.error,
    refresh,
  };
};
