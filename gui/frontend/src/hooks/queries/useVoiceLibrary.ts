import { useQuery, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { VoiceDetails, VoiceEntry } from '../../types';

/**
 * Query hook for fetching voice library providers
 */
export const useVoiceLibraryProviders = () => {
  return useQuery({
    queryKey: ['voiceLibrary', 'providers'],
    queryFn: async (): Promise<string[]> => {
      const response = await apiService.getVoiceLibraryProviders();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    staleTime: 1000 * 60 * 60 * 24, // 24 hours - rarely changes
    gcTime: 1000 * 60 * 60 * 2, // 2 hours in memory
  });
};

/**
 * Query hook for fetching voices for a specific provider
 * Voice library data is treated as relatively static
 */
export const useVoiceLibrary = (provider: string) => {
  return useQuery({
    queryKey: queryKeys.voiceLibrary(provider),
    queryFn: async (): Promise<VoiceEntry[]> => {
      const response = await apiService.getProviderVoices(provider);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!provider,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours - voice data rarely changes
    gcTime: 1000 * 60 * 60 * 2, // 2 hours in memory
    select: (data) => data, // Return data as-is since VoiceEntry already has the correct structure
  });
};

/**
 * Query hook for fetching voice details
 */
export const useVoiceDetails = (provider: string, stsId: string) => {
  return useQuery({
    queryKey: queryKeys.voiceDetails(provider, stsId),
    queryFn: async (): Promise<VoiceDetails> => {
      const response = await apiService.getVoiceDetails(provider, stsId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!provider && !!stsId,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours - voice details rarely change
  });
};

/**
 * Query hook for searching voices
 */
export const useVoiceSearch = (params: {
  query?: string;
  provider?: string;
  gender?: string;
  tags?: string[];
}) => {
  const hasSearchParams =
    params.query || params.provider || params.gender || params.tags?.length;

  return useQuery({
    queryKey: queryKeys.voiceSearch(params),
    queryFn: async (): Promise<VoiceEntry[]> => {
      const response = await apiService.searchVoices(params);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    enabled: !!hasSearchParams,
    staleTime: 1000 * 60 * 10, // 10 minutes for search results
  });
};

/**
 * Query hook for voice library statistics
 */
export const useVoiceLibraryStats = () => {
  return useQuery({
    queryKey: queryKeys.voiceLibraryStats,
    queryFn: async () => {
      const response = await apiService.getVoiceLibraryStats();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    staleTime: 1000 * 60 * 60, // 1 hour
  });
};

/**
 * Prefetch voice library data for better UX
 */
export const usePrefetchVoiceLibrary = () => {
  const queryClient = useQueryClient();

  return (provider: string) => {
    if (!provider) return;

    queryClient.prefetchQuery({
      queryKey: queryKeys.voiceLibrary(provider),
      queryFn: async () => {
        const response = await apiService.getProviderVoices(provider);
        if (response.error) throw new Error(response.error);
        return response.data!;
      },
      staleTime: 1000 * 60 * 60 * 24,
    });
  };
};
