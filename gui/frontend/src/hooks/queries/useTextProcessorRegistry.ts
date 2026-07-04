import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { textProcessorApi } from '../../services/textProcessorApi';

/**
 * Hook for fetching the text processor registry (available processors,
 * their config schemas, and chunk type/field metadata).
 *
 * The registry is static for the lifetime of the backend process.
 */
export const useTextProcessorRegistry = () => {
  return useQuery({
    queryKey: queryKeys.textProcessorRegistry,
    queryFn: () => textProcessorApi.getRegistry(),
    staleTime: Infinity,
    gcTime: Infinity,
  });
};
