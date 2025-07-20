import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';

export function useScreenplayResult(taskId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['screenplay-result', taskId],
    queryFn: async () => {
      if (!taskId) throw new Error('No task ID provided');
      
      const response = await apiService.getScreenplayResult(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
    enabled: enabled && !!taskId,
    staleTime: Infinity, // Results don't change once generated
  });
}