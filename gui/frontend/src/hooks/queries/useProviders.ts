import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ProviderInfo } from '../../types';

/**
 * Query hook for fetching TTS providers information
 * Uses moderate refresh rate as provider configuration can change
 */
export const useProviders = () => {
  return useQuery({
    queryKey: queryKeys.providersInfo,
    queryFn: async (): Promise<ProviderInfo[]> => {
      const response = await apiService.getProvidersInfo();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchOnWindowFocus: true, // Critical for provider availability
  });
};

/**
 * Query hook for fetching basic provider list
 */
export const useProvidersList = () => {
  return useQuery({
    queryKey: queryKeys.providers,
    queryFn: async (): Promise<string[]> => {
      const response = await apiService.getProviders();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

/**
 * Query hook for fetching specific provider information
 */
export const useProviderInfo = (provider: string) => {
  return useQuery({
    queryKey: queryKeys.providerInfo(provider),
    queryFn: async (): Promise<ProviderInfo> => {
      const response = await apiService.getProviderInfo(provider);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!provider,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

/**
 * Prefetch providers data for better UX
 */
export const usePrefetchProviders = () => {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.providersInfo,
      queryFn: async () => {
        const response = await apiService.getProvidersInfo();
        if (response.error) throw new Error(response.error);
        return response.data!;
      },
      staleTime: 1000 * 60 * 5,
    });
  };
};
