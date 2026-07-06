import { useCallback, useMemo } from 'react';

import type { AudioMetadata } from '@/services/AudioService';
import { useAudioCommands, useAudioState } from '@/services/AudioService';
import { normalizeAudioUrl } from '@/utils/audioUtils';

/**
 * Compact play/pause state for one audio URL, backed by the app-wide
 * AudioService singleton (same mechanism as PlayPreviewButton and the
 * Universal/Mini audio players).
 *
 * Because the service is a single global player, starting playback of a
 * different clip automatically replaces whatever was playing before - the
 * app-wide convention. `toggle()` pauses when this clip is playing, resumes
 * when it is paused, and load-and-plays otherwise.
 *
 * @param audioUrl - The clip's URL (compared against the service's current
 *                   src, ignoring query params, to know if "this" clip is
 *                   the active one)
 * @param metadata - Display metadata forwarded to the shared player UI
 */
export function useSharedAudioPlayback(
  audioUrl: string | null | undefined,
  metadata?: AudioMetadata
) {
  const audioState = useAudioState();
  const { loadAndPlay, pause, play } = useAudioCommands();

  // Normalize URLs so cache-busting query params don't break identity checks
  const normalizedUrl = useMemo(() => normalizeAudioUrl(audioUrl), [audioUrl]);
  const normalizedCurrentUrl = useMemo(
    () => normalizeAudioUrl(audioState.src),
    [audioState.src]
  );

  const isCurrentAudio =
    !!normalizedUrl &&
    !!normalizedCurrentUrl &&
    normalizedUrl === normalizedCurrentUrl;

  const isPlaying = isCurrentAudio && audioState.playbackState === 'playing';
  const isPaused = isCurrentAudio && audioState.playbackState === 'paused';
  const isLoading = isCurrentAudio && audioState.playbackState === 'loading';

  const toggle = useCallback(async () => {
    if (!audioUrl) return;

    try {
      if (isPlaying) {
        // This clip is playing - pause it
        pause();
      } else if (isPaused) {
        // This clip is paused - resume it
        await play();
      } else {
        // Different clip (or nothing) loaded - load and play this one,
        // replacing any current playback
        await loadAndPlay(audioUrl, metadata);
      }
    } catch (error) {
      console.error('Error toggling audio playback:', error);
      // Error state is managed by AudioService
    }
  }, [audioUrl, isPlaying, isPaused, pause, play, loadAndPlay, metadata]);

  return { isPlaying, isPaused, isLoading, toggle };
}
