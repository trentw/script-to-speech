import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';

import { ScreenplayContent } from '../../components/screenplay/ScreenplayContent';
import { RouteError } from '@/components/errors';
import { useScreenplay } from '../../stores/appStore';
import type { RouteStaticData } from '../../types/route-metadata';

export const Route = createFileRoute('/screenplay/$taskId')({
  component: ScreenplayTaskView,
  errorComponent: RouteError,
  staticData: {
    title: 'Screenplay Details',
    description: 'View the status and results of screenplay parsing tasks',
  } satisfies RouteStaticData,
});

function ScreenplayTaskView() {
  const { taskId } = Route.useParams();
  const navigate = useNavigate({ from: '/screenplay/$taskId' });
  const { setCurrentTaskId, setViewMode: setStoreViewMode, viewMode } = useScreenplay();

  // Set the task ID in the store when this route loads
  useEffect(() => {
    if (taskId) {
      setCurrentTaskId(taskId);
    }
  }, [taskId, setCurrentTaskId]);

  // Handle view mode changes
  const handleViewModeChange = (mode: 'upload' | 'status' | 'result') => {
    if (mode === 'upload') {
      // Navigate back to the upload route
      navigate({ to: '/screenplay' });
    } else {
      setStoreViewMode(mode);
    }
  };

  return (
    <ScreenplayContent
      viewMode={viewMode === 'upload' ? 'status' : viewMode} // Default to status for this route
      setViewMode={handleViewModeChange}
    />
  );
}