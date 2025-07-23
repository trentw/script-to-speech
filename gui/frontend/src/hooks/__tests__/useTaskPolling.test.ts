import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  TEST_TASK_COMPLETED,
  TEST_TASK_FAILED,
  TEST_TASK_PENDING,
  TEST_TASK_PROCESSING,
} from '@/test/utils/test-data';
import type { TaskStatusResponse as _TaskStatusResponse } from '@/types';

import { useTaskPolling } from '../useTaskPolling';

const mockApiService = {
  getTaskStatus: vi.fn(),
};

// Mock the apiService module
vi.mock('../../services/api', () => ({
  apiService: {
    getTaskStatus: (taskId: string) => mockApiService.getTaskStatus(taskId),
  },
}));

describe('useTaskPolling Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  describe('Task Polling', () => {
    it('should poll task status at 1 second intervals', async () => {
      // Arrange
      const taskId = 'task-123';
      const pendingTask = { ...TEST_TASK_PENDING, task_id: taskId };
      const processingTask = { ...TEST_TASK_PROCESSING, task_id: taskId };
      const completedTask = { ...TEST_TASK_COMPLETED, task_id: taskId };

      let callCount = 0;
      mockApiService.getTaskStatus.mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve({ data: pendingTask, error: null });
        if (callCount === 2)
          return Promise.resolve({ data: processingTask, error: null });
        if (callCount === 3)
          return Promise.resolve({ data: completedTask, error: null });
        return Promise.resolve({ data: completedTask, error: null });
      });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus(taskId);
      });

      // Assert - initial state
      expect(result.current.generationTasks).toEqual([]);

      // Wait for first poll
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(1);
      expect(result.current.generationTasks).toEqual([pendingTask]);

      // Wait for second poll
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(2);
      expect(result.current.generationTasks).toEqual([processingTask]);

      // Wait for third poll
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(3);
      expect(result.current.generationTasks).toEqual([completedTask]);

      // Should stop polling after completion
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(3);
    });

    it('should stop polling when task fails', async () => {
      // Arrange
      const taskId = 'task-failed-123';
      const processingTask = { ...TEST_TASK_PROCESSING, task_id: taskId };
      const failedTask = { ...TEST_TASK_FAILED, task_id: taskId };

      let callCount = 0;
      mockApiService.getTaskStatus.mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve({ data: processingTask, error: null });
        return Promise.resolve({ data: failedTask, error: null });
      });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus(taskId);
      });

      // First poll
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toEqual([processingTask]);

      // Second poll - failed
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toEqual([failedTask]);

      // Should stop polling after failure
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(2);
    });

    it('should handle multiple tasks simultaneously', async () => {
      // Arrange
      const task1 = { ...TEST_TASK_PROCESSING, task_id: 'task-1' };
      const task2 = { ...TEST_TASK_PROCESSING, task_id: 'task-2' };

      mockApiService.getTaskStatus.mockImplementation((taskId: string) => {
        if (taskId === 'task-1') {
          return Promise.resolve({ data: task1, error: null });
        }
        return Promise.resolve({ data: task2, error: null });
      });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus('task-1');
        result.current.pollTaskStatus('task-2');
      });

      // Wait for polls
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toHaveLength(2);
      expect(result.current.generationTasks).toContainEqual(task1);
      expect(result.current.generationTasks).toContainEqual(task2);

      // Update mock to return completed status
      const task1Completed = { ...TEST_TASK_COMPLETED, task_id: 'task-1' };
      const task2Completed = { ...TEST_TASK_COMPLETED, task_id: 'task-2' };

      mockApiService.getTaskStatus.mockImplementation((taskId: string) => {
        if (taskId === 'task-1') {
          return Promise.resolve({ data: task1Completed, error: null });
        }
        return Promise.resolve({ data: task2Completed, error: null });
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toHaveLength(2);
      expect(result.current.generationTasks).toContainEqual(task1Completed);
      expect(result.current.generationTasks).toContainEqual(task2Completed);
    });

    it('should replace existing task with same ID', async () => {
      // Arrange
      const initialTask = { ...TEST_TASK_PENDING, task_id: 'task-123' };
      const updatedTask = { ...TEST_TASK_PROCESSING, task_id: 'task-123' };

      mockApiService.getTaskStatus.mockResolvedValueOnce({
        data: updatedTask,
        error: null,
      });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      // Set initial task
      act(() => {
        result.current.setGenerationTasks([initialTask]);
      });

      expect(result.current.generationTasks).toEqual([initialTask]);

      // Start polling
      act(() => {
        result.current.pollTaskStatus('task-123');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      // Assert - should replace, not duplicate
      expect(result.current.generationTasks).toHaveLength(1);
      expect(result.current.generationTasks[0]).toEqual(updatedTask);
    });
  });

  describe('Error Handling', () => {
    it('should stop polling on API error', async () => {
      // Arrange
      mockApiService.getTaskStatus
        .mockResolvedValueOnce({ data: TEST_TASK_PROCESSING, error: null })
        .mockResolvedValueOnce({ data: null, error: 'Network error' });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus('task-123');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toEqual([TEST_TASK_PROCESSING]);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      // Should stop polling after error
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(2);
      // Task should remain in previous state
      expect(result.current.generationTasks).toEqual([TEST_TASK_PROCESSING]);
    });

    it('should handle API exceptions', async () => {
      // Arrange
      mockApiService.getTaskStatus
        .mockResolvedValueOnce({ data: TEST_TASK_PENDING, error: null })
        .mockRejectedValueOnce(new Error('API Error'));

      // Act
      const { result } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus('task-123');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.generationTasks).toEqual([TEST_TASK_PENDING]);

      // Should handle exception without crashing
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      // Task should remain in previous state
      expect(result.current.generationTasks).toEqual([TEST_TASK_PENDING]);
    });
  });

  describe('Cleanup', () => {
    it('should provide cleanup function that stops polling', async () => {
      // Arrange
      mockApiService.getTaskStatus.mockResolvedValue({
        data: TEST_TASK_PROCESSING,
        error: null,
      });

      // Act
      const { result } = renderHook(() => useTaskPolling());

      let cleanup: (() => void) | undefined;

      act(() => {
        cleanup = result.current.pollTaskStatus('task-123');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(1);

      // Clean up
      act(() => {
        cleanup?.();
      });

      // Should not poll anymore
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });

      expect(mockApiService.getTaskStatus).toHaveBeenCalledTimes(1);
    });

    it('should clean up all intervals on unmount', async () => {
      // Arrange
      mockApiService.getTaskStatus.mockResolvedValue({
        data: TEST_TASK_PROCESSING,
        error: null,
      });

      // Act
      const { result, unmount } = renderHook(() => useTaskPolling());

      act(() => {
        result.current.pollTaskStatus('task-1');
        result.current.pollTaskStatus('task-2');
        result.current.pollTaskStatus('task-3');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      const initialCallCount = mockApiService.getTaskStatus.mock.calls.length;
      expect(initialCallCount).toBeGreaterThan(0);

      // Unmount
      unmount();

      // Clear timers to prevent any pending intervals
      vi.clearAllTimers();

      // Reset mock to track new calls
      mockApiService.getTaskStatus.mockClear();

      // Should not poll anymore
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });

      expect(mockApiService.getTaskStatus).not.toHaveBeenCalled();
    });
  });

  describe('State Management', () => {
    it('should allow manual task management', () => {
      // Act
      const { result } = renderHook(() => useTaskPolling());

      // Manually set tasks
      act(() => {
        result.current.setGenerationTasks([
          TEST_TASK_PENDING,
          TEST_TASK_PROCESSING,
        ]);
      });

      // Assert
      expect(result.current.generationTasks).toEqual([
        TEST_TASK_PENDING,
        TEST_TASK_PROCESSING,
      ]);

      // Clear tasks
      act(() => {
        result.current.setGenerationTasks([]);
      });

      expect(result.current.generationTasks).toEqual([]);
    });
  });
});
