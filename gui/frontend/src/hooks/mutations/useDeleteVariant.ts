import { useMutation } from '@tanstack/react-query';

import { apiService } from '../../services/api';

/**
 * Mutation hook for deleting a variant file from standalone_speech.
 *
 * Features:
 * - Deletes the variant file from disk
 * - Returns success status
 */
export const useDeleteVariant = () => {
  return useMutation({
    mutationFn: async (filePath: string): Promise<{ success: boolean }> => {
      const response = await apiService.deleteVariant(filePath);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    onSuccess: (_, filePath) => {
      console.log('Variant deleted:', filePath);
    },

    onError: (error) => {
      console.error('Failed to delete variant:', error);
    },
  });
};
