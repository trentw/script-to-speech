import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type {
  CharacterInfo,
  GenerateYamlResponse,
  VoiceAssignment,
} from '@/types/voice-casting';

interface GenerateYamlRequest {
  assignments: VoiceAssignment[];
  characterInfo: CharacterInfo[];
  includeComments?: boolean;
}

export function useGenerateYaml() {
  return useMutation<GenerateYamlResponse, Error, GenerateYamlRequest>({
    mutationFn: async (data) => {
      const response = await apiService.generateYaml({
        assignments: data.assignments,
        character_info: data.characterInfo,
        include_comments: data.includeComments ?? true,
      });

      if (response.error) {
        // Handle error properly - response.error might be an object
        const errorMessage =
          typeof response.error === 'string'
            ? response.error
            : JSON.stringify(response.error);
        throw new Error(errorMessage);
      }

      return response.data!;
    },
  });
}
