import { useCallback, useEffect, useState } from 'react';

import { apiService } from '../services/api';
import type { VoiceEntry } from '../types';

interface UseVoiceLibraryReturn {
  voiceLibrary: Record<string, VoiceEntry[]>;
  loadVoiceLibrary: (provider: string) => Promise<void>;
}

export const useVoiceLibrary = (
  connectionStatus: 'checking' | 'connected' | 'disconnected',
  provider?: string
): UseVoiceLibraryReturn => {
  const [voiceLibrary, setVoiceLibrary] = useState<
    Record<string, VoiceEntry[]>
  >({});

  const loadVoiceLibrary = useCallback(
    async (provider: string) => {
      if (!provider || connectionStatus !== 'connected') return;

      // Avoid refetching if already loaded
      if (voiceLibrary[provider]) return;

      const response = await apiService.getProviderVoices(provider);
      if (response.data) {
        setVoiceLibrary((prev) => ({
          ...prev,
          [provider]: response.data!,
        }));
      }
    },
    [connectionStatus, voiceLibrary]
  );

  useEffect(() => {
    if (provider) {
      loadVoiceLibrary(provider);
    }
  }, [provider, loadVoiceLibrary]);

  return { voiceLibrary, loadVoiceLibrary };
};
