import { createFileRoute } from '@tanstack/react-router';
import {
  FileText,
  Folder,
  Play,
  Settings2,
  TestTube,
  Users,
} from 'lucide-react';

import { RouteError } from '@/components/errors';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { getProjectProgressStatus } from '@/lib/project-status';
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
      })
    : null;

  // Safety check - this should not happen if route layout is working correctly
  if (!project) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading project data...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Project Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Project Overview</h1>
        <p className="text-muted-foreground">
          Managing project:{' '}
          <span className="font-medium">{project.screenplayName}</span>
        </p>
      </div>

      <Separator />

      {/* Project Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Folder className="h-5 w-5" />
            Project Status
          </CardTitle>
          <CardDescription>
            Current state and basic information about your project
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <div className="text-muted-foreground text-sm font-medium">
                Screenplay Name
              </div>
              <p className="font-medium">{project.screenplayName}</p>
            </div>
            <div>
              <div className="text-muted-foreground text-sm font-medium">
                Status
              </div>
              <div className="flex items-center gap-2">
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
              </div>
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
          status="disabled"
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
    <Card
      className={`transition-colors ${isDisabled ? 'opacity-60' : 'hover:bg-accent/50'}`}
    >
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription className="text-sm">{description}</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <Button
          asChild={!isDisabled}
          variant="outline"
          className="w-full"
          disabled={isDisabled}
        >
          {isDisabled ? (
            <span>Not Available Yet</span>
          ) : (
            <a href={`#${href}`}>Open Tool</a>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
