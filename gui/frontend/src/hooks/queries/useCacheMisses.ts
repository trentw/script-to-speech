import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { CacheMissesResponse } from '../../types/review';

/**
 * Hook for fetching cache misses for a project.
 *
 * Features:
 * - Auto-fetches on mount (fast operation)
 * - Fresh data on each request (staleTime: 0)
 * - Refetch on window focus for CLI/GUI interop
 * - Manual invalidation support
 */
export const useCacheMisses = (projectName: string | null) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.cacheMisses(projectName || ''),
    queryFn: async (): Promise<CacheMissesResponse> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }

      const response = await apiService.getCacheMisses(projectName);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    // Always refetch for fresh data (cache misses can change at any time)
    staleTime: 0,

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Refetch on window focus (critical for CLI/GUI interop)
    refetchOnWindowFocus: true,

    // Only fetch if we have a project name
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

  // Manual refresh
  const refresh = () => {
    return queryClient.invalidateQueries({
      queryKey: queryKeys.cacheMisses(projectName || ''),
    });
  };

  return {
    data: query.data,
    isLoading: query.isLoading,
    isRefetching: query.isRefetching,
    error: query.error,
    refresh,
    refetch: query.refetch,
  };
};
