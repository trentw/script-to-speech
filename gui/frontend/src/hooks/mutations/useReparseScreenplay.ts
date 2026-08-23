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
      // Re-parsing can change chunk text, ordering, and PDF positions. Mark all
      // derived client views stale alongside the backend's cache invalidation.
      queryClient.invalidateQueries({
        queryKey: queryKeys.projectStatus(variables.inputPath),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chunkInventory(variables.screenplayName),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.pdfAnchors(variables.screenplayName),
      });

      console.log('Screenplay re-parsed successfully');
    },

    onError: (error) => {
      console.error('Screenplay re-parse failed:', error);
    },
  });
};
