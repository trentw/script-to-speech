import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ReparseRequest, ReparseResponse } from '../../types';

/**
 * Mutation hook for re-parsing a screenplay with header/footer removal options
 *
 * Features:
 * - Re-parses screenplay with user-specified patterns to remove
 * - Supports both line-based removal and global replace modes
 * - Invalidates project status cache after success
 * - Prevents concurrent parses via backend locking
 */
export const useReparseScreenplay = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ReparseRequest): Promise<ReparseResponse> => {
      const response = await apiService.reparseScreenplay(request);

      if (response.error) {
        throw new Error(response.error);
      }

      if (!response.data) {
        throw new Error('No reparse result returned');
      }

      return response.data;
    },

    onSuccess: (_data, variables) => {
      // Invalidate project status to reflect new parse results
      queryClient.invalidateQueries({
        queryKey: queryKeys.projectStatus(variables.inputPath),
      });

      console.log('Screenplay re-parsed successfully');
    },

    onError: (error) => {
      console.error('Screenplay re-parse failed:', error);
    },
  });
};
