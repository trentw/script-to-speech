import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';

interface VoiceCastingSession {
  sessionId: string;
  screenplayName: string;
  status: 'in-progress' | 'completed';
  assignedCount: number;
  totalCount: number;
  lastUpdated: number;
}

export function useVoiceCastingSessions(limit = 5) {
  return useQuery({
    queryKey: ['voice-casting-sessions', limit],
    queryFn: async () => {
      const response = await apiService.getRecentSessions(limit);

      if (response.error) {
        console.error('Failed to fetch recent sessions:', response.error);
        return [];
      }

      // Transform backend response to match frontend format
      return (
        response.data?.sessions.map(
          (session) =>
            ({
              sessionId: session.session_id,
              screenplayName: session.screenplay_name,
              status: session.status,
              assignedCount: session.assigned_count,
              totalCount: session.total_count,
              lastUpdated: new Date(session.updated_at).getTime(),
            }) as VoiceCastingSession
        ) || []
      );
    },
    staleTime: 60000, // Consider fresh for 1 minute
  });
}
