import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { projectApi } from '../../services/projectApi';
import type { ProjectStatus } from '../../types/project';

/**
 * Hook for fetching project status with intelligent caching for CLI/GUI interoperability
 *
 * Features:
 * - 5 second stale time for fresh data
 * - 5 minute cache time to avoid unnecessary refetching
 * - Refetch on window focus (critical for CLI/GUI interop)
 * - Smart retry logic (don't retry 404s)
 * - Manual invalidation support
 */
export const useProjectStatus = (inputPath: string | undefined) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.projectStatus(inputPath || ''),
    queryFn: async (): Promise<ProjectStatus | null> => {
      if (!inputPath) return null;

      return await projectApi.getProjectStatus(inputPath);
    },

    // Keep data fresh for 5 seconds
    staleTime: 5000,

    // Keep in cache for 5 minutes to avoid refetching
    gcTime: 5 * 60 * 1000,

    // Critical for CLI/GUI interoperability!
    refetchOnWindowFocus: true,

    // Only fetch if we have a path
    enabled: !!inputPath,

    // Retry with exponential backoff
    retry: (failureCount, error) => {
      // Don't retry 404s - project not found
      if (
        error.message?.includes('not found') ||
        error.message?.includes('404')
      ) {
        return false;
      }
      return failureCount < 3;
    },

    // Retry delay with exponential backoff
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Manual invalidation after operations
  const invalidate = () => {
    return queryClient.invalidateQueries({
      queryKey: queryKeys.projectStatus(inputPath || ''),
    });
  };

  return {
    status: query.data,
    isLoading: query.isLoading,
    error: query.error,
    invalidate, // Replaces 'rescan' - used to refresh after operations
    isStale: query.isStale,
    isFetching: query.isFetching,
  };
};
