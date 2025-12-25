import { Link } from '@tanstack/react-router';
import { AlertCircle, FolderX, RefreshCw } from 'lucide-react';
import React from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useProject } from '@/stores/appStore';
import type { ProjectStatus } from '@/types/project';

interface ProjectErrorStatesProps {
  status: ProjectStatus | null;
  error: Error | null;
  onRetry?: () => void;
  onReparse?: () => void;
  className?: string;
}

export function ProjectErrorStates({
  status,
  error,
  onRetry,
  onReparse,
  className,
}: ProjectErrorStatesProps) {
  const { setMode } = useProject();

  // Handle missing project error (project folder deleted externally)
  if (
    error?.message?.includes('not found') ||
    error?.message?.includes('Project not found')
  ) {
    return (
      <Alert variant="destructive" className={cn(className)}>
        <FolderX className="h-4 w-4" />
        <AlertTitle>Project Not Found</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>
            The project folder no longer exists. It may have been moved or
            deleted externally.
          </p>
          <div className="flex gap-2">
            {onRetry && (
              <Button variant="outline" size="sm" onClick={onRetry}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            )}
            <Button
              variant="link"
              size="sm"
              onClick={() => {
                setMode('manual');
              }}
              asChild
            >
              <Link to="/">Return to Project Selector</Link>
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    );
  }

  // Handle general network/API errors
  if (error) {
    return (
      <Alert variant="destructive" className={cn(className)}>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Connection Error</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>Failed to load project status: {error.message}</p>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  if (!status) {
    return null;
  }

  // Show error states for corrupt files
  const hasErrors = status.jsonError || status.voiceConfigError;

  if (!hasErrors) {
    return null;
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Corrupted JSON Error */}
      {status.jsonError && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Screenplay JSON Issue</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>The parsed screenplay file appears to be corrupted:</p>
            <p className="bg-muted rounded p-2 font-mono text-sm">
              {status.jsonError}
            </p>
            <div className="flex gap-2">
              {onReparse && (
                <Button variant="outline" size="sm" onClick={onReparse}>
                  Re-parse Screenplay
                </Button>
              )}
              <Button variant="link" size="sm" asChild>
                <Link to="/project/screenplay">View Details</Link>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Corrupted Voice Config Error */}
      {status.voiceConfigError && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Voice Configuration Issue</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>The voice configuration file appears to be corrupted:</p>
            <p className="bg-muted rounded p-2 font-mono text-sm">
              {status.voiceConfigError}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link to="/project/voices">Fix Configuration</Link>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
