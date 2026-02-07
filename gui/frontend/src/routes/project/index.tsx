import { createFileRoute } from '@tanstack/react-router';
import {
  FileAudio,
  FileText,
  Folder,
  Play,
  Search,
  Settings2,
  TestTube,
  Users,
} from 'lucide-react';
import { useEffect } from 'react';

import { Id3TagEditor } from '@/components/audiobook';
import { RouteError } from '@/components/errors';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { UniversalAudioPlayer } from '@/components/UniversalAudioPlayer';
import { useId3TagConfig } from '@/hooks/queries/useId3TagConfig';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { getProjectProgressStatus } from '@/lib/project-status';
import { apiService } from '@/services/api';
import { useAudioCommands, useAudioState } from '@/services/AudioService';
import { useProject } from '@/stores/appStore';
import type { RouteStaticData } from '@/types/route-metadata';

export const Route = createFileRoute('/project/')({
  component: ProjectOverview,
  errorComponent: RouteError,
  staticData: {
    title: 'Project Overview',
    icon: Folder,
    description: 'Overview dashboard for the current project',
    navigation: {
      order: 1,
      showInNav: true,
      label: 'Overview',
    },
    ui: {
      showPanel: false,
      showFooter: false,
    },
    helpText:
      'Get an overview of your project status and access different project tools.',
  } satisfies RouteStaticData,
});

function ProjectOverview() {
  // Use the store directly instead of route context
  const projectStore = useProject();
  const project =
    projectStore.mode === 'project' ? projectStore.project : undefined;

  // Use the project status hook directly
  const { status, error, isLoading } = useProjectStatus(
    project?.inputPath || ''
  );
  const progressStatus = status
    ? getProjectProgressStatus({
        hasJson: status.hasJson,
        hasVoiceConfig: status.hasVoiceConfig,
        speakerCount: status.speakerCount,
        voicesAssigned: status.voicesAssigned,
        hasOutputMp3: status.hasOutputMp3,
      })
    : null;

  // ID3 tag config for display title
  const { config: id3Config } = useId3TagConfig(project?.inputPath);
  const displayTitle = id3Config?.title || project?.screenplayName || '';

  // Don't render if no project (route guard will handle redirect)
  if (!project) {
    return null;
  }

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Project Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Project Overview</h1>
        <p className="text-muted-foreground">
          Managing project: <span className="font-medium">{displayTitle}</span>
        </p>
      </div>

      <Separator />

      {/* Project Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Folder className="h-5 w-5" />
            Project Status
            {progressStatus ? (
              <Badge
                variant="outline"
                className={progressStatus.badgeClassName}
              >
                {progressStatus.label}
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="border-slate-300 bg-slate-100 text-slate-600"
              >
                {error
                  ? 'Status Unavailable'
                  : isLoading
                    ? 'Loading…'
                    : 'Status Unknown'}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Current state and basic information about your project
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* ID3 Metadata — spans full width */}
            <div className="col-span-full">
              <Id3TagEditor
                inputPath={project.inputPath}
                screenplayName={project.screenplayName}
                idPrefix="overview-id3"
              />
            </div>
            <div>
              <div className="text-muted-foreground text-sm font-medium">
                Input Path
              </div>
              <p className="font-mono text-sm break-all">{project.inputPath}</p>
            </div>
            <div>
              <div className="text-muted-foreground text-sm font-medium">
                Output Path
              </div>
              <p className="font-mono text-sm break-all">
                {project.outputPath}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Generated Audiobook Card - shows when audio exists */}
      {status?.hasOutputMp3 && (
        <GeneratedAudioCard
          projectName={project.screenplayName}
          outputPath={project.outputPath}
        />
      )}

      {/* Project Tools Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Screenplay Info */}
        <ProjectToolCard
          title="Screenplay Info"
          description="View parsed screenplay details and statistics"
          icon={FileText}
          href="/project/screenplay"
          status="ready"
        />

        {/* Voice Casting */}
        <ProjectToolCard
          title="Voice Casting"
          description="Assign voices to characters in your screenplay"
          icon={Users}
          href="/project/voices"
          status="ready"
        />

        {/* Voice Testing */}
        <ProjectToolCard
          title="Voice Testing"
          description="Test character voices with sample dialogue"
          icon={TestTube}
          href="/project/test"
          status="ready"
        />

        {/* Text Processing */}
        <ProjectToolCard
          title="Text Processing"
          description="Configure dialogue processing and substitutions"
          icon={Settings2}
          href="/project/processing"
          status="disabled"
        />

        {/* Audio Generation */}
        <ProjectToolCard
          title="Audio Generation"
          description="Generate the complete audiobook"
          icon={Play}
          href="/project/generate"
          status="ready"
        />

        {/* Review Audio */}
        <ProjectToolCard
          title="Review Audio"
          description="Review and regenerate individual audio clips"
          icon={Search}
          href="/project/review"
          status="ready"
        />
      </div>
    </div>
  );
}

interface ProjectToolCardProps {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  status: 'ready' | 'disabled';
}

function ProjectToolCard({
  title,
  description,
  icon: Icon,
  href,
  status,
}: ProjectToolCardProps) {
  const isDisabled = status === 'disabled';

  return (
    <Card className={isDisabled ? 'opacity-60' : ''}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription className="text-sm">{description}</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        {isDisabled ? (
          <button
            className={
              appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              }) + ' w-full'
            }
            disabled={true}
          >
            Not Available Yet
          </button>
        ) : (
          <a
            href={`#${href}`}
            className={
              appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              }) + ' w-full'
            }
          >
            Open Tool
          </a>
        )}
      </CardContent>
    </Card>
  );
}

function GeneratedAudioCard({
  projectName,
  outputPath,
}: {
  projectName: string;
  outputPath: string;
}) {
  const { loadWithMetadata } = useAudioCommands();
  const { src } = useAudioState();

  // Construct audio URL for the output MP3
  const outputFilePath = `${outputPath}/${projectName}.mp3`;
  const audioUrl = apiService.getScreenplayDownloadFromPathUrl(
    outputFilePath,
    `${projectName}.mp3`
  );

  // Load audio when component mounts or URL changes
  useEffect(() => {
    if (audioUrl && audioUrl !== src) {
      loadWithMetadata(audioUrl, {
        primaryText: projectName,
        secondaryText: 'Generated Audiobook',
        downloadFilename: `${projectName}.mp3`,
      });
    }
  }, [audioUrl, loadWithMetadata, projectName, src]);

  return (
    <Card className="border-purple-200 bg-purple-50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileAudio className="h-5 w-5 text-purple-600" />
          Generated Audiobook
        </CardTitle>
        <CardDescription>
          Your audiobook is ready for playback and download
        </CardDescription>
      </CardHeader>
      <CardContent>
        <UniversalAudioPlayer />
      </CardContent>
    </Card>
  );
}
