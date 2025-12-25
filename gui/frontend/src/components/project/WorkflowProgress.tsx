import { Link } from '@tanstack/react-router';
import { CheckCircle, Circle, PlayCircle, Settings } from 'lucide-react';
import React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ProjectStatus } from '@/types/project';

interface WorkflowProgressProps {
  status: ProjectStatus | null;
  isLoading?: boolean;
  onParseScreenplay?: () => void;
  className?: string;
}

interface WorkflowStep {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  isComplete: (status: ProjectStatus) => boolean;
  getSubLabel?: (status: ProjectStatus) => string | undefined;
  isEnabled: (status: ProjectStatus) => boolean;
  actionButton?: {
    label: string;
    route?: string;
    action?: () => void;
    variant?: 'default' | 'ghost' | 'outline';
  };
  comingSoon?: boolean;
}

export function WorkflowProgress({
  status,
  isLoading = false,
  onParseScreenplay,
  className,
}: WorkflowProgressProps) {
  // Define workflow steps
  const workflowSteps: WorkflowStep[] = [
    {
      id: 'parse',
      label: 'Parse Screenplay',
      icon: Circle,
      isComplete: (status) => status.hasJson,
      getSubLabel: (status) =>
        status.dialogueChunks ? `${status.dialogueChunks} chunks` : undefined,
      isEnabled: () => true,
      actionButton: status?.hasJson
        ? {
            label: 'View Details',
            route: '/project/screenplay',
            variant: 'ghost',
          }
        : { label: 'Parse Now', action: onParseScreenplay, variant: 'default' },
    },
    {
      id: 'voices',
      label: 'Cast Voices',
      icon: Settings,
      isComplete: (status) => status.voicesCast,
      getSubLabel: (status) =>
        status.voicesAssigned && status.speakerCount
          ? `${status.voicesAssigned}/${status.speakerCount} speakers`
          : undefined,
      isEnabled: (status) => status.hasJson,
      actionButton: status?.voicesCast
        ? { label: 'Edit Casting', route: '/project/voices', variant: 'ghost' }
        : {
            label: 'Cast Voices',
            route: '/project/voices',
            variant: 'default',
          },
    },
    {
      id: 'generate',
      label: 'Generate Audio',
      icon: PlayCircle,
      isComplete: (status) => status.audioGenerated,
      isEnabled: (status) => status.voicesCast,
      comingSoon: true,
      actionButton: {
        label: 'Generate',
        variant: 'ghost',
      },
    },
  ];

  if (!status && !isLoading) {
    return (
      <div className={cn('text-muted-foreground p-6 text-center', className)}>
        No project loaded
      </div>
    );
  }

  return (
    <div className={cn('workflow-progress space-y-3', className)}>
      {workflowSteps.map((step) => {
        const isComplete = status ? step.isComplete(status) : false;
        const isEnabled = status ? step.isEnabled(status) : false;
        const subLabel = status ? step.getSubLabel?.(status) : undefined;
        const IconComponent = isComplete ? CheckCircle : step.icon;

        return (
          <div
            key={step.id}
            className={cn(
              'flex items-center justify-between rounded-lg border p-3',
              isComplete &&
                'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20',
              !isEnabled && 'opacity-50',
              step.comingSoon && 'opacity-60'
            )}
          >
            <div className="flex items-center gap-3">
              <IconComponent
                className={cn(
                  'h-5 w-5',
                  isComplete
                    ? 'text-green-600 dark:text-green-400'
                    : isEnabled
                      ? 'text-muted-foreground'
                      : 'text-muted-foreground/50'
                )}
              />
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'font-medium',
                      isComplete && 'text-green-700 dark:text-green-300',
                      !isEnabled && 'text-muted-foreground'
                    )}
                  >
                    {step.label}
                  </span>
                  {step.comingSoon && (
                    <Badge variant="secondary" className="text-xs">
                      Coming Soon
                    </Badge>
                  )}
                </div>
                {subLabel && (
                  <p className="text-muted-foreground mt-1 text-sm">
                    {subLabel}
                  </p>
                )}
              </div>
            </div>

            {/* Action Button */}
            {step.actionButton && !step.comingSoon && (
              <div>
                {step.actionButton.route ? (
                  <Button
                    variant={step.actionButton.variant || 'default'}
                    size="sm"
                    disabled={!isEnabled || isLoading}
                    asChild
                  >
                    <Link to={step.actionButton.route}>
                      {step.actionButton.label}
                    </Link>
                  </Button>
                ) : (
                  <Button
                    variant={step.actionButton.variant || 'default'}
                    size="sm"
                    disabled={!isEnabled || isLoading}
                    onClick={step.actionButton.action}
                  >
                    {step.actionButton.label}
                  </Button>
                )}
              </div>
            )}

            {/* Coming Soon Disabled Button */}
            {step.comingSoon && (
              <Button variant="ghost" size="sm" disabled>
                {step.actionButton?.label || 'Coming Soon'}
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
