import { useQueries } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ProviderInfo, VoiceEntry } from '../../types';
import { useVoiceLibraryProviders } from './useVoiceLibrary';

/**
 * Hook to get voice counts for all providers dynamically
 * Uses a two-step approach:
 * 1. Get all providers (show all possible providers)
 * 2. Get voice-library-enabled providers (only query these for voice counts)
 * 3. Default to 0 voices for providers not in voice library
 */
export const useAllVoiceCounts = (providers: ProviderInfo[]) => {
  // Step 1: Get voice-library-enabled providers
  const {
    data: voiceLibraryProviders = [],
    isLoading: voiceLibraryProvidersLoading,
  } = useVoiceLibraryProviders();

  // Step 2: Only query voice counts for voice-library-enabled providers
  const voiceLibraryEnabledProviders = providers.filter((provider) =>
    voiceLibraryProviders.includes(provider.identifier)
  );

  const queries = useQueries({
    queries: voiceLibraryEnabledProviders.map((provider) => ({
      queryKey: queryKeys.voiceLibrary(provider.identifier),
      queryFn: async (): Promise<VoiceEntry[]> => {
        const response = await apiService.getProviderVoices(
          provider.identifier
        );
        if (response.error) {
          throw new Error(response.error);
        }
        return response.data!;
      },
      enabled: !!provider.identifier,
      staleTime: 1000 * 60 * 60 * 24, // 24 hours - voice data rarely changes
      gcTime: 1000 * 60 * 60 * 2, // 2 hours in memory
    })),
  });

  // Step 3: Convert results to voice counts for all providers
  const voiceCounts: Record<string, number> = {};
  const providerErrors: Record<string, boolean> = {};

  providers.forEach((provider) => {
    if (voiceLibraryProviders.includes(provider.identifier)) {
      // This provider has voice library data - get count from query results
      const queryIndex = voiceLibraryEnabledProviders.findIndex(
        (p) => p.identifier === provider.identifier
      );
      const query = queries[queryIndex];

      if (query?.isError) {
        // Provider had an error, mark it as such
        providerErrors[provider.identifier] = true;
        voiceCounts[provider.identifier] = 0;
      } else {
        // Provider is either loading or has data
        providerErrors[provider.identifier] = false;
        voiceCounts[provider.identifier] = query?.data?.length || 0;
      }
    } else {
      // This provider doesn't have voice library data - default to 0 voices
      providerErrors[provider.identifier] = false;
      voiceCounts[provider.identifier] = 0;
    }
  });

  return {
    voiceCounts,
    providerErrors,
    isLoading: voiceLibraryProvidersLoading || queries.some((q) => q.isLoading),
    isError: queries.some((q) => q.isError),
    errors: queries.filter((q) => q.isError).map((q) => q.error),
  };
};
