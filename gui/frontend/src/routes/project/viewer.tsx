import { createFileRoute, Navigate } from '@tanstack/react-router';
import { BookOpen } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScreenplayViewer } from '@/components/viewer/ScreenplayViewer';
import { useChunkInventory } from '@/hooks/queries/useChunkInventory';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { isVoiceCastingComplete } from '@/lib/project-status';
import { useProject } from '@/stores/appStore';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route. The footer hosts the built-in
// UniversalAudioPlayer transport bar - the viewer's playback (single-chunk
// and sequential) runs through the app-wide AudioService, so the footer
// shows and controls the currently playing chunk.
const staticData: RouteStaticData = {
  ui: {
    showPanel: false,
    showFooter: true,
    mobileDrawers: [],
  },
};

export const Route = createFileRoute('/project/viewer')({
  component: ProjectScreenplayViewer,
  staticData,
});

function ProjectScreenplayViewer() {
  const projectState = useProject();

  // Get project info for hooks (null if not in project mode)
  const projectName =
    projectState.mode === 'project'
      ? (projectState.project?.screenplayName ?? null)
      : null;
  const inputPath =
    projectState.mode === 'project'
      ? (projectState.project?.inputPath ?? null)
      : null;

  // Check voice casting status - the inventory needs a full voice config to
  // resolve cache filenames
  const { status } = useProjectStatus(inputPath ?? undefined);
  const isFullyCast = isVoiceCastingComplete(status);

  const {
    data: inventory,
    isLoading,
    isRefetching,
    error,
    refresh,
  } = useChunkInventory(projectName, isFullyCast);

  // Type guard and redirect if not in project mode (after hooks)
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const { project } = projectState;
  // The parent /project route redirects here too; guard for type narrowing
  if (!project) {
    return <Navigate to="/project/welcome" replace />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col px-6 py-6">
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <BookOpen className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Screenplay Viewer
            </h1>
            <p className="text-muted-foreground">{project.screenplayName}</p>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Failed to load chunk inventory</AlertTitle>
          <AlertDescription>
            {error.message || 'An unknown error occurred'}
          </AlertDescription>
        </Alert>
      )}

      <div className="min-h-0 flex-1">
        <ScreenplayViewer
          // ProjectControls can replace the active project without changing
          // this route's pathname. Remount at that identity boundary so a
          // selection or active sequence from one screenplay cannot carry
          // over to same-numbered chunks in another screenplay.
          key={project.inputPath}
          inventory={inventory}
          projectName={project.screenplayName}
          hasPdf={status?.hasPdf ?? false}
          isLoading={isLoading || isRefetching}
          onRefresh={refresh}
          disabled={!isFullyCast}
          disabledReason="Complete voice casting before loading chunks"
          warningMessage={
            !isFullyCast
              ? 'Complete voice casting before viewing the screenplay.'
              : undefined
          }
        />
      </div>
    </div>
  );
}
