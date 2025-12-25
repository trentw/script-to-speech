import { Link } from '@tanstack/react-router';
import { ArrowRight, Clock, FolderOpen, Settings } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { cn } from '@/lib/utils';
import { useProject } from '@/stores/appStore';
import type { ProjectStatus } from '@/types/project';

import { ProjectErrorStates } from './ProjectErrorStates';
import { WorkflowProgress } from './WorkflowProgress';

interface ProjectOverviewProps {
  className?: string;
}

export function ProjectOverview({ className }: ProjectOverviewProps) {
  const projectState = useProject();

  // Get inputPath before conditional logic
  const inputPath =
    projectState.mode === 'project'
      ? projectState.project.inputPath
      : undefined;

  const { status, isLoading, error, invalidate } = useProjectStatus(inputPath);

  // Note: Route guard is handled by parent ProjectLayout in routes/project/route.tsx
  // No need for redundant check here - TypeScript ensures project exists via discriminated union
  if (projectState.mode !== 'project') {
    return null; // Should never happen due to parent guard, but satisfies TypeScript
  }

  // Determine next step in workflow
  const getNextStep = (status: ProjectStatus | null) => {
    if (!status) return null;

    if (!status.hasJson) {
      return {
        route: '/project/screenplay',
        label: 'Parse Screenplay',
        description:
          'Convert your screenplay PDF into structured dialogue chunks',
      };
    }

    if (!status.voicesCast) {
      return {
        route: '/project/voices',
        label: 'Cast Voices',
        description: 'Assign TTS voices to each character in your screenplay',
      };
    }

    if (!status.audioGenerated) {
      return {
        route: '/project/generate',
        label: 'Generate Audio',
        description: 'Create the final audiobook with multi-voiced narration',
      };
    }

    return null;
  };

  const nextStep = getNextStep(status);

  // Handle parse screenplay action
  const handleParseScreenplay = async () => {
    try {
      // This would trigger screenplay parsing via the backend
      // For now, we'll navigate to the screenplay view
      console.log('Parse screenplay action triggered');
      // In a real implementation, this would call the backend to parse
    } catch (error) {
      console.error('Failed to parse screenplay:', error);
    }
  };

  // Handle reparse action for error recovery
  const handleReparse = async () => {
    try {
      await handleParseScreenplay();
      await invalidate(); // Refresh status after reparse
    } catch (error) {
      console.error('Failed to reparse screenplay:', error);
    }
  };

  // Format last modified time (placeholder implementation)
  const getLastModified = (): string => {
    // In a real implementation, this would come from the backend
    return 'Last updated 2 hours ago';
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Project Information Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                {projectState.project.screenplayName}
              </CardTitle>
              <p className="text-muted-foreground mt-1 text-sm">
                {projectState.project.inputPath}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={invalidate}
                disabled={isLoading}
              >
                Refresh
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/">
                  <Settings className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              {getLastModified()}
            </div>
            {status?.dialogueChunks && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <span>{status.dialogueChunks} dialogue chunks</span>
              </>
            )}
            {status?.speakerCount && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <span>{status.speakerCount} speakers</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error States */}
      <ProjectErrorStates
        status={status}
        error={error}
        onRetry={invalidate}
        onReparse={handleReparse}
      />

      {/* Workflow Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <WorkflowProgress
            status={status}
            isLoading={isLoading}
            onParseScreenplay={handleParseScreenplay}
          />
        </CardContent>
      </Card>

      {/* Continue Wizard Navigation */}
      {nextStep && (
        <Card className="border-primary bg-primary/5">
          <CardContent className="pt-6">
            <div className="space-y-3 text-center">
              <h3 className="text-lg font-semibold">Ready for Next Step</h3>
              <p className="text-muted-foreground text-sm">
                {nextStep.description}
              </p>
              <Button size="lg" className="w-full" asChild>
                <Link to={nextStep.route}>
                  Continue: {nextStep.label}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completion Status */}
      {status?.audioGenerated && (
        <Card className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20">
          <CardContent className="pt-6">
            <div className="space-y-3 text-center">
              <h3 className="text-lg font-semibold text-green-700 dark:text-green-300">
                Audiobook Complete!
              </h3>
              <p className="text-sm text-green-600 dark:text-green-400">
                Your screenplay has been successfully converted to an audiobook.
              </p>
              <div className="flex justify-center gap-2">
                <Button variant="outline" size="sm">
                  Download Audio
                </Button>
                <Button variant="outline" size="sm">
                  View Output Folder
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Button variant="outline" asChild>
              <Link to="/project/screenplay">View Screenplay Details</Link>
            </Button>
            <Button variant="outline" asChild disabled={!status?.hasJson}>
              <Link to="/project/voices">Voice Casting</Link>
            </Button>
            <Button variant="outline" asChild disabled={!status?.voicesCast}>
              <Link to="/project/test">Test Voices</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
