import { createFileRoute, Navigate } from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { AlertTriangle, FileAudio, Tag } from 'lucide-react';
import { useState } from 'react';

import {
  AudiobookGenerationControls,
  AudiobookGenerationProgress,
  AudiobookGenerationResult,
  Id3TagEditor,
} from '@/components/audiobook';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useCreateAudiobookTask } from '@/hooks/mutations/useCreateAudiobookTask';
import {
  useAudiobookResult,
  useAudiobookStatus,
} from '@/hooks/queries/useAudiobookStatus';
import { useId3TagConfig } from '@/hooks/queries/useId3TagConfig';
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

  // ID3 tag config for missing-fields check
  const { config: id3Config } = useId3TagConfig(inputPath);

  // Warning dialog state
  const [showWarning, setShowWarning] = useState(false);
  const [pendingRequest, setPendingRequest] =
    useState<AudiobookGenerationRequest | null>(null);
  // Incrementing key to retrigger highlight animation each time
  const [highlightKey, setHighlightKey] = useState(0);

  // Type guard and redirect if not in project mode
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const { project } = projectState;

  // Resolve display title
  const displayTitle = id3Config?.title || project.screenplayName;

  // Compute missing ID3 fields
  const missingFields: string[] = [];
  if (!id3Config?.title) missingFields.push('Title');
  if (!id3Config?.screenplayAuthor) missingFields.push('Author');
  if (!id3Config?.date) missingFields.push('Year');
  const hasMissingFields = missingFields.length > 0;

  // Build file paths from project state
  const inputJsonPath = `${project.inputPath}/${project.screenplayName}.json`;
  const voiceConfigPath = `${project.inputPath}/${project.screenplayName}_voice_config.yaml`;

  const handleGenerate = async (request: AudiobookGenerationRequest) => {
    if (hasMissingFields) {
      setPendingRequest(request);
      setShowWarning(true);
      return;
    }
    await doGenerate(request);
  };

  const doGenerate = async (request: AudiobookGenerationRequest) => {
    try {
      const response = await createTask.mutateAsync(request);
      setCurrentTaskId(response.taskId);
    } catch (error) {
      console.error('Failed to start generation:', error);
    }
  };

  const handleConfigureClick = () => {
    setShowWarning(false);
    setPendingRequest(null);
    // Scroll to ID3 config section and retrigger highlight
    const el = document.querySelector('[data-id3-config]');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightKey((k) => k + 1);
    }
  };

  const handleGenerateAnyway = () => {
    setShowWarning(false);
    if (pendingRequest) {
      doGenerate(pendingRequest);
      setPendingRequest(null);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <FileAudio className="h-8 w-8" />
          <h1 className="text-3xl font-bold tracking-tight">
            Generate Audiobook
          </h1>
        </div>
      </div>

      <div className="space-y-6">
        {/* ID3 Tag Configuration Card */}
        <div data-id3-config>
          <HighlightWrapper highlightKey={highlightKey}>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Tag className="h-4 w-4" />
                  Audiobook Metadata
                </CardTitle>
                <CardDescription>
                  ID3 tags embedded in the generated MP3 file
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Id3TagEditor
                  inputPath={project.inputPath}
                  screenplayName={project.screenplayName}
                  compact
                  idPrefix="gen-id3"
                />
              </CardContent>
            </Card>
          </HighlightWrapper>
        </div>

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
            projectName={displayTitle}
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

      {/* Missing ID3 Tags Warning Dialog */}
      <Dialog
        open={showWarning}
        onOpenChange={(open) => {
          if (!open) {
            setShowWarning(false);
            setPendingRequest(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Missing Audiobook Metadata
            </DialogTitle>
          </DialogHeader>

          <Alert variant="warning" className="border-amber-200 bg-amber-50">
            <AlertDescription className="text-amber-900">
              The following audiobook metadata fields are not set:{' '}
              <strong>{missingFields.join(', ')}</strong>
            </AlertDescription>
          </Alert>

          <DialogFooter>
            <button
              className={appButtonVariants({ variant: 'secondary' })}
              onClick={handleConfigureClick}
            >
              Configure
            </button>
            <button
              className={appButtonVariants({ variant: 'primary' })}
              onClick={handleGenerateAnyway}
            >
              Generate Anyway
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Wrapper that plays a green ring/shadow highlight animation each time
 * `highlightKey` changes. Uses `boxShadow` instead of `backgroundColor`
 * so the effect is visible even when children have opaque backgrounds.
 * A `key` prop on the motion.div forces React to remount and replay.
 */
function HighlightWrapper({
  highlightKey,
  children,
}: {
  highlightKey: number;
  children: React.ReactNode;
}) {
  // highlightKey === 0 means no highlight has been requested yet
  if (highlightKey === 0) {
    return <>{children}</>;
  }

  return (
    <motion.div
      key={highlightKey}
      initial={{ boxShadow: '0 0 0 0px rgba(34, 197, 94, 0)' }}
      animate={{
        boxShadow: [
          '0 0 0 0px rgba(34, 197, 94, 0)',
          '0 0 0 3px rgba(34, 197, 94, 0.5)',
          '0 0 0 0px rgba(34, 197, 94, 0)',
        ],
      }}
      transition={{
        duration: 2,
        times: [0, 0.3, 1],
        ease: 'easeInOut',
      }}
      className="rounded-xl"
    >
      {children}
    </motion.div>
  );
}
