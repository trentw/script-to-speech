import { useQuery } from '@tanstack/react-query';
import { createFileRoute, Link, Navigate } from '@tanstack/react-router';
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import { useState } from 'react';

import { ScreenplayResultViewer } from '@/components/screenplay/ScreenplayResultViewer';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { API_BASE_URL } from '@/config/api';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { useProject } from '@/stores/appStore';
import type { ScreenplayResult } from '@/types';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route
const staticData: RouteStaticData = {
  ui: {
    showPanel: false,
    showFooter: false,
    mobileDrawers: [],
  },
};

export const Route = createFileRoute('/project/screenplay')({
  component: ProjectScreenplayInfo,
  staticData,
});

function ProjectScreenplayInfo() {
  const projectState = useProject();
  const [isReparsing, setIsReparsing] = useState(false);
  const containerClasses = 'container mx-auto px-6 py-8';

  // Get inputPath before any conditional logic (hooks must be unconditional)
  const inputPath =
    projectState.mode === 'project'
      ? projectState.project.inputPath
      : undefined;
  const screenplayName =
    projectState.mode === 'project'
      ? projectState.project.screenplayName
      : undefined;

  const {
    status,
    isLoading: _isLoading,
    error,
    invalidate,
  } = useProjectStatus(inputPath);

  // Load the screenplay data from backend
  const { data: screenplayData, refetch: refetchScreenplay } = useQuery({
    queryKey: ['project-screenplay-result', inputPath, screenplayName],
    queryFn: async (): Promise<ScreenplayResult | null> => {
      if (!status?.hasJson || !inputPath || !screenplayName) return null;

      try {
        // Fetch from the new backend endpoint
        const response = await fetch(
          `${API_BASE_URL}/screenplay/result-from-path?` +
            `input_path=${encodeURIComponent(inputPath)}&` +
            `screenplay_name=${encodeURIComponent(screenplayName)}`
        );

        if (!response.ok) {
          throw new Error('Failed to load screenplay result');
        }

        const result = await response.json();

        // Map backend response to ScreenplayResult interface
        return {
          screenplay_name: result.screenplay_name,
          original_filename: result.original_filename,
          analysis: result.analysis,
          files: result.files,
          log_file: result.log_file,
          text_only: result.text_only || false,
        };
      } catch (err) {
        console.error('Failed to load screenplay data:', err);
        return null;
      }
    },
    enabled: !!status?.hasJson && !!inputPath && !!screenplayName,
    // Leverage existing refetch patterns
    refetchOnWindowFocus: true,
    staleTime: 5000,
  });

  // Type guard and redirect if not in project mode (after all hooks)
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const handleReparse = async () => {
    setIsReparsing(true);
    try {
      // For now, just refresh the data from disk
      // In the future, we could add a reparse endpoint if needed
      await invalidate();
      await refetchScreenplay();
    } catch (err) {
      console.error('Failed to refresh:', err);
    } finally {
      setIsReparsing(false);
    }
  };

  if (error) {
    return (
      <div className={containerClasses}>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load project status: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!status?.hasJson) {
    return (
      <div className={containerClasses}>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please parse your screenplay first before viewing details.
            <Button asChild variant="link" className="ml-2 h-auto p-0">
              <Link to="/project">Go to Overview</Link>
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/project"
              className={appButtonVariants({
                variant: 'secondary',
                size: 'icon',
              })}
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-3xl font-bold tracking-tight">
              Screenplay Information
            </h1>
          </div>
          <button
            className={appButtonVariants({
              variant: 'secondary',
              size: 'sm',
            })}
            onClick={handleReparse}
            disabled={isReparsing}
          >
            {isReparsing ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Reparsing...
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Re-parse
              </>
            )}
          </button>
        </div>
        <p className="text-muted-foreground mt-2">
          Detailed analysis of your parsed screenplay structure and content.
        </p>
      </div>

      {/* Use ScreenplayResultViewer if we have data */}
      {screenplayData ? (
        <ScreenplayResultViewer
          result={screenplayData}
          taskId={screenplayName!} // Use project name as taskId for downloads
        />
      ) : (
        /* Fallback to basic stats if ScreenplayResultViewer data not available */
        <>
          {/* Screenplay Statistics */}
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  Dialogue Chunks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {status?.dialogueChunks || 0}
                </div>
                <p className="text-muted-foreground text-xs">
                  Individual dialogue segments
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  Speakers
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {status?.speakerCount || 0}
                </div>
                <p className="text-muted-foreground text-xs">
                  Unique characters found
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  Voices Assigned
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {status?.voicesAssigned || 0}
                </div>
                <p className="text-muted-foreground text-xs">
                  Characters with voice casting
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button asChild>
              <Link to="/project/voices">Continue to Voice Casting</Link>
            </Button>
          </div>
        </>
      )}

      {/* Error Information */}
      {status?.jsonError && (
        <Alert variant="destructive" className="mt-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            There were issues with the screenplay JSON: {status.jsonError}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
