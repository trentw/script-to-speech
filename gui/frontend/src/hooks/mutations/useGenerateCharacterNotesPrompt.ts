import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api';

interface GenerateCharacterNotesPromptRequest {
  sessionId: string;
  yamlContent: string;
  customPromptPath?: string;
}

interface GenerateCharacterNotesPromptResponse {
  prompt_content: string;
  privacy_notice: string;
}

export function useGenerateCharacterNotesPrompt() {
  return useMutation<
    GenerateCharacterNotesPromptResponse,
    Error,
    GenerateCharacterNotesPromptRequest
  >({
    mutationFn: async (data) => {
      const response = await apiService.generateCharacterNotesPrompt({
        session_id: data.sessionId,
        yaml_content: data.yamlContent,
        custom_prompt_path: data.customPromptPath,
      });

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    },
  });
}
