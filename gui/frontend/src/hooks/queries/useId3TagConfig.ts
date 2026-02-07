import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { projectApi } from '../../services/projectApi';
import type { Id3TagConfig } from '../../types/project';

/**
 * Hook for fetching ID3 tag configuration with CLI/GUI interoperability
 *
 * Features:
 * - 5 second stale time for fresh data
 * - 5 minute cache time to avoid unnecessary refetching
 * - Refetch on window focus (critical for CLI/GUI interop — user may edit YAML manually)
 */
export const useId3TagConfig = (inputPath: string | undefined) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.id3TagConfig(inputPath || ''),
    queryFn: async (): Promise<Id3TagConfig | null> => {
      if (!inputPath) return null;

      return await projectApi.getId3TagConfig(inputPath);
    },

    staleTime: 5000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    enabled: !!inputPath,

    retry: (failureCount, error) => {
      if (
        error.message?.includes('not found') ||
        error.message?.includes('404')
      ) {
        return false;
      }
      return failureCount < 3;
    },

    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  const invalidate = () => {
    return queryClient.invalidateQueries({
      queryKey: queryKeys.id3TagConfig(inputPath || ''),
    });
  };

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
    invalidate,
  };
};
