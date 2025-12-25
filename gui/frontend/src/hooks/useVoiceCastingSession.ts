import { useState } from 'react';

import { apiService } from '@/services/api';

export function useVoiceCastingSession() {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSessionFromTask = async (taskId: string) => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await apiService.createSessionFromTask(taskId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data.session_id;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create session';
      setError(errorMessage);
      throw err;
    } finally {
      setIsCreating(false);
    }
  };

  return {
    createSessionFromTask,
    isCreating,
    error,
  };
}
