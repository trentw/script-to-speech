import { FileTextIcon, FolderOpenIcon } from 'lucide-react';
import React, { useRef, useState } from 'react';
import { toast } from 'sonner';

import { appButtonVariants } from '@/components/ui/button-variants';
import { cn } from '@/lib/utils';
import {
  projectApi,
  type ProjectMeta as ApiProjectMeta,
} from '@/services/projectApi';
import { useProject, useUploadDialog } from '@/stores/appStore';
import type { ProjectMetaStore as ProjectMeta } from '@/types/project';

import { ProjectPicker } from './ProjectPicker';

interface ProjectControlsProps {
  className?: string;
  onProjectSelect?: (project: ProjectMeta) => void;
  onError?: (error: string) => void;
}

export function ProjectControls({
  className,
  onProjectSelect,
  onError,
}: ProjectControlsProps) {
  const projectState = useProject();
  const { setUploadDialog } = useUploadDialog();
  const isLoading = false;
  const [showProjectPicker, setShowProjectPicker] = useState(false);

  // File input ref for new project
  const newProjectFileRef = useRef<HTMLInputElement>(null);

  // Get current project name for display
  const projectName =
    projectState.mode === 'project' && projectState.project
      ? projectState.project.screenplayName
      : null;

  // Handle new project button click
  const handleNewProject = () => {
    newProjectFileRef.current?.click();
  };

  // Handle open project button click
  const handleOpenProject = () => {
    setShowProjectPicker(true);
  };

  // Handle new project file selection
  const handleNewProjectFile = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.match(/\.(pdf|txt)$/i)) {
      const errorMessage = 'Please select a PDF or TXT file';
      onError?.(errorMessage);
      toast.error(errorMessage);
      return;
    }

    try {
      // 1. Show "Parsing screenplay..." dialog immediately
      setUploadDialog({
        status: 'processing',
        filename: file.name,
        step: 'parsing',
      });

      // 2. Create project (includes parsing)
      const projectData = await projectApi.createProjectFromFile(file);

      // Create project meta but DON'T set it yet - wait for user to click OK
      const projectMeta: ProjectMeta = {
        screenplayName: projectData.screenplayName,
        inputPath: projectData.inputPath,
        outputPath: projectData.outputPath,
      };

      // 3. Update to "Checking for headers/footers..."
      setUploadDialog({
        status: 'processing',
        filename: file.name,
        step: 'detecting',
      });

      // 4. Fetch project status for stats
      const status = await projectApi.getProjectStatus(projectData.inputPath);
      const speakerCount = status.speakerCount ?? 0;
      const dialogueChunks = status.dialogueChunks ?? 0;

      // 5. Check for detection results and show final dialog
      const hasDetection =
        (projectData.autoRemovedPatterns?.length ?? 0) > 0 ||
        (projectData.suggestedPatterns?.length ?? 0) > 0;

      if (hasDetection) {
        setUploadDialog({
          status: 'detection',
          filename: file.name,
          speakerCount,
          dialogueChunks,
          autoRemoved: projectData.autoRemovedPatterns || [],
          suggested: projectData.suggestedPatterns || [],
          projectMeta,
        });
      } else {
        setUploadDialog({
          status: 'complete',
          filename: file.name,
          speakerCount,
          dialogueChunks,
          projectMeta,
        });
      }
    } catch (error) {
      setUploadDialog({ status: 'idle' });
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred';
      onError?.(errorMessage);
      toast.error(errorMessage);
    } finally {
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
    <div className={cn('project-controls space-y-2', className)}>
      {projectState.mode === 'manual' ? (
        /* Manual Mode Display */
        <>
          {/* Title */}
          <h1 className="text-lg font-bold tracking-tight">Script to Speech</h1>

          {/* Mode Display */}
          <div className="text-muted-foreground text-xs">Manual Mode</div>
        </>
      ) : (
        /* Project Mode Display */
        <>
          {/* Button Row */}
          <div className="flex gap-2">
            <button
              onClick={handleNewProject}
              disabled={isLoading}
              className={
                appButtonVariants({
                  variant: 'primary',
                  size: 'sm',
                }) + ' flex-1'
              }
              aria-label="Create new project from screenplay file"
            >
              <FileTextIcon className="h-4 w-4" />
              New
            </button>

            <button
              onClick={handleOpenProject}
              disabled={isLoading}
              className={
                appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                }) + ' flex-1'
              }
              aria-label="Open existing project"
            >
              <FolderOpenIcon className="h-4 w-4" />
              Open
            </button>
          </div>

          {/* Project Name Display */}
          <div className="text-muted-foreground text-xs">
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
                <span>Loading...</span>
              </div>
            ) : projectName ? (
              <span>
                Project: <span className="font-medium">{projectName}</span>
              </span>
            ) : (
              <span>No project loaded</span>
            )}
          </div>
        </>
      )}

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
