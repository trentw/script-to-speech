import {
  createFileRoute,
  Navigate,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router';
import { Search } from 'lucide-react';
import { useEffect } from 'react';

import { ProblemClipsSection } from '@/components/review/ProblemClipsSection';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useCacheMisses } from '@/hooks/queries/useCacheMisses';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { useSilentClips } from '@/hooks/queries/useSilentClips';
import { isVoiceCastingComplete } from '@/lib/project-status';
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
  const navigate = useNavigate();

  // Get scroll-to-section from location state
  const location = useRouterState({ select: (s) => s.location });
  const scrollToSection = location.state?.scrollToSection as
    | 'silent-clips'
    | 'missing-clips'
    | undefined;

  // Handle scroll-to-section effect
  useEffect(() => {
    if (scrollToSection) {
      const scrollToElement = () => {
        const sectionId =
          scrollToSection === 'silent-clips'
            ? 'review-silent-clips'
            : 'review-missing-clips';
        const element = document.getElementById(sectionId);
        if (element) {
          element.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
          });
        }
      };

      // Use requestAnimationFrame to ensure DOM is ready
      const frameId = requestAnimationFrame(() => {
        setTimeout(scrollToElement, 50);
      });

      // Clear state after scroll
      const timer = setTimeout(() => {
        navigate({ to: '.', replace: true, state: {} });
      }, 1000);

      return () => {
        clearTimeout(timer);
        cancelAnimationFrame(frameId);
      };
    }
  }, [scrollToSection, navigate]);

  // Get project info for hooks (null if not in project mode)
  const projectName =
    projectState.mode === 'project'
      ? projectState.project.screenplayName
      : null;
  const inputPath =
    projectState.mode === 'project' ? projectState.project.inputPath : null;

  // Check voice casting status
  const { status } = useProjectStatus(inputPath ?? undefined);
  const isFullyCast = isVoiceCastingComplete(status);

  // Cache misses - only auto-fetch when voice casting is complete
  const {
    data: cacheMissesData,
    isLoading: cacheMissesLoading,
    isRefetching: cacheMissesRefetching,
    error: cacheMissesError,
    refresh: refreshCacheMisses,
  } = useCacheMisses(projectName, isFullyCast);

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
        <div id="review-silent-clips">
          <ProblemClipsSection
            title="Silent Clips"
            description="Audio clips detected as silent. Regenerate with different text or review the original."
            clips={silentClipsData?.silentClips || []}
            projectName={project.screenplayName}
            cacheFolder={cacheFolder}
            showDbfs
            emptyMessage="No silent clips detected"
            notScannedMessage={
              isFullyCast
                ? 'No scan data. Click Refresh to scan for silent clips.'
                : undefined
            }
            hasScanned={!!silentClipsData?.scannedAt}
            scannedAt={silentClipsData?.scannedAt ?? undefined}
            isLoading={silentClipsLoading || silentClipsFetching}
            onRefresh={refreshSilentClips}
            disabled={!isFullyCast}
            disabledReason="Complete voice casting before scanning"
            warningMessage={
              !isFullyCast
                ? 'Complete voice casting before scanning for new silent clips.'
                : undefined
            }
          />
        </div>

        {/* Missing Clips Section - auto-refreshes on page load when voice casting is complete */}
        <div id="review-missing-clips">
          <ProblemClipsSection
            title="Missing Clips"
            description={
              cacheMissesData?.cacheMissesCapped
                ? `Showing first ${cacheMissesData.cacheMisses.length} of ${cacheMissesData.totalCacheMisses} missing clips. Generate audio or run the CLI to create missing clips.`
                : 'Audio clips that need to be generated. Use the Generate Audio page or regenerate individual clips here.'
            }
            clips={cacheMissesData?.cacheMisses || []}
            projectName={project.screenplayName}
            cacheFolder={cacheFolder}
            emptyMessage="No missing clips - all audio has been generated"
            notScannedMessage={undefined}
            hasScanned={isFullyCast ? !!cacheMissesData : false}
            scannedAt={cacheMissesData?.scannedAt}
            isLoading={cacheMissesLoading || cacheMissesRefetching}
            onRefresh={refreshCacheMisses}
            disabled={!isFullyCast}
            disabledReason="Complete voice casting before scanning"
            warningMessage={
              !isFullyCast
                ? 'Complete voice casting before checking for missing clips.'
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
}
