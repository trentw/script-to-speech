import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import {
  type EntryPayload,
  textProcessorApi,
} from '../../services/textProcessorApi';

/**
 * Mutation hooks for the user's global default text processor config.
 * The global default seeds the config of future screenplays at parse time.
 */

interface UpdateGlobalDefaultParams {
  entries: EntryPayload[];
  basedOnDefaultSha256?: string | undefined;
  /** Content hash last read, for optimistic-lock conflict detection */
  baseFileHash?: string | null | undefined;
}

export const useUpdateTextProcessorGlobalDefault = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      entries,
      basedOnDefaultSha256,
      baseFileHash,
    }: UpdateGlobalDefaultParams) => {
      return await textProcessorApi.updateGlobalDefault(
        entries,
        basedOnDefaultSha256,
        baseFileHash
      );
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.textProcessorGlobalDefault, data);
    },
  });
};

export const useDeleteTextProcessorGlobalDefault = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (baseFileHash?: string | null) => {
      return await textProcessorApi.deleteGlobalDefault(baseFileHash);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.textProcessorGlobalDefault, data);
    },
  });
};
