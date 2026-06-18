import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { AudiobookGenerationProgress } from '../../types';

/**
 * Query hook for the most-recent audiobook generation task of a project.
 *
 * The backend keeps the authoritative task registry, so this lets the UI
 * re-adopt a running session after navigating away (resume), drive the global
 * progress indicator, and detect completion for the toast — all computed from
 * the backend rather than GUI-only state. Returns null when no generation has
 * run for the project.
 *
 * Adaptive polling: fast while generating, slower for other running phases,
 * slow when idle/terminal (so a freshly-started run is still picked up). Polling
 * is disabled entirely when there is no project.
 */
export const useActiveAudiobookTask = (
  projectName: string | null,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: queryKeys.audiobookActive(projectName || ''),
    queryFn: async (): Promise<AudiobookGenerationProgress | null> => {
      if (!projectName) throw new Error('No project name provided');

      const response = await apiService.getActiveAudiobookTask(projectName);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data ?? null;
    },
    enabled: !!projectName && enabled,
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'processing') {
        return data.phase === 'generating' ? 1000 : 2000;
      }
      if (data?.status === 'pending') {
        return 2000;
      }
      // idle / completed / failed / cancelled: keep a slow poll so a newly
      // started run is still discovered.
      return 5000;
    },
    refetchIntervalInBackground: false, // Pause when tab hidden
    retry: false,
  });
};
