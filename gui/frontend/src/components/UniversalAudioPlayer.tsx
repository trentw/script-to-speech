import { FastForward, Loader2, Pause, Play, Rewind } from 'lucide-react';
import React from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';

import { useAudio } from '../hooks/useAudio';
import { DownloadButton, DownloadButtonPresets } from './ui/DownloadButton';
import { Slider } from './ui/slider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

export interface AudioPlayerProps {
  /** Audio URL to play - if undefined, shows empty state */
  audioUrl?: string;
  /** Primary text - main description or "Select audio for playback" */
  primaryText?: string;
  /** Secondary text - provider and voice info */
  secondaryText?: string;
  /** Custom filename for downloads */
  downloadFilename?: string;
  /** Show loading state during generation */
  loading?: boolean;
  /** Auto-play when new audio is loaded */
  autoplay?: boolean;
  /** Callback when audio starts playing */
  onPlay?: () => void;
  /** Callback when audio ends */
  onEnd?: () => void;
}

/**
 * Universal AudioPlayer component that's always visible
 * Used for voice previews, generated speech, and history playback
 */
export const UniversalAudioPlayer: React.FC<AudioPlayerProps> = ({
  audioUrl,
  primaryText,
  secondaryText,
  downloadFilename,
  loading = false,
  autoplay = false,
  onPlay,
}) => {
  const {
    isReady,
    isPlaying,
    isLoading,
    currentTime,
    duration,
    error,
    play,
    pause,
    seek,
  } = useAudio({
    src: audioUrl,
    autoplay: autoplay,
  });

  const hasAudio = Boolean(audioUrl && !loading);
  const canPlay = hasAudio && isReady && !error;
  const showLoading = loading || (isLoading && !isReady);

  const handlePlayPause = async () => {
    if (isPlaying) {
      pause();
    } else {
      if (onPlay) onPlay();
      await play();
    }
  };

  const handleSeek = (values: number[]) => {
    seek(values[0]);
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
                  onClick={() => seek(currentTime - 5)}
                  disabled={!canPlay}
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
                  disabled={!canPlay}
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
                  onClick={() => seek(currentTime + 5)}
                  disabled={!canPlay}
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
            {hasAudio && audioUrl && (
              <DownloadButton
                url={audioUrl}
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
            disabled={!canPlay}
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
