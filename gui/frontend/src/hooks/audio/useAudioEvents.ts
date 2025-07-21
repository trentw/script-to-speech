import { useCallback } from 'react';

import { useCentralAudio } from '../../stores/appStore';
import type {
  AudioCommand,
  AudioPayload,
  AudioSource,
} from '../../types/audio';

/**
 * Event-driven audio command system
 * Provides a clean API for triggering audio actions from anywhere in the app
 * Decouples audio commands from direct state manipulation
 */
export const useAudioEvents = () => {
  const { setAudioData, clearAudio } = useCentralAudio();

  /**
   * Execute an audio command
   * This is the main entry point for all audio actions
   */
  const executeCommand = useCallback(
    (command: AudioCommand) => {
      switch (command.type) {
        case 'play':
          if (command.payload) {
            setAudioData(
              command.payload.url,
              command.payload.primaryText,
              command.payload.secondaryText,
              command.payload.downloadFilename,
              command.payload.autoplay
            );
          }
          break;
        case 'stop':
        case 'clear':
          clearAudio();
          break;
        case 'pause':
          // Note: Pause functionality would require extending the audio player
          // For now, we'll treat it as a stop command
          clearAudio();
          break;
        default:
          console.warn('Unknown audio command type:', command.type);
      }
    },
    [setAudioData, clearAudio]
  );

  /**
   * Convenience method for playing audio
   * Most common use case - simplified API
   */
  const playAudio = useCallback(
    (
      url: string,
      primaryText: string,
      secondaryText?: string,
      downloadFilename?: string,
      autoplay: boolean = false,
      source: AudioSource = 'manual'
    ) => {
      executeCommand({
        type: 'play',
        payload: {
          url,
          primaryText,
          secondaryText,
          downloadFilename,
          autoplay,
          source,
        },
        timestamp: Date.now(),
      });
    },
    [executeCommand]
  );

  /**
   * Convenience method for stopping audio
   */
  const stopAudio = useCallback(() => {
    executeCommand({
      type: 'stop',
      timestamp: Date.now(),
    });
  }, [executeCommand]);

  /**
   * Convenience method for clearing audio player
   */
  const clearAudioPlayer = useCallback(() => {
    executeCommand({
      type: 'clear',
      timestamp: Date.now(),
    });
  }, [executeCommand]);

  /**
   * Play audio from generation completion
   * Specialized method for the generation workflow
   */
  const playGeneratedAudio = useCallback(
    (payload: AudioPayload) => {
      executeCommand({
        type: 'play',
        payload: {
          ...payload,
          source: 'generation',
          autoplay: true, // Generated audio always autoplays
        },
        timestamp: Date.now(),
      });
    },
    [executeCommand]
  );

  /**
   * Play audio from history/preview
   * Specialized method for user-initiated playback
   */
  const playPreviewAudio = useCallback(
    (
      url: string,
      primaryText: string,
      secondaryText?: string,
      downloadFilename?: string
    ) => {
      executeCommand({
        type: 'play',
        payload: {
          url,
          primaryText,
          secondaryText,
          downloadFilename,
          autoplay: false, // Preview audio doesn't autoplay
          source: 'preview',
        },
        timestamp: Date.now(),
      });
    },
    [executeCommand]
  );

  return {
    // Core command system
    executeCommand,

    // Convenience methods
    playAudio,
    stopAudio,
    clearAudioPlayer,

    // Specialized methods
    playGeneratedAudio,
    playPreviewAudio,
  };
};
