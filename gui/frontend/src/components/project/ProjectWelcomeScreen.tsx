import { useNavigate } from '@tanstack/react-router';
import { FolderOpen, Plus } from 'lucide-react';
import React, { useRef, useState } from 'react';
import { toast } from 'sonner';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  projectApi,
  type ProjectMeta as ApiProjectMeta,
} from '@/services/projectApi';
import { useProject, useUploadDialog } from '@/stores/appStore';
import type { ProjectMetaStore as ProjectMeta } from '@/types/project';

import { ProjectPicker } from './ProjectPicker';

export function ProjectWelcomeScreen() {
  const navigate = useNavigate();
  const { setProject, addRecentProject, recentProjects } = useProject();
  const { setUploadDialog } = useUploadDialog();
  const [isLoading, setIsLoading] = useState(false);
  const [showProjectPicker, setShowProjectPicker] = useState(false);

  // File input ref for new project
  const newProjectFileRef = useRef<HTMLInputElement>(null);

  // Handle new project button click
  const handleNewProject = () => {
    newProjectFileRef.current?.click();
  };

  // Handle open project button click
  const handleOpenProject = () => {
    setShowProjectPicker(true);
  };

  // Handle new project file selection - uses global upload dialog
  const handleNewProjectFile = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.match(/\.(pdf|txt)$/i)) {
      toast.error('Please select a PDF or TXT file');
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

    setProject(projectMeta);
    addRecentProject(projectMeta.inputPath);

    toast.success(`Opened project "${apiProject.name}"`);

    // Navigate to project overview
    navigate({ to: '/project' });
  };

  // Handle opening a recent project
  const handleOpenRecent = async (inputPath: string) => {
    try {
      setIsLoading(true);

      // Fetch project metadata from backend
      const projects = await projectApi.discoverProjects();
      const apiProject = projects.find((p) => p.input_path === inputPath);

      if (!apiProject) {
        throw new Error('Project not found');
      }

      handleProjectPickerSelect(apiProject);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to open recent project';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">Script to Speech</CardTitle>
          <CardDescription className="mt-4 text-base">
            Transform screenplay PDFs into professional multi-voiced audiobooks.
            Parse your script, cast voices from multiple TTS providers, and
            generate studio-quality audio with intelligent character detection.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Action Buttons */}
          <div className="flex justify-center gap-4">
            <button
              onClick={handleNewProject}
              disabled={isLoading}
              className={appButtonVariants({ variant: 'primary', size: 'lg' })}
              aria-label="Create new project from screenplay file"
            >
              <Plus className="mr-2 h-5 w-5" />
              New Project
            </button>

            <button
              onClick={handleOpenProject}
              disabled={isLoading}
              className={appButtonVariants({
                variant: 'secondary',
                size: 'lg',
              })}
              aria-label="Open existing project"
            >
              <FolderOpen className="mr-2 h-5 w-5" />
              Open Project
            </button>
          </div>

          {/* Loading Indicator */}
          {isLoading && (
            <div className="text-muted-foreground flex items-center justify-center gap-2 text-sm">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
              <span>Loading...</span>
            </div>
          )}

          {/* Recent Projects */}
          {!isLoading && recentProjects.length > 0 && (
            <div className="mt-6 border-t pt-6">
              <h3 className="mb-3 text-sm font-medium">Recent Projects</h3>
              <div className="space-y-2">
                {recentProjects.map((path) => (
                  <button
                    key={path}
                    onClick={() => handleOpenRecent(path)}
                    className="w-full rounded px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100"
                    aria-label={`Open recent project: ${path}`}
                  >
                    <div className="flex items-center gap-2">
                      <FolderOpen className="text-muted-foreground h-4 w-4" />
                      <span className="truncate">{path}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

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

      {/* Upload Progress Dialog is now rendered globally in __root.tsx */}
    </div>
  );
}
