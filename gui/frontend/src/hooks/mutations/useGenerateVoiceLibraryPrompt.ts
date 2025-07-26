import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api'

interface GenerateVoiceLibraryPromptRequest {
  yaml_content: string
  providers: string[]
  custom_prompt_path?: string
}

interface GenerateVoiceLibraryPromptResponse {
  prompt_content: string
  privacy_notice: string
}

export function useGenerateVoiceLibraryPrompt() {
  return useMutation<
    GenerateVoiceLibraryPromptResponse,
    Error,
    GenerateVoiceLibraryPromptRequest
  >({
    mutationFn: async (data) => {
      const response = await apiService.generateVoiceLibraryPrompt({
        yaml_content: data.yaml_content,
        providers: data.providers,
        custom_prompt_path: data.custom_prompt_path,
      })
      
      if (response.error) {
        // Handle error properly - response.error might be an object
        const errorMessage = typeof response.error === 'string' 
          ? response.error 
          : JSON.stringify(response.error);
        throw new Error(errorMessage)
      }
      
      return response.data!
    },
  })
}