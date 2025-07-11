import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { queryKeys } from '../../lib/queryKeys'
import type { GenerationRequest, TaskResponse } from '../../types'

/**
 * Mutation hook for creating new generation tasks
 * Includes optimistic updates and proper cache invalidation
 */
export const useCreateTask = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (request: GenerationRequest): Promise<TaskResponse> => {
      const response = await apiService.createGenerationTask(request)
      if (response.error) {
        throw new Error(response.error)
      }
      return response.data!
    },
    onSuccess: (data) => {
      // Invalidate tasks list to show new task
      queryClient.invalidateQueries({ queryKey: queryKeys.allTasks })
      
      // Start polling for the new task by prefetching
      queryClient.prefetchQuery({
        queryKey: queryKeys.taskStatus(data.task_id),
        queryFn: async () => {
          const response = await apiService.getTaskStatus(data.task_id)
          if (response.error) throw new Error(response.error)
          return response.data!
        },
      })
    },
    onError: (error) => {
      console.error('Task creation failed:', error)
    },
    onSettled: (data) => {
      // Additional cleanup or logging can go here
      if (data) {
        console.log('Task created successfully:', data.task_id)
      }
    },
  })
}

/**
 * Mutation hook for cleaning up old tasks
 */
export const useCleanupTasks = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (maxAgeHours: number = 24) => {
      const response = await apiService.cleanupOldTasks(maxAgeHours)
      if (response.error) {
        throw new Error(response.error)
      }
      return response.data!
    },
    onSuccess: () => {
      // Invalidate tasks list after cleanup
      queryClient.invalidateQueries({ queryKey: queryKeys.allTasks })
    },
  })
}