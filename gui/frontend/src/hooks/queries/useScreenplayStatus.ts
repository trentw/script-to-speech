import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import type { TaskStatusResponse } from '@/types';

export function useScreenplayStatus(taskId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['screenplay-status', taskId],
    queryFn: async () => {
      if (!taskId) throw new Error('No task ID provided');
      
      const response = await apiService.getScreenplayTaskStatus(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data as TaskStatusResponse;
    },
    enabled: enabled && !!taskId,
    // Poll every 2 seconds while task is pending or processing
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === 'pending' || data.status === 'processing')) {
        return 2000;
      }
      return false;
    },
  });
}