import { useQuery } from '@tanstack/react-query';
import { useCallback, useRef } from 'react';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ChunkInventoryResponse } from '../../types/chunks';

/**
 * Hook for fetching the full chunk inventory for a project.
 *
 * Features:
 * - Auto-fetches on mount when enabled (backend caches the inventory,
 *   so a modest staleTime is fine; mutations invalidate the query)
 * - refresh() forces a server-side recompute (refresh=true) and refetches
 * - Refetch on window focus for CLI/GUI interop
 *
 * @param projectName - The project name to fetch the inventory for
 * @param enabled - Whether to auto-fetch. Set to false to disable
 *                  auto-fetching (e.g., when voice casting is incomplete).
 *                  Default: true
 */
export const useChunkInventory = (
  projectName: string | null,
  enabled: boolean = true
) => {
  // When set, the next fetch bypasses the server-side inventory cache
  const forceRefreshRef = useRef(false);

  const query = useQuery({
    queryKey: queryKeys.chunkInventory(projectName || ''),
    queryFn: async (): Promise<ChunkInventoryResponse> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }

      const forceRefresh = forceRefreshRef.current;
      forceRefreshRef.current = false;

      const response = await apiService.getChunkInventory(
        projectName,
        forceRefresh
      );
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    // Backend caches the inventory and mutations invalidate this query,
    // so a modest stale time avoids redundant recomputes
    staleTime: 30 * 1000, // 30 seconds

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Refetch on window focus (critical for CLI/GUI interop)
    refetchOnWindowFocus: true,

    // Only fetch if we have a project name AND fetching is enabled
    enabled: !!projectName && enabled,

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

  const { refetch } = query;

  // Manual refresh - forces the backend to recompute the inventory
  const refresh = useCallback(() => {
    forceRefreshRef.current = true;
    return refetch();
  }, [refetch]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isRefetching: query.isRefetching,
    error: query.error,
    refresh,
    refetch: query.refetch,
  };
};
