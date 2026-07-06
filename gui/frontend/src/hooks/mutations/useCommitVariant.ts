import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type {
  CommitVariantRequest,
  CommitVariantResponse,
} from '../../types/review';

/**
 * Mutation hook for committing a variant to the project cache.
 *
 * Features:
 * - Copies variant from standalone_speech to project cache
 * - Returns success status and target path
 * - Does NOT auto-invalidate cache misses (user can see committed state)
 * - DOES invalidate the chunk inventory so badges/statuses refresh
 */
export const useCommitVariant = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: CommitVariantRequest
    ): Promise<CommitVariantResponse> => {
      const response = await apiService.commitVariant(request);
      if (response.error) {
        throw new Error(response.error);
      }
      // Check the success field from the response
      if (!response.data?.success) {
        throw new Error(response.data?.message || 'Failed to commit variant');
      }
      return response.data;
    },

    onSuccess: (_, variables) => {
      // Don't auto-invalidate cache misses - let user manually refresh
      // This allows them to see the "committed" visual state and continue
      // working through the list without items disappearing immediately

      // The chunk inventory's statuses/badges (cached, user-modified) change
      // on commit, so refresh it
      queryClient.invalidateQueries({
        queryKey: queryKeys.chunkInventory(variables.projectName),
      });

      console.log(
        'Variant committed:',
        variables.sourcePath,
        '->',
        variables.targetCacheFilename
      );
    },

    onError: (error) => {
      console.error('Failed to commit variant:', error);
    },
  });
};
