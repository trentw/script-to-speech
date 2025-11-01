import { CalendarIcon, FileTextIcon, FolderIcon } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { interactiveCardVariants } from '@/components/ui/interactive.variants';
import { Skeleton } from '@/components/ui/skeleton';
import { getProjectProgressStatus } from '@/lib/project-status';
import { cn } from '@/lib/utils';

interface ProjectMeta {
  name: string;
  input_path: string;
  output_path: string;
  has_json: boolean;
  has_voice_config: boolean;
  last_modified: string;
}

interface ProjectPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectSelect: (project: ProjectMeta) => void;
  className?: string;
}

export function ProjectPicker({
  isOpen,
  onClose,
  onProjectSelect,
  className,
}: ProjectPickerProps) {
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<ProjectMeta | null>(
    null
  );

  // Fetch projects when dialog opens
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen]);

  const fetchProjects = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/projects/discover?limit=20');
      const result = await response.json();

      if (!result.ok) {
        throw new Error(result.error || 'Failed to fetch projects');
      }

      setProjects(result.data || []);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProjectClick = (project: ProjectMeta) => {
    setSelectedProject(project);
  };

  const handleSelectProject = () => {
    if (selectedProject) {
      onProjectSelect(selectedProject);
      onClose();
    }
  };

  const formatLastModified = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  const formatProjectPath = (path: string) => {
    if (!path) {
      return '';
    }

    const normalized = path.replace(/\\/g, '/');
    const pathMarkers = ['/input/', '/output/'];

    for (const marker of pathMarkers) {
      const markerIndex = normalized.indexOf(marker);

      if (markerIndex !== -1) {
        return normalized.slice(markerIndex + 1);
      }
    }

    return normalized.startsWith('/') ? normalized.slice(1) : normalized;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className={cn(
          'border bg-white p-0 shadow-lg sm:max-w-3xl [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6',
          className
        )}
      >
        <div className="space-y-6 p-6">
          <DialogHeader className="space-y-2">
            <DialogTitle>Select Project</DialogTitle>
            <DialogDescription>
              Choose an existing project to open. Projects are discovered from
              your input directory.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Loading State */}
            {isLoading && (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-4">
                        <Skeleton className="h-10 w-10 rounded" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-4 w-1/3" />
                          <Skeleton className="h-3 w-2/3" />
                        </div>
                        <Skeleton className="h-6 w-20" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Error State */}
            {error && !isLoading && (
              <Alert variant="destructive">
                <AlertDescription>
                  {error}
                  <Button
                    variant="link"
                    size="sm"
                    onClick={fetchProjects}
                    className="ml-2"
                  >
                    Retry
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Empty State */}
            {!isLoading && !error && projects.length === 0 && (
              <div className="py-8 text-center">
                <FolderIcon className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
                <h3 className="mb-2 text-lg font-medium">No Projects Found</h3>
                <p className="text-muted-foreground mb-4">
                  No existing projects were found in your input directory.
                </p>
                <Button onClick={onClose} variant="outline">
                  Create New Project Instead
                </Button>
              </div>
            )}

            {/* Projects List */}
            {!isLoading && !error && projects.length > 0 && (
              <div className="max-h-96 space-y-2 overflow-y-auto">
                {projects.map((project) => {
                  const progressStatus = getProjectProgressStatus({
                    hasJson: project.has_json,
                    hasVoiceConfig: project.has_voice_config,
                  });
                  const isSelected =
                    selectedProject?.input_path === project.input_path;

                  return (
                    <Card
                      key={project.input_path}
                      className={cn(
                        'cursor-pointer py-0 transition-colors',
                        interactiveCardVariants({
                          variant: 'action',
                          state: 'idle',
                        }),
                        isSelected &&
                          'bg-accent border-2 border-gray-900 shadow-sm dark:border-gray-100'
                      )}
                      onClick={() => handleProjectClick(project)}
                    >
                      <CardContent className="p-4">
                        <div className="flex gap-4">
                          <div className="flex-shrink-0">
                            <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded">
                              <FileTextIcon className="text-primary h-5 w-5" />
                            </div>
                          </div>

                          <div className="min-w-0 flex-1 space-y-3">
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div className="min-w-0 space-y-1">
                                <h4 className="truncate font-medium">
                                  {project.name}
                                </h4>
                                <div className="text-muted-foreground flex items-center gap-2 text-sm">
                                  <CalendarIcon className="h-3 w-3" />
                                  <span>
                                    {formatLastModified(project.last_modified)}
                                  </span>
                                </div>
                              </div>

                              <Badge
                                variant="outline"
                                className={progressStatus.badgeClassName}
                              >
                                {progressStatus.label}
                              </Badge>
                            </div>

                            <p
                              className="text-muted-foreground text-xs leading-relaxed break-all"
                              title={project.input_path}
                            >
                              {formatProjectPath(project.input_path)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Action Buttons */}
            {!isLoading && !error && projects.length > 0 && (
              <div className="border-t pt-4">
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    className={appButtonVariants({
                      variant: 'secondary',
                      size: 'default',
                    })}
                    onClick={onClose}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className={appButtonVariants({
                      variant: 'primary',
                      size: 'default',
                    })}
                    onClick={handleSelectProject}
                    disabled={!selectedProject}
                  >
                    Open Project
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
