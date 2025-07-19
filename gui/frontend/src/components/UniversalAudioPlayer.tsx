import React from 'react';
import { Play, Pause, Download, Loader2, Rewind, FastForward } from 'lucide-react';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { useAudio } from '../hooks/useAudio';
import { downloadAudio } from '../utils/audioUtils';
import { appButtonVariants, semanticButtons } from '@/components/ui/button-variants';

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
    seek 
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

  const handleDownload = () => {
    if (audioUrl) {
      downloadAudio(audioUrl, downloadFilename);
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
      <div className="flex flex-col gap-3 p-4 border border-border rounded-lg bg-background shadow-lg">
        <div className="flex items-center gap-6">
          {/* Left: Track Info */}
          <div className="flex-1 flex flex-col gap-1 min-w-0">
              <div className="font-semibold text-base text-foreground truncate" title={displayContent.primary}>
                {displayContent.primary}
              </div>
              <div className="text-sm text-muted-foreground truncate" title={displayContent.secondary}>
                {displayContent.secondary}
              </div>
          </div>

          {/* Center: Prominent Playback Controls */}
          <div className="flex items-center justify-center gap-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({ variant: "audio-control", size: "icon-md" })}
                    onClick={() => seek(currentTime - 5)}
                    disabled={!canPlay}
                  >
                    <Rewind className="w-6 h-6" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Skip back 5 seconds</p>
                </TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({ variant: "audio-play", size: "icon-xl" })}
                    onClick={handlePlayPause}
                    disabled={!canPlay}
                  >
                    {showLoading ? (
                    <Loader2 className="w-9 h-9 animate-spin" />
                    ) : isPlaying ? (
                    <Pause className="w-9 h-9" />
                    ) : (
                    <Play className="w-9 h-9 ml-1" />
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
                    className={appButtonVariants({ variant: "audio-control", size: "icon-md" })}
                    onClick={() => seek(currentTime + 5)}
                    disabled={!canPlay}
                  >
                    <FastForward className="w-6 h-6" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Skip forward 5 seconds</p>
                </TooltipContent>
              </Tooltip>
          </div>

          {/* Right: Download */}
          <div className="flex-1 flex items-center gap-4 justify-end">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({ variant: "audio-control", size: "icon-md" })}
                    onClick={handleDownload}
                    disabled={!hasAudio}
                  >
                    <Download className="w-6 h-6" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Download audio file</p>
                </TooltipContent>
              </Tooltip>
          </div>
        </div>
        {/* Bottom: Progress */}
        <div className="flex items-center gap-4">
            <span className="text-xs text-muted-foreground w-12 text-right font-mono">
            {formatTime(currentTime)}
            </span>
            <Slider
            value={[currentTime]}
            onValueChange={handleSeek}
            max={duration || 100}
            step={0.1}
            disabled={!canPlay}
            className="w-full [&_[data-slot=slider-track]]:bg-gray-300 [&_[data-slot=slider-track]]:dark:bg-gray-600 [&_[data-slot=slider-range]]:bg-black [&_[data-slot=slider-range]]:dark:bg-white [&_[data-slot=slider-thumb]]:bg-black [&_[data-slot=slider-thumb]]:dark:bg-white [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-black [&_[data-slot=slider-thumb]]:dark:border-white [&_[data-slot=slider-thumb]]:shadow-md"
            />
            <span className="text-xs text-muted-foreground w-12 font-mono">
            {formatTime(duration)}
            </span>
        </div>
      </div>
    </TooltipProvider>
  );
};

export default UniversalAudioPlayer;