import { createFileRoute, useNavigate } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';

import { ScreenplayContent } from '../../components/screenplay/ScreenplayContent';
import { useScreenplay } from '../../stores/appStore';
import type { RouteStaticData } from '../../types/route-metadata';

export const Route = createFileRoute('/screenplay/')({
  component: ScreenplayUploadView,
  errorComponent: RouteError,
  staticData: {
    // Title inherited from parent route: "Screenplay Parser"
    description: 'Upload a screenplay PDF file to begin parsing',
    helpText:
      'Supported formats: PDF files containing properly formatted screenplays. The parser will extract dialogue, character names, and scene information.',
  } satisfies RouteStaticData,
});

function ScreenplayUploadView() {
  const navigate = useNavigate({ from: '/screenplay' });
  const { setViewMode: setStoreViewMode } = useScreenplay();

  // When a task is created, navigate to the task-specific route
  const handleTaskCreated = (taskId: string) => {
    setStoreViewMode('status');
    navigate({ to: '/screenplay/$taskId', params: { taskId } });
  };

  return (
    <ScreenplayContent viewMode="upload" onTaskCreated={handleTaskCreated} />
  );
}
