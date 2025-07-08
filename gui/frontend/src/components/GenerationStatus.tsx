import React from 'react';
import type { TaskStatusResponse } from '../types';
import { TaskStatus } from '../types';

interface GenerationStatusProps {
  tasks: TaskStatusResponse[];
}

export const GenerationStatus: React.FC<GenerationStatusProps> = ({ tasks }) => {
  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.PENDING:
        return '⏳';
      case TaskStatus.PROCESSING:
        return '🔄';
      case TaskStatus.COMPLETED:
        return '✅';
      case TaskStatus.FAILED:
        return '❌';
      default:
        return '❓';
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.PENDING:
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case TaskStatus.PROCESSING:
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case TaskStatus.COMPLETED:
        return 'text-green-600 bg-green-50 border-green-200';
      case TaskStatus.FAILED:
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const formatProgress = (progress?: number) => {
    if (progress === undefined) return null;
    return Math.round(progress * 100);
  };

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No generation tasks</p>
        <p className="text-sm mt-1">Click "Generate Speech" to start</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <div
          key={task.task_id}
          className={`p-4 border rounded-lg ${getStatusColor(task.status)}`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-lg">
                {getStatusIcon(task.status)}
              </span>
              <div>
                <div className="font-medium">
                  {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                </div>
                <div className="text-sm opacity-90">
                  {task.message}
                </div>
              </div>
            </div>
            
            <div className="text-xs opacity-75">
              {task.task_id.slice(0, 8)}...
            </div>
          </div>

          {/* Progress bar for processing tasks */}
          {task.status === TaskStatus.PROCESSING && task.progress !== undefined && (
            <div className="mt-3">
              <div className="flex justify-between items-center text-sm mb-1">
                <span>Progress</span>
                <span>{formatProgress(task.progress)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${formatProgress(task.progress)}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Result summary for completed tasks */}
          {task.status === TaskStatus.COMPLETED && task.result && (
            <div className="mt-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="font-medium">Provider:</span>
                  <span className="ml-1">{task.result.provider}</span>
                </div>
                <div>
                  <span className="font-medium">Voice:</span>
                  <span className="ml-1">{task.result.voice_id}</span>
                </div>
                <div className="col-span-2">
                  <span className="font-medium">Files:</span>
                  <span className="ml-1">{task.result.files.length} generated</span>
                </div>
                <div className="col-span-2">
                  <span className="font-medium">Text:</span>
                  <span className="ml-1 italic">"{task.result.text_preview}"</span>
                </div>
              </div>
            </div>
          )}

          {/* Error details for failed tasks */}
          {task.status === TaskStatus.FAILED && task.error && (
            <div className="mt-3">
              <div className="text-sm font-medium mb-1">Error Details:</div>
              <div className="text-sm bg-white bg-opacity-50 p-2 rounded border">
                {task.error}
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Summary */}
      {tasks.length > 1 && (
        <div className="border-t pt-3 mt-4">
          <div className="text-sm text-gray-600 grid grid-cols-2 gap-4">
            <div>
              <span className="font-medium">Total:</span>
              <span className="ml-1">{tasks.length} tasks</span>
            </div>
            <div>
              <span className="font-medium">Completed:</span>
              <span className="ml-1">
                {tasks.filter(t => t.status === TaskStatus.COMPLETED).length}
              </span>
            </div>
            <div>
              <span className="font-medium">Processing:</span>
              <span className="ml-1">
                {tasks.filter(t => t.status === TaskStatus.PROCESSING).length}
              </span>
            </div>
            <div>
              <span className="font-medium">Failed:</span>
              <span className="ml-1">
                {tasks.filter(t => t.status === TaskStatus.FAILED).length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};