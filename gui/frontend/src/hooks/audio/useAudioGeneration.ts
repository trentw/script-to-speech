import { useCallback, useState } from 'react';

import { useUIState } from '../../stores/appStore';
import type { GenerationRequest } from '../../types';
import { useCreateTask } from '../mutations/useTasks';
import { useTaskCompletion } from './useTaskCompletion';

/**
 * Hook for managing audio generation workflow
 * Replaces the scattered logic in App.tsx with a clean, focused API
 * Handles task creation, tracking, and completion detection
 */
export const useAudioGeneration = () => {
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const createTaskMutation = useCreateTask();
  const { clearError, setError } = useUIState();

  // Use task completion detection with cleanup callback
  useTaskCompletion(pendingTaskId, () => {
    // Task was processed (either played or had no audio)
    setPendingTaskId(null);
  });

  /**
   * Generate audio for the provided request
   * Returns a promise that resolves when the task is created (not completed)
   */
  const handleGenerate = useCallback(
    async (request: GenerationRequest) => {
      // Clear any previous errors and reset state
      clearError();
      setPendingTaskId(null);

      // Create the generation task
      return new Promise<string>((resolve, reject) => {
        createTaskMutation.mutate(request, {
          onSuccess: (data) => {
            // Start tracking this specific task for completion
            setPendingTaskId(data.task_id);
            resolve(data.task_id);
          },
          onError: (error) => {
            console.error('Task creation failed:', error);
            setError(error.message);
            setPendingTaskId(null);
            reject(error);
          },
        });
      });
    },
    [createTaskMutation, clearError, setError]
  );

  /**
   * Cancel the current generation if it's pending
   * Note: This doesn't cancel the actual task on the server,
   * just stops tracking it for autoplay
   */
  const cancelGeneration = useCallback(() => {
    setPendingTaskId(null);
  }, []);

  /**
   * Check if generation is currently in progress
   * This includes both the API call and waiting for completion
   */
  const isGenerating = createTaskMutation.isPending || !!pendingTaskId;

  /**
   * Get the current pending task ID
   * Useful for UI components that need to show which task is being tracked
   */
  const currentTaskId = pendingTaskId;

  /**
   * Check if we're waiting for a specific task to complete
   * Different from isGenerating which includes the initial API call
   */
  const isWaitingForCompletion =
    !!pendingTaskId && !createTaskMutation.isPending;

  return {
    // Main action
    handleGenerate,

    // State
    isGenerating,
    isWaitingForCompletion,
    currentTaskId,

    // Additional actions
    cancelGeneration,

    // Raw mutation state (for advanced use cases)
    createTaskMutation: {
      isPending: createTaskMutation.isPending,
      error: createTaskMutation.error,
      isError: createTaskMutation.isError,
      reset: createTaskMutation.reset,
    },
  };
};

/**
 * Simplified version of useAudioGeneration for basic use cases
 * Returns just the essential generate function and loading state
 */
export const useSimpleAudioGeneration = () => {
  const { handleGenerate, isGenerating } = useAudioGeneration();

  return {
    generate: handleGenerate,
    isGenerating,
  };
};
