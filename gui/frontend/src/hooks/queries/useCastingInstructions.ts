import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';

export interface CastingInstruction {
  id: string;
  text: string;
  enabled: boolean;
}

export interface CastingInstructionsData {
  overall: CastingInstruction[];
  provider_instructions: Record<string, CastingInstruction[]>;
}

/**
 * Generate deterministic IDs from scope + index so that refetches
 * produce identical React keys and don't cause list remounts.
 */
function addIds(
  items: Array<{ text: string; enabled: boolean }>,
  scope: string
): CastingInstruction[] {
  return items.map((item, index) => ({
    id: `${scope}-${index}`,
    text: item.text,
    enabled: item.enabled,
  }));
}

export function useCastingInstructions() {
  return useQuery<CastingInstructionsData>({
    queryKey: ['casting-instructions'],
    queryFn: async () => {
      const response = await apiService.getCastingInstructions();
      if (response.error) {
        throw new Error(response.error);
      }
      const data = response.data!;
      const result: CastingInstructionsData = {
        overall: addIds(data.overall || [], 'overall'),
        provider_instructions: {},
      };
      for (const [provider, items] of Object.entries(
        data.provider_instructions || {}
      )) {
        result.provider_instructions[provider] = addIds(items, provider);
      }
      return result;
    },
    staleTime: Infinity,
  });
}
