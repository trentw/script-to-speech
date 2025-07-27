import { Loader2, Pause, Play } from 'lucide-react';
import React from 'react';

import { cn } from '@/lib/utils';

import {
  useAudioCommands,
  useAudioMetadata,
  useAudioState,
} from '../services/AudioService';
import { Button } from './ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

export interface MiniAudioPlayerProps {
  /** Additional CSS classes */
  className?: string;
  /** Show secondary text if available */
  showSecondaryText?: boolean;
  /** Custom title to override primary text */
  title?: string;
  /** Compact mode - even smaller UI */
  compact?: boolean;
}

/**
 * MiniAudioPlayer - Compact audio player for constrained spaces
 *
 * A minimal audio player that shows play/pause controls and title.
 * Uses AudioService's internal Zustand store for single source of truth.
 *
 * Features:
 * - Compact design suitable for lists, cards, or tight spaces
 * - Shows current audio metadata from AudioService internal store
 * - Pure visualization component (no reactive patterns)
 * - Tooltip support for truncated text
 * - Responsive design with optional compact mode
 */
export const MiniAudioPlayer: React.FC<MiniAudioPlayerProps> = ({
  className,
  showSecondaryText = false,
  title,
  compact = false,
}) => {
  // Get state and metadata from AudioService's internal store
  const { playbackState, src } = useAudioState();
  const { primaryText, secondaryText } = useAudioMetadata();
  const commands = useAudioCommands();

  // If no audio is loaded, don't render anything
  if (!src) {
    return null;
  }

  // Determine display text
  const displayTitle = title || primaryText || 'Audio';
  const displaySecondary = showSecondaryText ? secondaryText : undefined;

  // Determine button state and handler
  const isPlaying = playbackState === 'playing';
  const isLoading = playbackState === 'loading';
  const isReady = playbackState === 'idle' || playbackState === 'paused';
  const canPlay = isReady && !isLoading;
  const buttonHandler = isPlaying ? commands.pause : commands.play;

  // Button icon based on state
  const ButtonIcon = isLoading ? Loader2 : isPlaying ? Pause : Play;
  const buttonProps = {
    onClick: canPlay ? buttonHandler : undefined,
    disabled: !canPlay,
    'aria-label': isPlaying ? 'Pause audio' : 'Play audio',
  };

  return (
    <TooltipProvider>
      <div
        className={cn(
          'flex min-w-0 items-center gap-2',
          compact ? 'gap-1' : 'gap-2',
          className
        )}
      >
        {/* Play/Pause Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size={compact ? 'sm' : 'default'}
              className={cn(
                'flex-shrink-0',
                compact ? 'h-6 w-6 p-0' : 'h-8 w-8 p-0'
              )}
              {...buttonProps}
            >
              <ButtonIcon
                className={cn(
                  isLoading && 'animate-spin',
                  compact ? 'h-3 w-3' : 'h-4 w-4'
                )}
              />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {isLoading
              ? 'Loading audio...'
              : isPlaying
                ? 'Pause audio'
                : 'Play audio'}
          </TooltipContent>
        </Tooltip>

        {/* Audio Title */}
        <div className="flex min-w-0 flex-1 flex-col">
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  'text-foreground truncate font-medium',
                  compact ? 'text-xs' : 'text-sm'
                )}
                title={displayTitle}
              >
                {displayTitle}
              </div>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <div className="text-sm">{displayTitle}</div>
              {displaySecondary && (
                <div className="text-muted-foreground mt-1 text-xs">
                  {displaySecondary}
                </div>
              )}
            </TooltipContent>
          </Tooltip>

          {/* Secondary Text */}
          {displaySecondary && !compact && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className="text-muted-foreground truncate text-xs"
                  title={displaySecondary}
                >
                  {displaySecondary}
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <div className="text-xs">{displaySecondary}</div>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default MiniAudioPlayer;
