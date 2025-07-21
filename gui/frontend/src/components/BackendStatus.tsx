import React, { useEffect, useState } from 'react';

// Check if we're running in Tauri
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__;

// Dynamically import Tauri API only when needed
const invokeCommand = async (command: string) => {
  if (!isTauri) {
    throw new Error('Tauri commands not available in web mode');
  }

  const { invoke } = await import('@tauri-apps/api/core');
  return invoke(command);
};

interface BackendStatusProps {
  onStatusChange?: (isRunning: boolean) => void;
}

export const BackendStatus: React.FC<BackendStatusProps> = ({
  onStatusChange,
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check initial status by trying to connect to the health endpoint
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/health');
      const running = response.ok;
      setIsRunning(running);
      onStatusChange?.(running);
    } catch {
      setIsRunning(false);
      onStatusChange?.(false);
    }
  };

  const startBackend = async () => {
    setIsStarting(true);
    setError(null);

    try {
      if (isTauri) {
        // Use Tauri command to start backend
        await invokeCommand('start_backend');

        // Wait a moment for the server to start, then check status
        setTimeout(async () => {
          await checkBackendStatus();
          setIsStarting(false);
        }, 3000);
      } else {
        // In web mode, just assume the backend should be started manually
        setError(
          'Please start the backend manually: cd gui/backend && uv run sts-gui-server'
        );
        setIsStarting(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsStarting(false);
    }
  };

  const stopBackend = async () => {
    try {
      if (isTauri) {
        // Use Tauri command to stop backend
        await invokeCommand('stop_backend');
      }
      setIsRunning(false);
      onStatusChange?.(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-gray-50 p-3">
      <div
        className={`h-3 w-3 rounded-full ${
          isRunning
            ? 'bg-green-500'
            : isStarting
              ? 'animate-pulse bg-yellow-500'
              : 'bg-red-500'
        }`}
      />

      <div className="flex-1">
        <div className="text-sm font-medium">
          Backend Status:{' '}
          {isStarting ? 'Starting...' : isRunning ? 'Running' : 'Stopped'}
          {isTauri && (
            <span className="ml-2 rounded bg-blue-100 px-2 py-1 text-xs text-blue-800">
              Desktop
            </span>
          )}
        </div>
        {error && (
          <div className="mt-1 text-xs text-red-600">Error: {error}</div>
        )}
      </div>

      <div className="flex gap-2">
        {isTauri && !isRunning && !isStarting && (
          <button
            onClick={startBackend}
            className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700"
          >
            Start Backend
          </button>
        )}

        {isTauri && isRunning && (
          <button
            onClick={stopBackend}
            className="rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700"
          >
            Stop Backend
          </button>
        )}

        <button
          onClick={checkBackendStatus}
          className="rounded bg-gray-600 px-3 py-1 text-xs text-white hover:bg-gray-700"
        >
          Refresh
        </button>
      </div>
    </div>
  );
};
