import { Loader2, Pause, Play } from 'lucide-react';
import { forwardRef, useCallback, useMemo } from 'react';

import { cn } from '@/lib/utils';
import { useAudioCommands, useAudioState } from '@/services/AudioService';
import type { VoiceEntry } from '@/types';
import { normalizeAudioUrl } from '@/utils/audioUtils';
import { getVoiceDisplayName } from '@/utils/voiceUtils';

import { appButtonVariants } from './ui/button-variants';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';

interface PlayPreviewButtonProps {
  voice: VoiceEntry;
  providerName: string;
  characterName?: string;
  tooltip?: string;
  disabled?: boolean;
  className?: string;
  size?: 'icon-sm' | 'icon' | 'icon-md' | 'icon-lg';
  variant?: 'list-action' | 'audio-control' | 'audio-play';
}

/**
 * Smart play/pause button for audio previews
 * Handles all audio operations directly using the command pattern
 * No conditional flows or hidden complexity
 */
export const PlayPreviewButton = forwardRef<
  HTMLButtonElement,
  PlayPreviewButtonProps
>(
  (
    {
      voice,
      providerName,
      characterName,
      tooltip = 'Play preview',
      disabled = false,
      className,
      size = 'icon-sm',
      variant = 'list-action',
    },
    ref
  ) => {
    const audioState = useAudioState();
    const { loadAndPlay, pause, play } = useAudioCommands();

    // Normalize URLs for comparison
    const normalizedPreviewUrl = useMemo(
      () => normalizeAudioUrl(voice?.preview_url),
      [voice?.preview_url]
    );

    const normalizedCurrentUrl = useMemo(
      () => normalizeAudioUrl(audioState.src),
      [audioState.src]
    );

    // Determine if this preview is the currently loaded audio
    const isCurrentAudio =
      normalizedPreviewUrl &&
      normalizedCurrentUrl &&
      normalizedPreviewUrl === normalizedCurrentUrl;

    // Determine button states
    const isPlaying = isCurrentAudio && audioState.playbackState === 'playing';
    const isPaused = isCurrentAudio && audioState.playbackState === 'paused';
    const isLoading = isCurrentAudio && audioState.playbackState === 'loading';

    // Handle button click with explicit commands
    const handleClick = useCallback(async () => {
      if (!voice?.preview_url) return;

      try {
        if (isPlaying) {
          // Currently playing this audio - pause it
          pause();
        } else if (isPaused) {
          // Currently paused on this audio - resume it
          await play();
        } else {
          // Different audio or no audio loaded - load and play new audio
          const voiceName = getVoiceDisplayName(voice);
          const primaryText = characterName
            ? `${characterName} • Voice preview: ${voiceName}`
            : `Voice preview: ${voiceName}`;
          const secondaryText = `${providerName} • ${voiceName}`;

          // Atomic command: load audio and set metadata in one operation
          await loadAndPlay(voice.preview_url, {
            primaryText,
            secondaryText,
          });
        }
      } catch (error) {
        console.error('Error toggling preview audio:', error);
        // Error handling is managed by AudioService
      }
    }, [
      voice,
      providerName,
      characterName,
      isPlaying,
      isPaused,
      loadAndPlay,
      pause,
      play,
    ]);

    // Determine button state and icon
    const isDisabled = disabled || !voice?.preview_url || isLoading;
    const showPause = isPlaying;
    const buttonLabel = showPause ? 'Pause' : isPaused ? 'Resume' : 'Play';
    const tooltipText = showPause
      ? 'Pause preview'
      : isPaused
        ? 'Resume preview'
        : tooltip;

    const buttonContent = (
      <button
        ref={ref}
        className={cn(appButtonVariants({ variant, size }), className)}
        onClick={(e) => {
          e.stopPropagation();
          handleClick();
        }}
        disabled={isDisabled}
        aria-label={`${buttonLabel} audio preview`}
        aria-pressed={isPlaying}
        type="button"
      >
        {isLoading ? (
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
        ) : showPause ? (
          <Pause className="h-3 w-3" aria-hidden="true" />
        ) : (
          <Play className="h-3 w-3" aria-hidden="true" />
        )}
      </button>
    );

    // If no tooltip text, return button without tooltip wrapper
    if (!tooltipText) {
      return buttonContent;
    }

    return (
      <Tooltip>
        <TooltipTrigger asChild>{buttonContent}</TooltipTrigger>
        <TooltipContent>
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    );
  }
);

PlayPreviewButton.displayName = 'PlayPreviewButton';
