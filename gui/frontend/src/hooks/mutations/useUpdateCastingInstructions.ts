import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  CastingInstruction,
  CastingInstructionsData,
} from '@/hooks/queries/useCastingInstructions';
import { apiService } from '@/services/api';

function stripIds(items: CastingInstruction[]) {
  return items.map(({ text, enabled }) => ({ text, enabled }));
}

export function useUpdateCastingInstructions() {
  const queryClient = useQueryClient();

  return useMutation<CastingInstructionsData, Error, CastingInstructionsData>({
    mutationFn: async (data) => {
      const payload = {
        overall: stripIds(data.overall),
        provider_instructions: Object.fromEntries(
          Object.entries(data.provider_instructions).map(([k, v]) => [
            k,
            stripIds(v),
          ])
        ),
      };
      const response = await apiService.updateCastingInstructions(payload);
      if (response.error) {
        throw new Error(response.error);
      }
      // Return the optimistic data (ids are already present)
      return data;
    },
    onMutate: async (newData) => {
      await queryClient.cancelQueries({
        queryKey: ['casting-instructions'],
      });
      const previous = queryClient.getQueryData<CastingInstructionsData>([
        'casting-instructions',
      ]);
      queryClient.setQueryData(['casting-instructions'], newData);
      return { previous };
    },
    onError: (
      _err,
      _newData,
      context: { previous: CastingInstructionsData | undefined } | undefined
    ) => {
      if (context?.previous) {
        queryClient.setQueryData(['casting-instructions'], context.previous);
      }
    },
    // NOTE: onSettled invalidation is intentionally omitted. Unsaved "add"
    // rows live only in the query cache; a refetch would discard them because
    // the server doesn't know about them yet. With deterministic IDs and
    // staleTime: Infinity the cache is authoritative for this single-user
    // settings data, so skipping the refetch is safe.
  });
}
