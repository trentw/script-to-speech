import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { projectApi } from '../../services/projectApi';
import type { ProjectMeta } from '../../types/project';

/**
 * Hook for discovering existing projects in the workspace
 *
 * Features:
 * - 30 second stale time for project discovery (longer than status)
 * - 5 minute cache time to avoid expensive filesystem scans
 * - Refetch on window focus for CLI/GUI interop
 * - Sorted by last modified date (most recent first)
 */
export const useDiscoverProjects = (options?: { limit?: number }) => {
  return useQuery({
    queryKey: queryKeys.projectsDiscover(options?.limit),
    queryFn: async (): Promise<ProjectMeta[]> => {
      return await projectApi.discoverProjects(options?.limit);
    },

    // 30 seconds stale time for project discovery (filesystem scanning is expensive)
    staleTime: 30000,

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Refetch on window focus to detect CLI changes
    refetchOnWindowFocus: true,

    // Retry on failure with exponential backoff
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};
