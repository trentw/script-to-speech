import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { VoiceCastingSession } from '@/types/voice-casting';
import { handleApiError } from '@/utils/apiErrorHandler';

interface ClearVoiceRequest {
  sessionId: string;
  character: string;
  versionId: number;
}

interface ClearVoiceResponse {
  session: VoiceCastingSession;
  success: boolean;
}

/**
 * Clears voice assignment from a character while preserving metadata.
 *
 * This mutation calls the dedicated DELETE /voice endpoint which removes only
 * voice-related fields (provider, sts_id, provider_config) while preserving
 * all character metadata stored as YAML comments (casting notes, role, line counts).
 * The backend uses ruamel.yaml with careful comment preservation.
 *
 * @example
 * const clearVoice = useClearVoice();
 * clearVoice.mutate({
 *   sessionId: 'abc-123',
 *   character: 'ALICE',
 *   versionId: 1
 * });
 */
export function useClearVoice() {
  const queryClient = useQueryClient();

  return useMutation<ClearVoiceResponse, Error, ClearVoiceRequest>({
    mutationFn: async (data) => {
      // Call the dedicated clear voice endpoint which preserves metadata
      const response = await apiService.clearCharacterVoice(
        data.sessionId,
        data.character,
        data.versionId
      );

      if (response.error) {
        throw handleApiError(response);
      }

      return response.data!;
    },
    onSuccess: (data, variables) => {
      // Simply invalidate to trigger a refetch
      // This ensures the query runs its full transformation logic
      queryClient.invalidateQueries({
        queryKey: ['session', variables.sessionId],
      });

      // Also invalidate the sessions list to update counts/status
      queryClient.invalidateQueries({
        queryKey: ['voice-casting-sessions'],
      });
    },
  });
}
