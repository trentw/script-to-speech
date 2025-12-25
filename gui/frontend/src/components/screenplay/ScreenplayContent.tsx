import { useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';

import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useUploadScreenplay } from '@/hooks/mutations/useUploadScreenplay';
import { useRecentScreenplays } from '@/hooks/queries/useRecentScreenplays';
import { useScreenplayResult } from '@/hooks/queries/useScreenplayResult';
import { useScreenplayStatus } from '@/hooks/queries/useScreenplayStatus';
import { useScreenplay, useUIState } from '@/stores/appStore';
import type { RecentScreenplay } from '@/types';

import { ScreenplayHistoryList } from './ScreenplayHistoryList';
import { ScreenplayParsingStatus } from './ScreenplayParsingStatus';
import { ScreenplayResultViewer } from './ScreenplayResultViewer';
import { ScreenplayUploadZone } from './ScreenplayUploadZone';

interface ScreenplayContentProps {
  viewMode: 'upload' | 'status' | 'result';
  setViewMode?: (mode: 'upload' | 'status' | 'result') => void;
  onTaskCreated?: (taskId: string) => void;
}

export function ScreenplayContent({
  viewMode,
  setViewMode,
  onTaskCreated,
}: ScreenplayContentProps) {
  const navigate = useNavigate();
  const {
    currentTaskId,
    setCurrentTaskId,
    setSelectedScreenplay,
    setViewMode: setStoreViewMode,
  } = useScreenplay();

  const { setError, clearError } = useUIState();

  // Queries and mutations
  const uploadMutation = useUploadScreenplay();
  const { data: taskStatus } = useScreenplayStatus(currentTaskId);
  const { data: taskResult } = useScreenplayResult(
    currentTaskId,
    taskStatus?.status === 'completed'
  );
  const { data: recentScreenplays = [] } = useRecentScreenplays();

  // Handle upload
  const handleUpload = async (file: File, textOnly: boolean) => {
    clearError();
    try {
      const result = await uploadMutation.mutateAsync({ file, textOnly });
      setCurrentTaskId(result.task_id);
      // Don't navigate immediately - wait for task to actually start processing
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Upload failed');
    }
  };

  // Handle selection from history
  const handleSelectScreenplay = (screenplay: RecentScreenplay) => {
    setSelectedScreenplay(screenplay);
    setCurrentTaskId(screenplay.task_id);
    // Navigate to the task route
    navigate({
      to: '/screenplay/$taskId',
      params: { taskId: screenplay.task_id },
    });
  };

  // Update view mode based on task status
  useEffect(() => {
    if (taskStatus) {
      // Navigate to task page when task actually starts processing (from upload page)
      if (
        onTaskCreated &&
        (taskStatus.status === 'pending' ||
          taskStatus.status === 'processing') &&
        viewMode === 'upload'
      ) {
        onTaskCreated(currentTaskId!);
        return; // Exit early since we're navigating away
      }

      // Switch to result view when completed and navigate if we're not already on task page
      if (taskStatus.status === 'completed') {
        // Navigate to task page if we're not already there
        if (!window.location.hash.includes(`/screenplay/${currentTaskId}`)) {
          navigate({
            to: '/screenplay/$taskId',
            params: { taskId: currentTaskId! },
          });
        }
        // Update view mode to show results
        if (setViewMode) {
          setViewMode('result');
          setStoreViewMode('result');
        }
      }
      // Switch to status view when backend starts processing (pending or processing)
      else if (
        (taskStatus.status === 'pending' ||
          taskStatus.status === 'processing') &&
        viewMode === 'upload' &&
        setViewMode
      ) {
        setViewMode('status');
        setStoreViewMode('status');
      }
    }
  }, [
    taskStatus,
    viewMode,
    setViewMode,
    setStoreViewMode,
    onTaskCreated,
    currentTaskId,
    navigate,
  ]);

  // Reset to upload mode when no task is selected
  useEffect(() => {
    if (!currentTaskId && viewMode !== 'upload' && setViewMode) {
      setViewMode('upload');
      setStoreViewMode('upload');
    }
  }, [currentTaskId, viewMode, setViewMode, setStoreViewMode]);

  return (
    <div className="flex h-full flex-col overflow-x-hidden overflow-y-auto">
      {/* All content scrolls together */}
      <div className="flex-shrink-0">
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <h2 className="text-2xl font-bold">Screenplay Parser</h2>
          <p className="text-muted-foreground mt-2">
            Upload and parse screenplays from PDF or TXT files into structured
            JSON format
          </p>
        </div>

        <Separator />

        {/* Main Content */}
        <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-3">
          {/* Left Column - Upload/Status/Result */}
          <div className="space-y-6 lg:col-span-2">
            {viewMode === 'upload' && (
              <ScreenplayUploadZone
                onUpload={handleUpload}
                disabled={
                  uploadMutation.isPending ||
                  Boolean(currentTaskId && !taskStatus)
                }
              />
            )}

            {viewMode === 'status' && taskStatus && (
              <ScreenplayParsingStatus status={taskStatus} />
            )}

            {viewMode === 'result' && taskResult && (
              <ScreenplayResultViewer
                result={taskResult}
                taskId={currentTaskId}
              />
            )}
          </div>

          {/* Right Column - Recent History */}
          <div>
            <Card className="p-4">
              <h3 className="mb-4 text-lg font-semibold">Recent Screenplays</h3>
              <ScreenplayHistoryList
                screenplays={recentScreenplays}
                onSelect={handleSelectScreenplay}
                selectedId={currentTaskId}
              />
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
