import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ProviderInfo } from '../../types';

/**
 * Query hook for fetching provider metadata including required and optional fields
 * This is used for dynamic form generation in custom voice configuration
 */
export const useProviderMetadata = (provider: string | undefined) => {
  return useQuery({
    queryKey: queryKeys.providerInfo(provider || ''),
    queryFn: async (): Promise<ProviderInfo> => {
      if (!provider) {
        throw new Error('Provider is required');
      }
      const response = await apiService.getProviderInfo(provider);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!provider,
    staleTime: 1000 * 60 * 10, // 10 minutes - provider metadata rarely changes
    gcTime: 1000 * 60 * 30, // Keep in cache for 30 minutes
  });
};
