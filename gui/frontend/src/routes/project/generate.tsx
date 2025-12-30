import { createFileRoute, Navigate } from '@tanstack/react-router';
import { FileAudio } from 'lucide-react';
import { useState } from 'react';

import {
  AudiobookGenerationControls,
  AudiobookGenerationProgress,
  AudiobookGenerationResult,
} from '@/components/audiobook';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCreateAudiobookTask } from '@/hooks/mutations/useCreateAudiobookTask';
import {
  useAudiobookResult,
  useAudiobookStatus,
} from '@/hooks/queries/useAudiobookStatus';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { isVoiceCastingComplete } from '@/lib/project-status';
import { useProject } from '@/stores/appStore';
import type { AudiobookGenerationRequest } from '@/types';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route
const staticData: RouteStaticData = {
  ui: {
    showPanel: false,
    showFooter: false,
    mobileDrawers: [],
  },
};

export const Route = createFileRoute('/project/generate')({
  component: ProjectAudioGeneration,
  staticData,
});

function ProjectAudioGeneration() {
  const projectState = useProject();
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  // Get input path for project status check (before type guard)
  const inputPath =
    projectState.mode === 'project'
      ? projectState.project.inputPath
      : undefined;

  // Check voice casting status
  const { status } = useProjectStatus(inputPath);
  const isFullyCast = isVoiceCastingComplete(status);

  const createTask = useCreateAudiobookTask();
  const { data: progress } = useAudiobookStatus(currentTaskId);
  const { data: result } = useAudiobookResult(
    currentTaskId,
    progress?.status === 'completed'
  );

  // Type guard and redirect if not in project mode
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const { project } = projectState;

  // Build file paths from project state
  const inputJsonPath = `${project.inputPath}/${project.screenplayName}.json`;
  const voiceConfigPath = `${project.inputPath}/${project.screenplayName}_voice_config.yaml`;

  const handleGenerate = async (request: AudiobookGenerationRequest) => {
    try {
      const response = await createTask.mutateAsync(request);
      setCurrentTaskId(response.taskId);
    } catch (error) {
      console.error('Failed to start generation:', error);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <FileAudio className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Generate Audiobook
            </h1>
            <p className="text-muted-foreground">{project.screenplayName}</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Error Display */}
        {createTask.isError && (
          <Alert variant="destructive">
            <AlertTitle>Failed to Start Generation</AlertTitle>
            <AlertDescription>
              {createTask.error?.message || 'An unknown error occurred'}
            </AlertDescription>
          </Alert>
        )}

        {/* Show controls when no task is running */}
        {!currentTaskId && (
          <AudiobookGenerationControls
            projectName={project.screenplayName}
            inputJsonPath={inputJsonPath}
            voiceConfigPath={voiceConfigPath}
            onGenerate={handleGenerate}
            isGenerating={createTask.isPending}
            disabled={!isFullyCast}
            disabledReason={
              !isFullyCast
                ? 'Complete voice casting to enable audio generation'
                : undefined
            }
          />
        )}

        {/* Show progress when task is running */}
        {currentTaskId && progress && (
          <AudiobookGenerationProgress progress={progress} />
        )}

        {/* Show result when task is complete */}
        {result && (
          <AudiobookGenerationResult
            result={result}
            projectName={project.screenplayName}
            onStartNew={() => setCurrentTaskId(null)}
          />
        )}

        {/* File Paths Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Project Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex items-start gap-2">
                <span className="text-muted-foreground w-24 shrink-0">
                  Input JSON:
                </span>
                <code className="bg-muted rounded px-2 py-1 text-xs break-all">
                  {inputJsonPath}
                </code>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-muted-foreground w-24 shrink-0">
                  Voice Config:
                </span>
                <code className="bg-muted rounded px-2 py-1 text-xs break-all">
                  {voiceConfigPath}
                </code>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-muted-foreground w-24 shrink-0">
                  Output Dir:
                </span>
                <code className="bg-muted rounded px-2 py-1 text-xs break-all">
                  {project.outputPath}
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
