import {
  FileTextIcon,
  FolderOpenIcon,
  MousePointerClickIcon,
} from 'lucide-react';
import React, { useRef, useState } from 'react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
  projectApi,
  type ProjectMeta as ApiProjectMeta,
} from '@/services/projectApi';
import { useProject } from '@/stores/appStore';
import type { ProjectMetaStore as ProjectMeta } from '@/types/project';

import { ProjectPicker } from './ProjectPicker';

interface ModeSelectorProps {
  className?: string;
  onProjectSelect?: (project: ProjectMeta) => void;
  onError?: (error: string) => void;
}

export function ModeSelector({
  className,
  onProjectSelect,
  onError,
}: ModeSelectorProps) {
  const projectState = useProject();
  const [isLoading, setIsLoading] = useState(false);
  const [showProjectPicker, setShowProjectPicker] = useState(false);

  // File input refs for new project only
  const newProjectFileRef = useRef<HTMLInputElement>(null);

  // Get current display value
  const getCurrentDisplayValue = () => {
    if (projectState.mode === 'project') {
      return `Project: ${projectState.project.screenplayName}`;
    }
    return 'Manual Mode';
  };

  // Handle mode selection from dropdown
  const handleModeSelect = (value: string) => {
    switch (value) {
      case 'manual':
        projectState.setMode('manual');
        break;
      case 'new-project':
        newProjectFileRef.current?.click();
        break;
      case 'open-project':
        setShowProjectPicker(true);
        break;
      default:
        break;
    }
  };

  // Handle new project file selection
  const handleNewProjectFile = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsLoading(true);

      // Validate file type
      if (!file.name.match(/\.(pdf|txt)$/i)) {
        throw new Error('Please select a PDF or TXT file');
      }

      // Use the project API service
      const projectData = await projectApi.createProjectFromFile(file);

      // Update store and notify parent
      const projectMeta: ProjectMeta = {
        screenplayName: projectData.screenplayName,
        inputPath: projectData.inputPath,
        outputPath: projectData.outputPath,
      };

      projectState.setProject(projectMeta);
      projectState.addRecentProject(projectData.inputPath);
      onProjectSelect?.(projectMeta);

      toast.success(
        `Project "${projectData.screenplayName}" created successfully!`
      );
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred';
      onError?.(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
      // Reset file input
      if (newProjectFileRef.current) {
        newProjectFileRef.current.value = '';
      }
    }
  };

  // Handle project selection from ProjectPicker
  const handleProjectPickerSelect = (apiProject: ApiProjectMeta) => {
    const projectMeta: ProjectMeta = {
      screenplayName: apiProject.name,
      inputPath: apiProject.input_path,
      outputPath: apiProject.output_path,
    };

    projectState.setProject(projectMeta);
    projectState.addRecentProject(projectMeta.inputPath);
    onProjectSelect?.(projectMeta);

    toast.success(`Opened project "${apiProject.name}"`);
  };

  return (
    <div className={cn('mode-selector space-y-2', className)}>
      <Select onValueChange={handleModeSelect} disabled={isLoading}>
        <SelectTrigger className="w-full justify-between">
          <SelectValue placeholder={getCurrentDisplayValue()} />
          {isLoading && (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
          )}
        </SelectTrigger>
        <SelectContent className="bg-white">
          {/* Manual Mode */}
          <SelectItem value="manual">
            <div className="flex items-center gap-2">
              <MousePointerClickIcon className="h-4 w-4" />
              <span>Manual Mode</span>
            </div>
          </SelectItem>

          <Separator />

          {/* Project Actions */}
          <SelectItem value="new-project">
            <div className="flex items-center gap-2">
              <FileTextIcon className="h-4 w-4" />
              <span>New Project</span>
              <Badge variant="secondary" className="ml-auto">
                PDF/TXT
              </Badge>
            </div>
          </SelectItem>

          <SelectItem value="open-project">
            <div className="flex items-center gap-2">
              <FolderOpenIcon className="h-4 w-4" />
              <span>Open Project</span>
            </div>
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Hidden file input for new project */}
      <input
        ref={newProjectFileRef}
        type="file"
        accept=".pdf,.txt"
        onChange={handleNewProjectFile}
        style={{ display: 'none' }}
        aria-label="Select screenplay file for new project"
      />

      {/* Project Picker Dialog */}
      <ProjectPicker
        isOpen={showProjectPicker}
        onClose={() => setShowProjectPicker(false)}
        onProjectSelect={handleProjectPickerSelect}
      />
    </div>
  );
}
