import React, { useState } from 'react';
import { HistoryTab } from '../HistoryTab';
import { HistoryDetailsPanel } from '../HistoryDetailsPanel';
import type { TaskStatusResponse } from '../../types';

export const HistoryContent: React.FC = () => {
  const [selectedHistoryTask, setSelectedHistoryTask] = useState<TaskStatusResponse | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleShowHistoryDetails = (task: TaskStatusResponse) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setSelectedHistoryTask(task);
      setIsTransitioning(false);
    }, 150);
  };

  const handleBackToHistory = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setSelectedHistoryTask(null);
      setIsTransitioning(false);
    }, 150);
  };

  return (
    <div className="h-full flex flex-col relative">
      <div className={`absolute inset-0 transition-all duration-300 ease-in-out ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}>
        <div className={`h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
          selectedHistoryTask ? '-translate-x-full' : 'translate-x-0'
        }`}>
          <HistoryTab onTaskSelect={handleShowHistoryDetails} />
        </div>
        
        {/* History Details Panel - slides in from the right */}
        <div className={`absolute inset-0 h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
          selectedHistoryTask ? 'translate-x-0' : 'translate-x-full'
        }`}>
          {selectedHistoryTask && (
            <HistoryDetailsPanel
              task={selectedHistoryTask}
              onBack={handleBackToHistory}
            />
          )}
        </div>
      </div>
    </div>
  );
};