import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { projectApi } from '../../services/projectApi';
import type { CreateProjectResponse } from '../../types/project';

/**
 * Mutation hook for creating new projects from uploaded files
 *
 * Features:
 * - Invalidates discovery cache after success
 * - Pre-populates project status cache with initial data
 * - Provides loading states and error handling
 * - Optimistic updates for better UX
 * - Returns header/footer detection results for popover display
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File): Promise<CreateProjectResponse> => {
      const projectData = await projectApi.createProjectFromFile(file);
      return {
        inputPath: projectData.inputPath,
        outputPath: projectData.outputPath,
        screenplayName: projectData.screenplayName,
        autoRemovedPatterns: projectData.autoRemovedPatterns,
        suggestedPatterns: projectData.suggestedPatterns,
      };
    },

    onSuccess: (data) => {
      // Invalidate discovery cache to show new project
      queryClient.invalidateQueries({
        queryKey: queryKeys.projectsDiscover(),
      });

      // Pre-populate project status cache with initial optimistic data
      // This prevents unnecessary immediate refetch when navigating to project
      queryClient.setQueryData(queryKeys.projectStatus(data.inputPath), {
        hasPdf: true,
        hasJson: true,
        hasVoiceConfig: false,
        hasOptionalConfig: false,
        hasOutputMp3: false,
        screenplayParsed: true,
        voicesCast: false,
        audioGenerated: false,
        // Note: speakerCount, dialogueChunks will be filled by real data on first fetch
      });

      console.log('Project created successfully:', data.screenplayName);
    },

    onError: (error) => {
      console.error('Project creation failed:', error);
    },
  });
};
