import { ListVideo, Loader2, Pause, Play } from 'lucide-react';
import { memo } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useSharedAudioPlayback } from '@/hooks/audio/useSharedAudioPlayback';
import { apiService } from '@/services/api';
import type { ChunkInventoryEntry } from '@/types/chunks';

import { buildViewerMetadata, isPlayable } from './viewerLogic';

interface ChunkPlaybackControlsProps {
  entry: ChunkInventoryEntry;
  projectName: string;
  /** Value handed back to onPlayFromHere (list position for rows, chunk idx
   * for the detail panel) - lets callers pass one stable callback. */
  playFromValue: number;
  /** Start sequential playback from this chunk. */
  onPlayFromHere: (value: number) => void;
}

/**
 * The per-chunk play / play-from-here button pair, used by list rows and the
 * detail panel header (so both lenses share identical play affordances).
 * Single-chunk playback flows through the app-wide AudioService via
 * useSharedAudioPlayback.
 */
export const ChunkPlaybackControls = memo(function ChunkPlaybackControls({
  entry,
  projectName,
  playFromValue,
  onPlayFromHere,
}: ChunkPlaybackControlsProps) {
  const playable = isPlayable(entry);
  const audioUrl = playable
    ? apiService.getCacheAudioUrl(projectName, entry.cacheFilename)
    : null;
  const { isPlaying, isLoading, toggle } = useSharedAudioPlayback(
    audioUrl,
    buildViewerMetadata(entry)
  );

  return (
    <>
      {playable && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className={appButtonVariants({
                variant: 'list-action',
                size: 'icon-sm',
              })}
              onClick={(event) => {
                event.stopPropagation();
                void toggle();
              }}
              aria-label={isPlaying ? 'Pause chunk' : 'Play chunk'}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent>
            {isPlaying ? 'Pause' : 'Play this chunk'}
          </TooltipContent>
        </Tooltip>
      )}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className={appButtonVariants({
              variant: 'list-action',
              size: 'icon-sm',
            })}
            onClick={(event) => {
              event.stopPropagation();
              onPlayFromHere(playFromValue);
            }}
            aria-label="Play from here"
          >
            <ListVideo className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Play from here</TooltipContent>
      </Tooltip>
    </>
  );
});
