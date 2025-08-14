import { useMutation, useQueryClient } from '@tanstack/react-query';
import { produce } from 'immer';

import { apiService } from '@/services/api';
import type { VoiceAssignment, VoiceCastingSession } from '@/types/voice-casting';

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
        // Handle version conflicts (409 status) specifically
        if (response.error.includes('409') || response.error.includes('version')) {
          throw new Error('The session has been updated by another user. Please refresh and try again.');
        }
        throw new Error(response.error);
      }

      return response.data!;
    },
    onMutate: async (variables) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ['session', variables.sessionId]
      });

      // Snapshot the previous value
      const previousSession = queryClient.getQueryData<VoiceCastingSession>([
        'session',
        variables.sessionId
      ]);

      // Optimistically update the cache
      if (previousSession) {
        const optimisticSession = produce(previousSession, (draft) => {
          // Update version for optimistic locking
          if (draft.yaml_version_id !== undefined) {
            draft.yaml_version_id = variables.versionId + 1;
          }
          
          // We don't directly update assignments here since they're parsed from YAML
          // The backend will handle updating the YAML content with the new assignment
          draft.updated_at = new Date().toISOString();
        });

        queryClient.setQueryData(
          ['session', variables.sessionId],
          optimisticSession
        );
      }

      // Return context with previous value for rollback
      return { previousSession };
    },
    onError: (error, variables, context) => {
      // Rollback optimistic update on error
      if (context?.previousSession) {
        queryClient.setQueryData(
          ['session', variables.sessionId],
          context.previousSession
        );
      }
    },
    onSuccess: (data, variables) => {
      // Update the session cache with the server response
      queryClient.setQueryData(
        ['session', variables.sessionId],
        data.session
      );

      // Invalidate related queries to ensure consistency
      queryClient.invalidateQueries({
        queryKey: ['session', variables.sessionId]
      });
    },
  });
}