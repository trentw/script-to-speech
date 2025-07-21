import { useEffect, useRef } from 'react';

import type { TaskStatusResponse } from '../../types';
import { getAudioFilename, getAudioUrls } from '../../utils/audioUtils';
import { useSmartTaskPolling } from '../queries/useSmartTaskPolling';
import { useAudioEvents } from './useAudioEvents';

/**
 * Hook for detecting task completion and triggering audio playback
 * Decouples task completion detection from UI components
 * Uses event-driven architecture to trigger audio commands
 */
export const useTaskCompletion = (
  pendingTaskId: string | null,
  onTaskProcessed?: (taskId: string) => void
) => {
  const { data: tasks } = useSmartTaskPolling();
  const { playGeneratedAudio } = useAudioEvents();

  useEffect(() => {
    // Early return if no pending task or no tasks data
    if (!pendingTaskId || !tasks) return;

    // Find the specific task we're waiting for
    const completedTask = tasks.find(
      (task) => task.task_id === pendingTaskId && task.status === 'completed'
    );

    // If task is not yet completed, keep waiting
    if (!completedTask) return;

    // Task completed! Check if it has audio files
    const audioUrls = getAudioUrls(completedTask);
    if (audioUrls.length === 0) {
      // No audio files, but task is complete - still call onTaskProcessed
      onTaskProcessed?.(pendingTaskId);
      return;
    }

    // Prepare audio data for playback
    const displayText =
      completedTask.request?.text ||
      completedTask.result?.text_preview ||
      'Generated audio';
    const provider =
      completedTask.request?.provider || completedTask.result?.provider;
    const voiceId =
      completedTask.request?.sts_id || completedTask.result?.voice_id;

    // Trigger audio playback through event system
    playGeneratedAudio({
      url: audioUrls[0], // Use first audio file for single player
      primaryText:
        displayText.length > 50
          ? displayText.slice(0, 50) + '...'
          : displayText,
      secondaryText: [provider, voiceId].filter(Boolean).join(' • '),
      downloadFilename: getAudioFilename(completedTask, 0),
      autoplay: true,
      source: 'generation',
    });

    // Notify that task was processed
    onTaskProcessed?.(pendingTaskId);
  }, [tasks, pendingTaskId, playGeneratedAudio, onTaskProcessed]);
};

/**
 * Hook for detecting any task completion (not just specific ones)
 * Useful for general task monitoring and UI updates
 */
export const useAnyTaskCompletion = (
  onTaskCompleted?: (taskId: string, task: TaskStatusResponse) => void
) => {
  const { data: tasks } = useSmartTaskPolling();
  const processedTaskIds = useRef(new Set<string>());

  useEffect(() => {
    if (!tasks || !onTaskCompleted) return;

    // Check for newly completed tasks that haven't been processed yet
    const newlyCompletedTasks = tasks.filter(
      (task) =>
        task.status === 'completed' &&
        !processedTaskIds.current.has(task.task_id)
    );

    newlyCompletedTasks.forEach((task) => {
      processedTaskIds.current.add(task.task_id);
      onTaskCompleted(task.task_id, task);
    });
  }, [tasks, onTaskCompleted]);
};
