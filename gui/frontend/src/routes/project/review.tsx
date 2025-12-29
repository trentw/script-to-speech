import { createFileRoute, Navigate } from '@tanstack/react-router';
import { Search } from 'lucide-react';

import { ProblemClipsSection } from '@/components/review/ProblemClipsSection';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useCacheMisses } from '@/hooks/queries/useCacheMisses';
import { useSilentClips } from '@/hooks/queries/useSilentClips';
import { useProject } from '@/stores/appStore';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route
const staticData: RouteStaticData = {
  ui: {
    showPanel: false,
    showFooter: false,
    mobileDrawers: [],
  },
};

export const Route = createFileRoute('/project/review')({
  component: ProjectAudioReview,
  staticData,
});

function ProjectAudioReview() {
  const projectState = useProject();

  // Get project name for hook (null if not in project mode)
  const projectName =
    projectState.mode === 'project'
      ? projectState.project.screenplayName
      : null;

  // Cache misses - auto-fetches on mount (fast operation)
  const {
    data: cacheMissesData,
    isLoading: cacheMissesLoading,
    isRefetching: cacheMissesRefetching,
    error: cacheMissesError,
    refresh: refreshCacheMisses,
  } = useCacheMisses(projectName);

  // Silent clips - auto-fetches (backend caches data from generation)
  const {
    data: silentClipsData,
    isLoading: silentClipsLoading,
    isFetching: silentClipsFetching,
    error: silentClipsError,
    refresh: refreshSilentClips,
  } = useSilentClips(projectName);

  // Type guard and redirect if not in project mode (after hooks)
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const { project } = projectState;

  // Cache folder from either response (they should be the same)
  const cacheFolder =
    cacheMissesData?.cacheFolder || silentClipsData?.cacheFolder || '';

  // Error states
  const hasError = cacheMissesError || silentClipsError;

  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <Search className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Review Audio</h1>
            <p className="text-muted-foreground">{project.screenplayName}</p>
          </div>
        </div>
      </div>

      {/* Error states */}
      {hasError && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Failed to load data</AlertTitle>
          <AlertDescription>
            {cacheMissesError?.message ||
              silentClipsError?.message ||
              'An unknown error occurred'}
          </AlertDescription>
        </Alert>
      )}

      {/* Both sections always shown */}
      <div className="space-y-8">
        {/* Silent Clips Section - only scans on user request or after generation */}
        <ProblemClipsSection
          title="Silent Clips"
          description="Audio clips detected as silent. Regenerate with different text or review the original."
          clips={silentClipsData?.silentClips || []}
          projectName={project.screenplayName}
          cacheFolder={cacheFolder}
          showDbfs
          emptyMessage="No silent clips detected"
          notScannedMessage="No scan data. Click Refresh to scan for silent clips."
          hasScanned={!!silentClipsData?.scannedAt}
          scannedAt={silentClipsData?.scannedAt ?? undefined}
          isLoading={silentClipsLoading || silentClipsFetching}
          onRefresh={refreshSilentClips}
        />

        {/* Cache Misses Section - auto-refreshes on page load */}
        <ProblemClipsSection
          title="Cache Misses"
          description={
            cacheMissesData?.cacheMissesCapped
              ? `Showing first ${cacheMissesData.cacheMisses.length} of ${cacheMissesData.totalCacheMisses} cache misses. Generate audio or run the CLI to create missing clips.`
              : 'Audio clips that need to be generated. Use the Generate Audio page or regenerate individual clips here.'
          }
          clips={cacheMissesData?.cacheMisses || []}
          projectName={project.screenplayName}
          cacheFolder={cacheFolder}
          emptyMessage="No cache misses - all audio is cached"
          hasScanned={!!cacheMissesData}
          scannedAt={cacheMissesData?.scannedAt}
          isLoading={cacheMissesLoading || cacheMissesRefetching}
          onRefresh={refreshCacheMisses}
        />
      </div>
    </div>
  );
}
