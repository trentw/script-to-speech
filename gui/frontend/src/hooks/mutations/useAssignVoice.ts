import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type {
  VoiceAssignment,
  VoiceCastingSession,
} from '@/types/voice-casting';
import { handleApiError } from '@/utils/apiErrorHandler';

interface AssignVoiceRequest {
  sessionId: string;
  character: string;
  assignment: VoiceAssignment;
  versionId: number;
}

interface AssignVoiceResponse {
  session: VoiceCastingSession;
  success: boolean;
}

/**
 * Assigns a voice from the library to a character.
 *
 * This mutation only modifies voice-related fields (provider, sts_id, provider_config)
 * and preserves all character metadata stored as YAML comments (casting notes, role, etc.).
 *
 * @example
 * const assignVoice = useAssignVoice();
 * assignVoice.mutate({
 *   sessionId: 'abc-123',
 *   character: 'ALICE',
 *   assignment: { provider: 'openai', sts_id: 'alloy' },
 *   versionId: 1
 * });
 */
export function useAssignVoice() {
  const queryClient = useQueryClient();

  return useMutation<AssignVoiceResponse, Error, AssignVoiceRequest>({
    mutationFn: async (data) => {
      const response = await apiService.updateCharacterAssignment(
        data.sessionId,
        data.character,
        data.assignment,
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
