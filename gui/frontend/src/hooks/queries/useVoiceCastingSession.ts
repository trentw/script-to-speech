import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { VoiceCastingSession } from '@/types/voice-casting';

export function useVoiceCastingSession(sessionId: string | undefined) {
  return useQuery<VoiceCastingSession, Error>({
    queryKey: ['session', sessionId],
    queryFn: async () => {
      if (!sessionId) {
        throw new Error('Session ID is required');
      }

      const response = await apiService.getVoiceCastingSession(sessionId);

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    },
    enabled: !!sessionId,
    staleTime: 30 * 1000, // Consider data fresh for 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}
