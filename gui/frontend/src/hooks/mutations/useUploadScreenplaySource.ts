import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { VoiceCastingSession } from '@/types/voice-casting';

interface UploadScreenplaySourceRequest {
  sessionId: string;
  file: File;
}

export function useUploadScreenplaySource() {
  const queryClient = useQueryClient();

  return useMutation<VoiceCastingSession, Error, UploadScreenplaySourceRequest>(
    {
      mutationFn: async (data) => {
        const response = await apiService.uploadScreenplaySource(
          data.sessionId,
          data.file
        );

        if (response.error) {
          throw new Error(response.error);
        }

        return response.data!;
      },
      onSuccess: (data) => {
        // Update the session in the cache
        queryClient.setQueryData(
          ['voice-casting-session', data.session_id],
          data
        );
      },
    }
  );
}
