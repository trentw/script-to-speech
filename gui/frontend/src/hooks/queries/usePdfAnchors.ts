import { useQuery } from '@tanstack/react-query';
import { useCallback, useRef } from 'react';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ChunkAnchorsResponse } from '../../types/pdfAnchors';

/**
 * Hook for fetching chunk-to-PDF anchors for the overlay view.
 *
 * Mirrors useChunkInventory: the backend caches anchors and invalidates them
 * on re-parse / text-processor config changes, so a modest staleTime is fine.
 * refresh() forces a server-side recompute. The first compute of a large PDF
 * takes several seconds (pdfplumber word extraction), so callers should show a
 * loading state and only enable this when the PDF lens is actually open.
 *
 * @param projectName - The project name
 * @param enabled - Whether to auto-fetch (e.g., only when the PDF lens is
 *                  open and the project has a PDF). Default: true
 */
export const usePdfAnchors = (
  projectName: string | null,
  enabled: boolean = true
) => {
  const forceRefreshRef = useRef(false);

  const query = useQuery({
    queryKey: queryKeys.pdfAnchors(projectName || ''),
    queryFn: async (): Promise<ChunkAnchorsResponse> => {
      if (!projectName) {
        throw new Error('No project name provided');
      }

      const forceRefresh = forceRefreshRef.current;
      forceRefreshRef.current = false;

      const response = await apiService.getPdfAnchors(
        projectName,
        forceRefresh
      );
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    enabled: !!projectName && enabled,

    retry: (failureCount, error) => {
      // Don't retry 404s - project or PDF not found
      if (
        error.message?.includes('not found') ||
        error.message?.includes('No source PDF') ||
        error.message?.includes('404')
      ) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });

  const { refetch } = query;

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
