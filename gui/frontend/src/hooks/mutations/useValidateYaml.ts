import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { ValidateYamlResponse } from '@/types/voice-casting';

interface ValidateYamlRequest {
  yamlContent: string;
  screenplayJsonPath: string;
}

export function useValidateYaml() {
  return useMutation<ValidateYamlResponse, Error, ValidateYamlRequest>({
    mutationFn: async ({ yamlContent, screenplayJsonPath }) => {
      const response = await apiService.validateYaml({
        yaml_content: yamlContent,
        screenplay_json_path: screenplayJsonPath,
      });

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    },
  });
}
