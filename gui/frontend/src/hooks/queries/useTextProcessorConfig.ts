import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { textProcessorApi } from '../../services/textProcessorApi';
import type { TextProcessorConfig } from '../../types/text-processing';

/**
 * Hook for fetching a project's text processor config with CLI/GUI
 * interoperability.
 *
 * Mirrors useId3TagConfig: 5 second stale time and refetch on window focus
 * (critical for CLI/GUI interop — the user may edit the YAML file manually).
 */
export const useTextProcessorConfig = (inputPath: string | undefined) => {
  return useQuery({
    queryKey: queryKeys.textProcessorConfig(inputPath || ''),
    queryFn: async (): Promise<TextProcessorConfig | null> => {
      if (!inputPath) return null;
      return await textProcessorApi.getConfig(inputPath);
    },

    staleTime: 5000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    enabled: !!inputPath,
  });
};
