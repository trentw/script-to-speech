import { useCallback } from 'react';

import { useAudioCommands as useAudioServiceCommands } from '../services/AudioService';
import type { VoiceEntry } from '../types';
import { getVoiceDisplayName } from '../utils/voiceUtils';

/**
 * High-level audio command hooks for common use cases
 *
 * This hook provides application-specific commands that use the AudioService's
 * internal Zustand store pattern for atomic state updates.
 *
 * Features:
 * - Commands pass metadata directly to AudioService (single source of truth)
 * - No dual state management - AudioService handles everything
 * - Explicit command flow eliminates race conditions
 * - Clean separation between control and display concerns
 */
export function useAudioCommands() {
  const commands = useAudioServiceCommands();

  /**
   * Play a voice preview with explicit command flow
   * Passes metadata directly to AudioService for atomic updates
   */
  const playVoicePreview = useCallback(
    async (voice: VoiceEntry, providerName: string, characterName?: string) => {
      if (!voice?.preview_url) return;

      const voiceName = getVoiceDisplayName(voice);
      const primaryText = characterName
        ? `${characterName} • Voice preview: ${voiceName}`
        : `Voice preview: ${voiceName}`;
      const secondaryText = `${providerName} • ${voiceName}`;

      // Atomic command: load audio and set metadata in one operation
      await commands.loadAndPlay(voice.preview_url, {
        primaryText,
        secondaryText,
        // no download filename for previews
      });
    },
    [commands]
  );

  /**
   * Play generated audio with explicit command flow
   * Passes metadata directly to AudioService for atomic updates
   */
  const playGeneratedAudio = useCallback(
    async (
      audioUrl: string,
      primaryText: string,
      secondaryText?: string,
      downloadFilename?: string
    ) => {
      // Atomic command: load audio and set metadata in one operation
      await commands.loadAndPlay(audioUrl, {
        primaryText,
        secondaryText: secondaryText || '',
        downloadFilename,
      });
    },
    [commands]
  );

  /**
   * Load audio with metadata without playing (rare use case)
   */
  const loadAudio = useCallback(
    async (
      audioUrl: string,
      primaryText: string,
      secondaryText?: string,
      downloadFilename?: string
    ) => {
      // Atomic command: load audio and set metadata in one operation
      commands.loadWithMetadata(audioUrl, {
        primaryText,
        secondaryText: secondaryText || '',
        downloadFilename,
      });
    },
    [commands]
  );

  /**
   * Load and play audio in one command (convenience method)
   * Always loads then plays - no conditional behavior
   */
  const loadAndPlayAudio = useCallback(
    async (
      audioUrl: string,
      primaryText: string,
      secondaryText?: string,
      downloadFilename?: string
    ) => {
      // Atomic command: load audio and set metadata in one operation
      await commands.loadAndPlay(audioUrl, {
        primaryText,
        secondaryText: secondaryText || '',
        downloadFilename,
      });
    },
    [commands]
  );

  return {
    // High-level commands for common use cases
    playVoicePreview,
    playGeneratedAudio,
    loadAndPlayAudio,

    // Low-level commands for fine control
    loadAudio,
    playAudio: commands.play,
    pauseAudio: commands.pause,
    toggleAudio: commands.toggle,
    clearAudio: commands.clear,

    // Direct access to AudioService commands
    ...commands,
  };
}
