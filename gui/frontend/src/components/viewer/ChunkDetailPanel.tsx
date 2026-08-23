import { Copy, X } from 'lucide-react';
import { toast } from 'sonner';

import { buildProblemClip } from '@/components/review/chunkSearch';
import { DialogueItem } from '@/components/review/DialogueItem';
import { GENERATION_KIND_BADGES } from '@/components/review/generationKind';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { cn } from '@/lib/utils';
import type { ChunkInventoryEntry, ChunkSpeakerConfig } from '@/types/chunks';

import { ChunkPlaybackControls } from './ChunkPlaybackControls';

/** Cap on rendered shared-chunk jump chips */
const MAX_OCCURRENCE_CHIPS = 12;

const STATUS_LABELS: Record<string, string> = {
  cached: 'cached',
  missing: 'missing',
  expected_silence: 'expected silence',
};

interface ChunkDetailPanelProps {
  entry: ChunkInventoryEntry;
  speakerConfigs: Record<string, ChunkSpeakerConfig>;
  projectName: string;
  cacheFolder: string;
  /** Scroll the list to another chunk (shared-audio chips) */
  onJumpToChunk: (idx: number) => void;
  /** Start sequential playback from this chunk (by idx). Shared by both
   * lenses - in the PDF lens this is the only play-from-here entry point. */
  onPlayFromHere?: ((idx: number) => void) | undefined;
  /** Chunks derived from the same selected PDF source region. */
  regionEntries?: ChunkInventoryEntry[] | undefined;
  onSelectRegionEntry?: ((idx: number) => void) | undefined;
  onClose: () => void;
}

/**
 * Split-panel detail view for a selected chunk: the advanced details
 * (original vs processed text, cache filename, shared-audio occurrences)
 * plus the full chunk-audio editor card (play / regenerate / edit / commit).
 */
export function ChunkDetailPanel({
  entry,
  speakerConfigs,
  projectName,
  cacheFolder,
  onJumpToChunk,
  onPlayFromHere,
  regionEntries = [],
  onSelectRegionEntry,
  onClose,
}: ChunkDetailPanelProps) {
  const userModifiedBadge = entry.userModified
    ? GENERATION_KIND_BADGES[entry.userModified]
    : null;
  const otherOccurrences = entry.occurrences.filter((idx) => idx !== entry.idx);

  const copyCacheFilename = async () => {
    try {
      await navigator.clipboard.writeText(entry.cacheFilename);
      toast('Cache filename copied');
    } catch {
      toast.error('Could not copy to clipboard');
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-border flex items-start justify-between gap-2 border-b p-4">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">
            {entry.speakerDisplay}
            <span className="text-muted-foreground ml-2 font-normal">
              chunk #{entry.idx}
            </span>
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="text-xs">
              {entry.chunkType}
            </Badge>
            <Badge
              variant={entry.status === 'missing' ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {STATUS_LABELS[entry.status] ?? entry.status}
            </Badge>
            {userModifiedBadge && (
              <Badge variant="outline" className="text-xs">
                {userModifiedBadge.label}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {onPlayFromHere && (
            <ChunkPlaybackControls
              entry={entry}
              projectName={projectName}
              playFromValue={entry.idx}
              onPlayFromHere={onPlayFromHere}
            />
          )}
          <button
            className={appButtonVariants({
              variant: 'list-action',
              size: 'icon-sm',
            })}
            onClick={onClose}
            aria-label="Close details"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Details + editor */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {regionEntries.length > 1 && (
          <section>
            <div className="mb-2">
              <h3 className="text-xs font-semibold uppercase">
                Source region · {regionEntries.length} audio chunks
              </h3>
              <p className="text-muted-foreground mt-1 text-xs">
                This PDF text was split into multiple spoken segments. Choose
                one to inspect or re-record it.
              </p>
            </div>
            <div className="space-y-1.5">
              {regionEntries.map((regionEntry) => {
                const provenance = regionEntry.userModified
                  ? GENERATION_KIND_BADGES[regionEntry.userModified]
                  : null;
                const isCurrent = regionEntry.idx === entry.idx;
                return (
                  <button
                    key={regionEntry.idx}
                    type="button"
                    aria-label={`Select chunk #${regionEntry.idx} from source region`}
                    aria-current={isCurrent ? 'true' : undefined}
                    className={cn(
                      'border-border hover:bg-accent/40 w-full rounded-md border p-2 text-left transition-colors',
                      isCurrent && 'border-primary bg-primary/5'
                    )}
                    onClick={() => onSelectRegionEntry?.(regionEntry.idx)}
                  >
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="font-semibold">#{regionEntry.idx}</span>
                      <span className="truncate">
                        {regionEntry.speakerDisplay}
                      </span>
                      <Badge variant="outline" className="ml-auto text-[10px]">
                        {STATUS_LABELS[regionEntry.status] ??
                          regionEntry.status}
                      </Badge>
                      {provenance && (
                        <Badge variant="outline" className="text-[10px]">
                          {provenance.label}
                        </Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">
                      {regionEntry.originalText || '(silence)'}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Audio
          </h3>
          <div className="border-border rounded-lg border p-2">
            <DialogueItem
              clip={buildProblemClip(entry, speakerConfigs)}
              projectName={projectName}
              cacheFolder={cacheFolder}
              showPlayExisting={entry.status === 'cached'}
              occurrenceCount={entry.occurrences.length}
              userModified={entry.userModified}
            />
          </div>
        </section>

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Original
          </h3>
          <p className="bg-muted rounded-md p-2 text-sm whitespace-pre-wrap">
            {entry.originalText || (
              <span className="text-muted-foreground italic">(empty)</span>
            )}
          </p>
        </section>

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Spoken (processed)
          </h3>
          <p className="bg-muted rounded-md p-2 text-sm whitespace-pre-wrap">
            {entry.processedText || (
              <span className="text-muted-foreground italic">(empty)</span>
            )}
          </p>
        </section>

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Cache file
          </h3>
          <div className="flex items-start gap-1">
            <code className="bg-muted flex-1 rounded-md p-2 font-mono text-xs break-all">
              {entry.cacheFilename}
            </code>
            <button
              className={appButtonVariants({
                variant: 'list-action',
                size: 'icon-sm',
              })}
              onClick={() => void copyCacheFilename()}
              aria-label="Copy cache filename"
            >
              <Copy className="h-4 w-4" />
            </button>
          </div>
        </section>

        {otherOccurrences.length > 0 && (
          <section>
            <h3 className="text-muted-foreground mb-1 text-xs font-medium uppercase">
              Shared audio
            </h3>
            <p className="text-muted-foreground mb-2 text-xs">
              This audio file is shared by {entry.occurrences.length} chunks -
              re-recording changes all of them.
            </p>
            <div className="flex flex-wrap gap-1">
              {otherOccurrences.slice(0, MAX_OCCURRENCE_CHIPS).map((idx) => (
                <button
                  key={idx}
                  className={appButtonVariants({
                    variant: 'secondary',
                    size: 'sm',
                  })}
                  onClick={() => onJumpToChunk(idx)}
                >
                  chunk #{idx}
                </button>
              ))}
              {otherOccurrences.length > MAX_OCCURRENCE_CHIPS && (
                <span className="text-muted-foreground self-center text-xs">
                  +{otherOccurrences.length - MAX_OCCURRENCE_CHIPS} more
                </span>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
