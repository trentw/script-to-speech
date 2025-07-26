import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api'
import type { ParseYamlResponse } from '@/types/voice-casting'

interface ParseYamlRequest {
  yamlContent: string
}

export function useParseYaml() {
  return useMutation<ParseYamlResponse, Error, ParseYamlRequest>({
    mutationFn: async (data) => {
      const response = await apiService.parseYaml(data.yamlContent)
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      return response.data!
    },
  })
}