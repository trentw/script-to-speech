import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { AudiobookGenerationProgress } from '../../types';

/**
 * Mutation hook for cancelling a running audiobook generation task.
 *
 * Cancellation is cooperative: completed clips are kept and the run can be
 * resumed by generating again. The backend may still report 'processing' until
 * the worker observes the signal, so we seed the status cache with the returned
 * progress to reflect "stopping" immediately; the existing status poll then
 * transitions it to 'cancelled'.
 */
export const useCancelAudiobookTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      taskId: string
    ): Promise<AudiobookGenerationProgress> => {
      const response = await apiService.cancelAudiobookTask(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.audiobookStatus(data.taskId), data);
    },
    onError: (error) => {
      console.error('Audiobook generation cancellation failed:', error);
    },
  });
};
