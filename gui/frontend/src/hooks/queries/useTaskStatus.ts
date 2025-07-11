import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { queryKeys } from '../../lib/queryKeys'
import type { TaskStatusResponse } from '../../types'

/**
 * Query hook for fetching task status with intelligent polling
 * Uses exponential backoff and stops polling when task is complete
 */
export const useTaskStatus = (taskId: string) => {
  const queryClient = useQueryClient()
  
  return useQuery({
    queryKey: queryKeys.taskStatus(taskId),
    queryFn: async (): Promise<TaskStatusResponse> => {
      const response = await apiService.getTaskStatus(taskId)
      if (response.error) {
        throw new Error(response.error)
      }
      return response.data!
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') {
        // Clean up completed tasks to prevent memory bloat
        setTimeout(() => {
          queryClient.removeQueries({
            queryKey: queryKeys.taskStatus(taskId),
          })
        }, 1000 * 60 * 5) // Remove after 5 minutes
        
        return false // Stop polling
      }
      
      // Exponential backoff for long-running tasks
      const attemptIndex = query.state.fetchFailureCount || 0
      return Math.min(2000 * Math.pow(2, attemptIndex), 15000) // Max 15 seconds
    },
    refetchIntervalInBackground: false, // Pause when tab hidden
    staleTime: 0, // Always refetch for real-time updates
    gcTime: 1000 * 60 * 10, // Keep in cache for 10 minutes
  })
}

/**
 * Query hook for fetching all tasks
 */
export const useAllTasks = () => {
  return useQuery({
    queryKey: queryKeys.allTasks,
    queryFn: async (): Promise<TaskStatusResponse[]> => {
      const response = await apiService.getAllTasks()
      if (response.error) {
        throw new Error(response.error)
      }
      return response.data!
    },
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 1000 * 5, // 5 seconds
  })
}

/**
 * Hook for managing multiple task statuses
 * Useful for tracking multiple concurrent tasks
 * TODO: Implement with useQueries when needed
 */
export const useMultipleTaskStatus = (taskIds: string[]) => {
  // Note: This would require useQueries for multiple queries
  // For now, return a placeholder that can be implemented later
  console.log('Multiple task status tracking not yet implemented for:', taskIds)
  return {
    tasks: [],
    isLoading: false,
    error: null,
  }
}