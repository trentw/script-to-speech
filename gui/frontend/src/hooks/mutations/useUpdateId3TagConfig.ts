import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { projectApi } from '../../services/projectApi';
import type { Id3TagConfig, Id3TagConfigUpdate } from '../../types/project';

interface UpdateId3TagConfigParams {
  inputPath: string;
  update: Id3TagConfigUpdate;
}

/**
 * Mutation hook for updating ID3 tag configuration with optimistic updates
 */
export const useUpdateId3TagConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ inputPath, update }: UpdateId3TagConfigParams) => {
      return await projectApi.updateId3TagConfig(inputPath, update);
    },

    onMutate: async ({ inputPath, update }) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({
        queryKey: queryKeys.id3TagConfig(inputPath),
      });

      // Snapshot previous value
      const previousConfig = queryClient.getQueryData<Id3TagConfig | null>(
        queryKeys.id3TagConfig(inputPath)
      );

      // Optimistically update
      if (previousConfig) {
        queryClient.setQueryData<Id3TagConfig>(
          queryKeys.id3TagConfig(inputPath),
          {
            ...previousConfig,
            ...(update.title !== undefined && { title: update.title }),
            ...(update.screenplayAuthor !== undefined && {
              screenplayAuthor: update.screenplayAuthor,
            }),
            ...(update.date !== undefined && { date: update.date }),
          }
        );
      }

      return { previousConfig };
    },

    onError: (_error, { inputPath }, context) => {
      // Rollback to snapshot
      if (context?.previousConfig) {
        queryClient.setQueryData(
          queryKeys.id3TagConfig(inputPath),
          context.previousConfig
        );
      }
    },

    onSettled: (_data, _error, { inputPath }) => {
      // Invalidate to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: queryKeys.id3TagConfig(inputPath),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.projectStatus(inputPath),
      });
    },
  });
};
