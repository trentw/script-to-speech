import { CheckIcon, ClockIcon, FolderIcon } from 'lucide-react';
import React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface RecentProjectsListProps {
  projects: string[];
  onProjectSelect: (inputPath: string) => void;
  currentProject?: string;
  className?: string;
}

export function RecentProjectsList({
  projects,
  onProjectSelect,
  currentProject,
  className,
}: RecentProjectsListProps) {
  // Extract project name from input path
  const getProjectName = (inputPath: string): string => {
    if (!inputPath || typeof inputPath !== 'string') {
      return 'Unknown Project';
    }
    const pathParts = inputPath.split('/');
    return pathParts[pathParts.length - 1] || 'Unknown Project';
  };

  // Format the last modified time (placeholder - would need real data from backend)
  const getRelativeTime = (inputPath: string): string => {
    // This is a placeholder - in a real implementation, you'd get this from the backend
    // For now, we'll show generic relative times
    const index = projects.indexOf(inputPath);
    const labels = [
      'Just now',
      '2 hours ago',
      'Yesterday',
      '3 days ago',
      '1 week ago',
    ];
    return labels[index] || `${index + 1} days ago`;
  };

  if (projects.length === 0) {
    return (
      <Card className={cn('p-4 text-center', className)}>
        <ClockIcon className="text-muted-foreground mx-auto mb-2 h-8 w-8" />
        <p className="text-muted-foreground text-sm">No recent projects</p>
        <p className="text-muted-foreground mt-1 text-xs">
          Create or open a project to see it here
        </p>
      </Card>
    );
  }

  return (
    <Card className={cn('recent-projects-list', className)}>
      <div className="border-b p-3">
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <ClockIcon className="h-4 w-4" />
          Recent Projects
        </h3>
      </div>

      <ScrollArea className="max-h-60">
        <div className="p-1">
          {projects.filter(Boolean).map((inputPath, _index) => {
            const projectName = getProjectName(inputPath);
            const isCurrentProject = inputPath === currentProject;
            const relativeTime = getRelativeTime(inputPath);

            return (
              <Button
                key={inputPath}
                variant="ghost"
                onClick={() => onProjectSelect(inputPath)}
                disabled={isCurrentProject}
                className={cn(
                  'mb-1 h-auto w-full justify-start p-3',
                  'text-left whitespace-normal',
                  isCurrentProject &&
                    'bg-accent text-accent-foreground cursor-default'
                )}
              >
                <div className="flex w-full items-start gap-3">
                  {/* Project Icon */}
                  <div className="mt-0.5 flex-shrink-0">
                    {isCurrentProject ? (
                      <CheckIcon className="h-4 w-4 text-green-600" />
                    ) : (
                      <FolderIcon className="text-muted-foreground h-4 w-4" />
                    )}
                  </div>

                  {/* Project Info */}
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <p className="truncate text-sm font-medium">
                        {projectName}
                      </p>
                      {isCurrentProject && (
                        <Badge variant="secondary" className="text-xs">
                          Current
                        </Badge>
                      )}
                    </div>

                    <p className="text-muted-foreground truncate text-xs">
                      {inputPath}
                    </p>

                    <p className="text-muted-foreground mt-1 text-xs">
                      {relativeTime}
                    </p>
                  </div>
                </div>
              </Button>
            );
          })}
        </div>
      </ScrollArea>

      {projects.length >= 10 && (
        <div className="bg-muted/30 border-t p-2">
          <p className="text-muted-foreground text-center text-xs">
            Showing 10 most recent projects
          </p>
        </div>
      )}
    </Card>
  );
}
