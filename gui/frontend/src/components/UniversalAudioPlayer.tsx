import React from 'react';
import { Play, Pause, Download, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { useAudio } from '../hooks/useAudio';
import { downloadAudio } from '../utils/audioUtils';

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
 * 
 * Layout: [Audio Identification] [Playback Controls] [Download]
 */
export const UniversalAudioPlayer: React.FC<AudioPlayerProps> = ({
  audioUrl,
  primaryText,
  secondaryText,
  downloadFilename,
  loading = false,
  autoplay = false,
  onPlay,
  onEnd,
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
  const showLoading = loading || isLoading;

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
    if (!isFinite(seconds)) return '0:00';
    
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Determine display content based on state
  const getDisplayContent = () => {
    if (loading) {
      return {
        primary: 'Generating audio...',
        secondary: 'Please wait',
      };
    }
    
    if (error) {
      return {
        primary: 'Audio error',
        secondary: error,
      };
    }
    
    if (!hasAudio) {
      return {
        primary: primaryText || 'Select audio for playback',
        secondary: secondaryText || 'No audio selected',
      };
    }
    
    return {
      primary: primaryText || 'Audio ready',
      secondary: secondaryText || 'Ready to play',
    };
  };

  const displayContent = getDisplayContent();

  return (
    <div className="flex items-center gap-4 p-4 border border-border rounded-lg bg-background">
      {/* Left: Audio Identification */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-foreground truncate">
          {displayContent.primary}
        </div>
        <div className="text-sm text-muted-foreground truncate">
          {displayContent.secondary}
        </div>
      </div>

      {/* Center: Playback Controls */}
      <div className="flex flex-col items-center gap-2 w-32">
        {/* Play/Pause Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handlePlayPause}
          disabled={!canPlay}
          className="h-10 w-10 p-0 rounded-full hover:bg-accent"
        >
          {showLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4 ml-0.5" />
          )}
        </Button>

        {/* Progress Slider */}
        {hasAudio && (
          <>
            <Slider
              value={[currentTime]}
              onValueChange={handleSeek}
              max={duration || 0}
              step={0.1}
              disabled={!canPlay}
              className="w-full h-2"
            />
            <div className="flex justify-between text-xs text-muted-foreground w-full">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </>
        )}
      </div>

      {/* Right: Download Button */}
      <div className="flex items-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDownload}
          disabled={!hasAudio}
          className="h-8 w-8 p-0"
          title="Download audio"
        >
          <Download className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};