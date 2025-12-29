import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { AudiobookGenerationProgress } from '../../types';

/**
 * Query hook for fetching audiobook generation task status with adaptive polling
 *
 * Uses faster polling (500ms) during active generation phase,
 * slower polling (2s) for other phases, and stops when complete/failed.
 */
export const useAudiobookStatus = (taskId: string | null) => {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: queryKeys.audiobookStatus(taskId || ''),
    queryFn: async (): Promise<AudiobookGenerationProgress> => {
      if (!taskId) throw new Error('No task ID provided');

      const response = await apiService.getAudiobookStatus(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;

      // Stop polling when complete or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        // Invalidate review queries so fresh data is fetched when user visits review page
        if (data?.status === 'completed') {
          queryClient.invalidateQueries({
            queryKey: ['review', 'cache-misses'],
          });
          queryClient.invalidateQueries({
            queryKey: ['review', 'silent-clips'],
          });
        }

        // Clean up query after some time
        setTimeout(
          () => {
            queryClient.removeQueries({
              queryKey: queryKeys.audiobookStatus(taskId || ''),
            });
          },
          1000 * 60 * 10 // Remove after 10 minutes
        );
        return false;
      }

      // Fast polling during active generation
      if (data?.phase === 'generating') {
        return 500; // 500ms during generation
      }

      // Slower polling for other phases
      return 2000; // 2s for other phases
    },
    refetchIntervalInBackground: false, // Pause when tab hidden
    staleTime: 0, // Always refetch for real-time updates
    gcTime: 1000 * 60 * 15, // Keep in cache for 15 minutes
  });
};

/**
 * Query hook for fetching audiobook generation result
 * Only enabled when task is completed
 */
export const useAudiobookResult = (
  taskId: string | null,
  isCompleted: boolean
) => {
  return useQuery({
    queryKey: queryKeys.audiobookResult(taskId || ''),
    queryFn: async () => {
      if (!taskId) throw new Error('No task ID provided');

      const response = await apiService.getAudiobookResult(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!taskId && isCompleted,
    staleTime: Infinity, // Result won't change once fetched
    gcTime: 1000 * 60 * 30, // Keep in cache for 30 minutes
  });
};

/**
 * Query hook for fetching all audiobook generation tasks
 */
export const useAllAudiobookTasks = () => {
  return useQuery({
    queryKey: queryKeys.audiobookTasks,
    queryFn: async (): Promise<AudiobookGenerationProgress[]> => {
      const response = await apiService.getAllAudiobookTasks();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    staleTime: 1000 * 30, // Consider stale after 30 seconds
    gcTime: 1000 * 60 * 5, // Keep in cache for 5 minutes
  });
};
