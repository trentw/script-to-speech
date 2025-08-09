import { useMemo } from 'react';

import { useVoiceCasting } from '@/stores/appStore';

export function useVoiceCastingSessions(limit = 5) {
  const { getRecentSessions } = useVoiceCasting();

  return useMemo(() => {
    const sessions = getRecentSessions(limit);

    // Map sessions to include computed properties for display
    return sessions.map((session) => {
      const totalCharacters = session.screenplayData?.characters.size || 0;
      const assignedCharacters = Array.from(
        session.assignments.entries()
      ).filter(
        ([_, assignment]) =>
          assignment.provider &&
          (assignment.sts_id || assignment.provider_config)
      ).length;

      return {
        sessionId: session.sessionId,
        screenplayName: session.screenplayName,
        status:
          assignedCharacters === totalCharacters && totalCharacters > 0
            ? 'completed'
            : 'in-progress',
        assignedCount: assignedCharacters,
        totalCount: totalCharacters,
        lastUpdated: session.lastUpdated,
      };
    });
  }, [getRecentSessions, limit]);
}
