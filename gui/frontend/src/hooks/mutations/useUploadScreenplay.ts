import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import type { TaskResponse } from '@/types';

interface UploadScreenplayParams {
  file: File;
  textOnly?: boolean;
}

export function useUploadScreenplay() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file, textOnly = false }: UploadScreenplayParams) => {
      const response = await apiService.uploadScreenplay(file, textOnly);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data as TaskResponse;
    },
    onSuccess: () => {
      // Invalidate screenplay tasks query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['screenplay-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['recent-screenplays'] });
    },
  });
}