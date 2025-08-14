import { useEffect, useMemo } from 'react';

import { useVoiceLibrary } from '@/hooks/queries';
import { useVoiceCasting } from '@/stores/appStore';
import type { VoiceEntry } from '@/types';

/**
 * Hook to resolve voice entry data, checking cache first then falling back to library lookup
 * @param provider - The TTS provider identifier
 * @param sts_id - The STS voice ID
 * @returns The resolved VoiceEntry or null if not found
 */
export function useResolveVoiceEntry(
  provider?: string,
  sts_id?: string
): VoiceEntry | null {
  const { getActiveSession, addToVoiceCache } = useVoiceCasting();
  const { data: voiceLibrary } = useVoiceLibrary(provider);

  const voice = useMemo(() => {
    // Early return if missing required params
    if (!provider || !sts_id) {
      console.log('[useResolveVoiceEntry] Missing params:', { provider, sts_id });
      return null;
    }

    const activeSession = getActiveSession();
    const voiceCache = activeSession?.voiceCache || new Map();

    // Check cache first
    const cacheKey = `${provider}:${sts_id}`;
    const cached = voiceCache.get(cacheKey);
    if (cached) {
      console.log('[useResolveVoiceEntry] Found in cache:', cacheKey);
      return cached;
    }

    // Fallback to library lookup (pure operation)
    const found = voiceLibrary?.find((v) => v.sts_id === sts_id) || null;
    console.log('[useResolveVoiceEntry] Library lookup:', {
      provider,
      sts_id,
      found: !!found,
      librarySize: voiceLibrary?.length || 0,
    });
    return found;
  }, [provider, sts_id, voiceLibrary, getActiveSession]);

  // Handle caching as a side effect
  useEffect(() => {
    const activeSession = getActiveSession();
    const voiceCache = activeSession?.voiceCache || new Map();

    if (
      voice &&
      provider &&
      sts_id &&
      !voiceCache.has(`${provider}:${sts_id}`)
    ) {
      addToVoiceCache(provider, sts_id, voice);
    }
  }, [voice, provider, sts_id, addToVoiceCache, getActiveSession]);

  return voice;
}
