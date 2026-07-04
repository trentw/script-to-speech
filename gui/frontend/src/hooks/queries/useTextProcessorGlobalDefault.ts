import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { textProcessorApi } from '../../services/textProcessorApi';

/**
 * Hook for fetching the user's global default text processor config
 * (the workspace file that seeds newly parsed screenplays).
 */
export const useTextProcessorGlobalDefault = () => {
  return useQuery({
    queryKey: queryKeys.textProcessorGlobalDefault,
    queryFn: () => textProcessorApi.getGlobalDefault(),
    staleTime: 5000,
    refetchOnWindowFocus: true,
  });
};
