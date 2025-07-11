import React from 'react';
import { GenerationStatus } from './GenerationStatus';
import { AudioPlayer } from './AudioPlayer';
import { useUIState } from '../stores/appStore';
import type { TaskStatusResponse } from '../types';

interface ResultsPanelProps {
  generationTasks: TaskStatusResponse[];
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  generationTasks,
}) => {
  const { error, clearError } = useUIState();
  return (
    <div className="space-y-6">
      
      {/* Generation Status */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Generation Status</h2>
        <GenerationStatus tasks={generationTasks} />
      </div>

      {/* Audio Player */}
      {generationTasks.some(t => t.status === 'completed' && t.result) && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generated Audio</h2>
          <AudioPlayer
            tasks={generationTasks.filter(t => t.status === 'completed' && t.result)}
          />
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="card p-6 border-red-200 bg-red-50">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
          <button
            className="btn-secondary mt-3"
            onClick={clearError}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};