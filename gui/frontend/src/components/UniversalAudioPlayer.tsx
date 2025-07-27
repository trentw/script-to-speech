import { FastForward, Loader2, Pause, Play, Rewind } from 'lucide-react';
import React, { useEffect } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';

import { useAudioCommands,useAudioMetadata, useAudioState } from '../services/AudioService';
import { DownloadButton, DownloadButtonPresets } from './ui/DownloadButton';
import { Slider } from './ui/slider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

export interface AudioPlayerProps {
  /** Callback when audio starts playing */
  onPlay?: () => void;
  /** Callback when audio ends */
  onEnd?: () => void;
}

/**
 * Universal AudioPlayer component - Pure visualization component
 * Now uses AudioService's internal Zustand store for single source of truth
 * NO reactive patterns - purely displays current state and provides controls
 */
export const UniversalAudioPlayer: React.FC<AudioPlayerProps> = ({
  onPlay,
  onEnd,
}) => {
  // Get audio state and metadata from AudioService's internal store
  const { playbackState, currentTime, duration, error, src } = useAudioState();
  const { primaryText, secondaryText, downloadFilename } = useAudioMetadata();
  const commands = useAudioCommands();

  // Handle onEnd callback - only when audio naturally ends
  useEffect(() => {
    if (onEnd && playbackState === 'idle' && currentTime === 0 && src) {
      onEnd();
    }
  }, [onEnd, playbackState, currentTime, src]);

  const hasAudio = Boolean(src);
  const isPlaying = playbackState === 'playing';
  const isLoading = playbackState === 'loading';
  const showLoading = isLoading;
  
  // Specific control capabilities - fixes disabled controls during playback
  const canTogglePlayback = hasAudio && !isLoading && !error;
  const canSeek = hasAudio && !isLoading && !error && duration > 0;

  const handlePlayPause = async () => {
    if (isPlaying) {
      commands.pause();
    } else {
      if (onPlay) onPlay();
      await commands.play();
    }
  };

  const handleSeek = (values: number[]) => {
    commands.seek(values[0]);
  };

  const formatTime = (seconds: number): string => {
    if (!isFinite(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getDisplayContent = () => {
    // Always show actual content if available, even during loading
    if (primaryText || secondaryText) {
      return {
        primary: primaryText || 'Audio Ready',
        secondary: secondaryText || 'Ready for playback',
      };
    }

    if (error) {
      return {
        primary: 'Audio Error',
        secondary: 'Could not load audio file',
      };
    }

    // Only show loading state when no content is available
    if (showLoading) {
      return {
        primary: 'Loading audio...',
        secondary: 'Please wait...',
      };
    }

    if (!hasAudio) {
      return {
        primary: 'Text to Speech',
        secondary: 'Generate audio or select from history to play',
      };
    }

    return {
      primary: 'Audio Ready',
      secondary: 'Ready for playback',
    };
  };

  const displayContent = getDisplayContent();

  return (
    <TooltipProvider>
      <div className="border-border bg-background flex flex-col gap-3 rounded-lg border p-4 shadow-lg">
        <div className="flex items-center gap-6">
          {/* Left: Track Info */}
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <div
              className="text-foreground truncate text-base font-semibold"
              title={displayContent.primary}
            >
              {displayContent.primary}
            </div>
            <div
              className="text-muted-foreground truncate text-sm"
              title={displayContent.secondary}
            >
              {displayContent.secondary}
            </div>
          </div>

          {/* Center: Prominent Playback Controls */}
          <div className="flex items-center justify-center gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={appButtonVariants({
                    variant: 'audio-control',
                    size: 'icon-md',
                  })}
                  onClick={() => commands.seek(currentTime - 5)}
                  disabled={!canSeek}
                >
                  <Rewind className="h-6 w-6" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Skip back 5 seconds</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={appButtonVariants({
                    variant: 'audio-play',
                    size: 'icon-xl',
                  })}
                  onClick={handlePlayPause}
                  disabled={!canTogglePlayback}
                >
                  {showLoading ? (
                    <Loader2 className="h-9 w-9 animate-spin" />
                  ) : isPlaying ? (
                    <Pause className="h-9 w-9" />
                  ) : (
                    <Play className="ml-1 h-9 w-9" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isPlaying ? 'Pause' : 'Play'} audio</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={appButtonVariants({
                    variant: 'audio-control',
                    size: 'icon-md',
                  })}
                  onClick={() => commands.seek(currentTime + 5)}
                  disabled={!canSeek}
                >
                  <FastForward className="h-6 w-6" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Skip forward 5 seconds</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Right: Download */}
          <div className="flex flex-1 items-center justify-end gap-4">
            {hasAudio && src && (
              <DownloadButton
                url={src}
                filename={downloadFilename}
                {...DownloadButtonPresets.audioControl}
                tooltip="Download audio file"
                disabled={!hasAudio}
              />
            )}
          </div>
        </div>
        {/* Bottom: Progress */}
        <div className="flex items-center gap-4">
          <span className="text-muted-foreground w-12 text-right font-mono text-xs">
            {formatTime(currentTime)}
          </span>
          <Slider
            value={[currentTime]}
            onValueChange={handleSeek}
            max={duration || 100}
            step={0.1}
            disabled={!canSeek}
            className="w-full [&_[data-slot=slider-range]]:bg-black [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-black [&_[data-slot=slider-thumb]]:bg-black [&_[data-slot=slider-thumb]]:shadow-md [&_[data-slot=slider-track]]:bg-gray-300"
          />
          <span className="text-muted-foreground w-12 font-mono text-xs">
            {formatTime(duration)}
          </span>
        </div>
      </div>
    </TooltipProvider>
  );
};

export default UniversalAudioPlayer;
