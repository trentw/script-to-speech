import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type {
  AudiobookGenerationRequest,
  AudiobookTaskResponse,
} from '../../types';

/**
 * Mutation hook for creating new audiobook generation tasks
 *
 * Creates a new audiobook generation task and starts polling for progress.
 * Automatically invalidates the audiobook tasks list on success.
 */
export const useCreateAudiobookTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: AudiobookGenerationRequest
    ): Promise<AudiobookTaskResponse> => {
      const response = await apiService.createAudiobookTask(request);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    onSuccess: async (data) => {
      // Invalidate tasks list to show new task
      await queryClient.invalidateQueries({
        queryKey: queryKeys.audiobookTasks,
      });

      // Start polling for the new task by prefetching
      queryClient.prefetchQuery({
        queryKey: queryKeys.audiobookStatus(data.taskId),
        queryFn: async () => {
          const response = await apiService.getAudiobookStatus(data.taskId);
          if (response.error) throw new Error(response.error);
          return response.data!;
        },
      });
    },
    onError: (error) => {
      console.error('Audiobook generation task creation failed:', error);
    },
  });
};

/**
 * Mutation hook for cleaning up old audiobook tasks
 */
export const useCleanupAudiobookTasks = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (maxAgeHours: number = 24) => {
      const response = await apiService.cleanupAudiobookTasks(maxAgeHours);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    onSuccess: () => {
      // Invalidate tasks list after cleanup
      queryClient.invalidateQueries({ queryKey: queryKeys.audiobookTasks });
    },
  });
};
