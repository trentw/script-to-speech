import { useMemo } from 'react';

import { useVoiceLibrary } from '@/hooks/queries';
import type { VoiceEntry } from '@/types';

/**
 * Hook to resolve voice entry data from the voice library
 * @param provider - The TTS provider identifier
 * @param sts_id - The STS voice ID
 * @returns The resolved VoiceEntry or null if not found
 */
export function useResolveVoiceEntry(
  provider?: string,
  sts_id?: string
): VoiceEntry | null {
  const { data: voiceLibrary } = useVoiceLibrary(provider);

  const voice = useMemo(() => {
    // Early return if missing required params
    if (!provider || !sts_id) {
      console.log('[useResolveVoiceEntry] Missing params:', {
        provider,
        sts_id,
      });
      return null;
    }

    // Look up voice in library
    const found = voiceLibrary?.find((v) => v.sts_id === sts_id) || null;
    console.log('[useResolveVoiceEntry] Library lookup:', {
      provider,
      sts_id,
      found: !!found,
      librarySize: voiceLibrary?.length || 0,
    });
    return found;
  }, [provider, sts_id, voiceLibrary]);

  return voice;
}
