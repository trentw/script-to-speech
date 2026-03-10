import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { VoiceEntry } from '../../types';
import type {
  LLMRunImportResponse,
  VoiceUpdateRequest,
} from '../../types/voice-editor';

/**
 * Mutation hook for updating a voice's properties/description/tags.
 * Invalidates voiceLibrary and voiceDetails queries on success.
 */
export const useUpdateVoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      provider,
      stsId,
      updates,
    }: {
      provider: string;
      stsId: string;
      updates: VoiceUpdateRequest;
    }): Promise<VoiceEntry> => {
      const response = await apiService.updateVoice(provider, stsId, updates);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },

    onSuccess: (_, variables) => {
      // Invalidate queries so fresh data is fetched from YAML
      queryClient.invalidateQueries({
        queryKey: queryKeys.voiceLibrary(variables.provider),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.voiceDetails(variables.provider, variables.stsId),
      });
    },
  });
};

/**
 * Mutation hook for importing an LLM run directory.
 */
export const useImportLLMRun = () => {
  return useMutation({
    mutationFn: async (runDir: string): Promise<LLMRunImportResponse> => {
      const response = await apiService.importLLMRun(runDir);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
  });
};
