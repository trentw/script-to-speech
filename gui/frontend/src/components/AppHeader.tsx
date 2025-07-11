import React from 'react';
import { BackendStatus } from './BackendStatus';

interface AppHeaderProps {
  onStatusChange: (isRunning: boolean) => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({ onStatusChange }) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Script to Speech</h1>
            <p className="text-sm text-gray-500">TTS Playground Desktop Application</p>
          </div>
          <div className="max-w-xs">
            <BackendStatus onStatusChange={onStatusChange} />
          </div>
        </div>
      </div>
    </header>
  );
};