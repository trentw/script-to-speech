import { useCallback, useState } from 'react';

import { apiService } from '../services/api';
import type { TaskStatusResponse } from '../types';

interface UseTaskPollingReturn {
  generationTasks: TaskStatusResponse[];
  setGenerationTasks: React.Dispatch<
    React.SetStateAction<TaskStatusResponse[]>
  >;
  pollTaskStatus: (taskId: string) => void;
}

export const useTaskPolling = (): UseTaskPollingReturn => {
  const [generationTasks, setGenerationTasks] = useState<TaskStatusResponse[]>(
    []
  );

  const pollTaskStatus = useCallback((taskId: string) => {
    const pollInterval = setInterval(async () => {
      const response = await apiService.getTaskStatus(taskId);

      if (response.data) {
        const task = response.data;

        setGenerationTasks((prev) => [
          ...prev.filter((t) => t.task_id !== taskId),
          task,
        ]);

        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollInterval);
        }
      } else {
        clearInterval(pollInterval);
        // Could add error handling here if needed
      }
    }, 1000);

    // Return cleanup function for the interval
    return () => clearInterval(pollInterval);
  }, []);

  return { generationTasks, setGenerationTasks, pollTaskStatus };
};
