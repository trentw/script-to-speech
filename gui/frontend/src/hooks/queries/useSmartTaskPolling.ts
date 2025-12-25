import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { TaskStatusResponse } from '../../types';

/**
 * Smart task polling hook that only polls when there are active tasks
 * Eliminates unnecessary polling when all tasks are completed/failed
 * Uses conditional refetchInterval based on task status
 */
export const useSmartTaskPolling = () => {
  return useQuery({
    queryKey: queryKeys.allTasks,
    queryFn: async (): Promise<TaskStatusResponse[]> => {
      const response = await apiService.getAllTasks();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    // Smart polling: only poll when there are active tasks
    refetchInterval: (query) => {
      const tasks = query.state.data;
      if (!tasks || tasks.length === 0) {
        return false; // No tasks, no need to poll
      }

      // Check if any tasks are still active (not completed or failed)
      const hasActiveTasks = tasks.some(
        (task) => task.status === 'processing' || task.status === 'pending'
      );

      // Only poll if there are active tasks
      return hasActiveTasks ? 2000 : false;
    },
    refetchIntervalInBackground: false, // Pause when tab hidden
    staleTime: 1000, // 1 second - keep data fresh
    gcTime: 1000 * 60 * 10, // Keep in cache for 10 minutes
  });
};

/**
 * Hook for checking if there are any active tasks
 * Useful for UI indicators and conditional rendering
 */
export const useHasActiveTasks = () => {
  const { data: tasks } = useSmartTaskPolling();

  const hasActiveTasks =
    tasks?.some(
      (task) => task.status === 'processing' || task.status === 'pending'
    ) ?? false;

  return {
    hasActiveTasks,
    activeTasks:
      tasks?.filter(
        (task) => task.status === 'processing' || task.status === 'pending'
      ) ?? [],
  };
};
