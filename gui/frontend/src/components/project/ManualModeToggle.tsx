import React from 'react';
import { toast } from 'sonner';

import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { projectApi } from '@/services/projectApi';
import { useProject } from '@/stores/appStore';
import type { ProjectMetaStore as ProjectMeta } from '@/types/project';

interface ManualModeToggleProps {
  className?: string;
}

export function ManualModeToggle({ className }: ManualModeToggleProps) {
  const projectState = useProject();
  const isManualMode = projectState.mode === 'manual';

  const handleToggle = async (checked: boolean) => {
    if (checked) {
      // Switching to manual mode
      projectState.setMode('manual');
    } else {
      // Trying to turn off manual mode - load the most recent project
      const recentProjects = projectState.recentProjects;

      if (recentProjects.length > 0) {
        // Load the most recent project
        const mostRecentPath = recentProjects[0];

        try {
          // Discover projects to find the one matching the recent path
          const projects = await projectApi.discoverProjects(50);
          const matchingProject = projects.find(
            (p) => p.input_path === mostRecentPath
          );

          if (matchingProject) {
            const projectMeta: ProjectMeta = {
              screenplayName: matchingProject.name,
              inputPath: matchingProject.input_path,
              outputPath: matchingProject.output_path,
            };

            projectState.setProject(projectMeta);
            toast.success(`Loaded project "${matchingProject.name}"`);
          } else {
            // Project not found, stay in manual mode
            toast.info(
              'Recent project not found. Use Open to select a project.'
            );
          }
        } catch (error) {
          console.error('Failed to load recent project:', error);
          toast.error('Failed to load recent project');
        }
      } else {
        // No recent projects, stay in manual mode
        toast.info('No recent projects. Use Open to select a project.');
      }
    }
  };

  return (
    <div className={cn('manual-mode-toggle space-y-2', className)}>
      {/* Toggle Row */}
      <div className="flex items-center justify-between gap-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <label
              htmlFor="manual-mode-switch"
              className="text-muted-foreground cursor-pointer text-sm font-medium"
            >
              Manual Mode
            </label>
          </TooltipTrigger>
          <TooltipContent side="right" sideOffset={8}>
            <p className="max-w-xs">
              Use screenplay tools in a one-off fashion, separate from a
              screenplay project
            </p>
          </TooltipContent>
        </Tooltip>

        <Switch
          id="manual-mode-switch"
          checked={isManualMode}
          onCheckedChange={handleToggle}
          aria-label="Toggle manual mode"
          className="border-2 shadow-sm data-[state=checked]:border-gray-900 data-[state=checked]:bg-gray-900 data-[state=unchecked]:border-gray-400 data-[state=unchecked]:bg-gray-200"
        />
      </div>

      {/* Status Text */}
      <div className="text-muted-foreground text-xs">
        {isManualMode ? 'Enabled' : 'Disabled'}
      </div>
    </div>
  );
}
