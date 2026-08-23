import { MicOff, PenLine, RotateCcw, VolumeX } from 'lucide-react';
import { memo } from 'react';

import { GENERATION_KIND_BADGES } from '@/components/review/generationKind';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ChunkInventoryEntry } from '@/types/chunks';

import { ChunkPlaybackControls } from './ChunkPlaybackControls';
import { getRowTextClasses } from './viewerLogic';

interface ChunkRowProps {
  entry: ChunkInventoryEntry;
  index: number;
  projectName: string;
  /** Row currently being played by sequential playback */
  isActive: boolean;
  /** Row selected in the detail panel */
  isSelected: boolean;
  onSelect: (index: number) => void;
  onPlayFromHere: (index: number) => void;
}

/**
 * One chunk in the reading view: a status/idx gutter, the chunk text styled
 * per type, and hover playback controls. Clicking the row opens it in the
 * detail panel.
 */
export const ChunkRow = memo(function ChunkRow({
  entry,
  index,
  projectName,
  isActive,
  isSelected,
  onSelect,
  onPlayFromHere,
}: ChunkRowProps) {
  const userModifiedBadge = entry.userModified
    ? GENERATION_KIND_BADGES[entry.userModified]
    : null;

  return (
    <div
      data-testid={`chunk-row-${entry.idx}`}
      className={cn(
        'group flex gap-2 px-4 py-1.5 transition-colors',
        entry.chunkType === 'scene_heading' &&
          'border-border mt-4 border-t pt-4',
        entry.chunkType === 'speaker_attribution' && 'pt-3',
        isSelected && 'bg-accent/50',
        isActive && 'bg-primary/10',
        !isSelected && !isActive && 'hover:bg-accent/30'
      )}
    >
      {/* No aria-label here: it would override the subtree and hide the
          screenplay text from screen readers in what is a reading view. The
          accessible name is the row content (#idx + text) plus a hidden
          chunk-type prefix. */}
      <button
        type="button"
        onClick={() => onSelect(index)}
        className="focus-visible:outline-primary flex min-w-0 flex-1 cursor-pointer gap-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <span className="sr-only">
          {`Chunk ${entry.idx}, ${entry.chunkType.replace(/_/g, ' ')}: `}
        </span>
        {/* Gutter: chunk number + status/user-modified markers */}
        <span className="text-muted-foreground flex w-14 shrink-0 flex-col items-end gap-1 pt-1 text-right font-sans text-[10px]">
          <span>#{entry.idx}</span>
          {entry.status === 'missing' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <MicOff className="text-destructive h-3.5 w-3.5" />
              </TooltipTrigger>
              <TooltipContent>No audio generated</TooltipContent>
            </Tooltip>
          )}
          {entry.status === 'expected_silence' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <VolumeX className="h-3.5 w-3.5 opacity-50" />
              </TooltipTrigger>
              <TooltipContent>Expected silence</TooltipContent>
            </Tooltip>
          )}
          {userModifiedBadge && (
            <Tooltip>
              <TooltipTrigger asChild>
                {entry.userModified === 'edit' ? (
                  <PenLine className="h-3.5 w-3.5" />
                ) : (
                  <RotateCcw className="h-3.5 w-3.5" />
                )}
              </TooltipTrigger>
              <TooltipContent>{userModifiedBadge.label}</TooltipContent>
            </Tooltip>
          )}
        </span>

        {/* Chunk text, styled for reading by type */}
        <span className="min-w-0 flex-1">
          <span
            className={cn(
              'block',
              getRowTextClasses(entry.chunkType),
              entry.status === 'expected_silence' && 'opacity-50'
            )}
          >
            {entry.originalText || (
              <span className="text-muted-foreground italic">(silence)</span>
            )}
          </span>
        </span>
      </button>

      {/* Playback controls: hover-revealed, but kept visible on the selected
          and active rows so the affordance is discoverable */}
      <div
        className={cn(
          'flex w-16 shrink-0 items-start justify-end gap-1 pt-0.5 transition-opacity focus-within:opacity-100',
          isSelected || isActive
            ? 'opacity-100'
            : 'opacity-0 group-hover:opacity-100'
        )}
      >
        <ChunkPlaybackControls
          entry={entry}
          projectName={projectName}
          playFromValue={index}
          onPlayFromHere={onPlayFromHere}
        />
      </div>
    </div>
  );
});
