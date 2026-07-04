import { X } from 'lucide-react';
import React from 'react';

import { Badge } from '@/components/ui/badge';

import type { TextProcessorPreviewDiff } from '../../types/text-processing';
import { ChunkDiff } from './ChunkDiff';
import { InlineIconButton } from './InlineIconButton';

interface DirtyDiffResultsProps {
  result: TextProcessorPreviewDiff;
  /** What the diff was run against, for the headline (e.g. "this change") */
  subject?: string;
  onDismiss?: () => void;
}

/**
 * Renders a preview-diff result: the chunks whose final output differs
 * between a draft pipeline and the saved baseline. Used inline under a dirty
 * entry ("test this change") and in the Preview tab ("preview unsaved
 * changes").
 */
export const DirtyDiffResults: React.FC<DirtyDiffResultsProps> = ({
  result,
  subject = 'these changes',
  onDismiss,
}) => {
  const headline =
    result.alignment === 'counts_differ'
      ? `${subject} alter the chunk structure`
      : result.changed_chunk_count === 0
        ? `No additional changes from ${subject}`
        : `${result.changed_chunk_count} chunk${
            result.changed_chunk_count === 1 ? '' : 's'
          } change with ${subject}`;

  return (
    <div className="bg-muted/30 space-y-2 rounded-md border p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium first-letter:uppercase">
          {headline}
          <span className="text-muted-foreground font-normal">
            {' '}
            (vs the saved config)
          </span>
        </p>
        {onDismiss && (
          <InlineIconButton label="Dismiss results" onClick={onDismiss}>
            <X className="h-3.5 w-3.5" />
          </InlineIconButton>
        )}
      </div>

      {result.alignment === 'counts_differ' ? (
        <div className="text-muted-foreground space-y-1 text-xs">
          <p>
            The runs produce different chunk counts (
            {result.baseline_final_count} saved vs {result.draft_final_count}{' '}
            with changes), so per-chunk diffs can't be paired up. Structure
            stages:
          </p>
          <div className="flex flex-wrap gap-2">
            {result.draft_stages.map((stage, index) => {
              const baselineStage = result.baseline_stages.find(
                (s, i) => s.name === stage.name && i === index
              );
              const differs =
                baselineStage &&
                baselineStage.after_count !== stage.after_count;
              return (
                <Badge
                  key={`${stage.name}-${index}`}
                  variant={differs ? 'default' : 'outline'}
                  className="font-mono text-[10px]"
                >
                  {stage.name}
                  {baselineStage && differs
                    ? ` (${baselineStage.after_count} → ${stage.after_count})`
                    : ` (${stage.after_count})`}
                </Badge>
              );
            })}
          </div>
        </div>
      ) : (
        result.changed_chunk_count > 0 && (
          <div className="space-y-2">
            {result.changed_chunks.map((chunk) => (
              <div
                key={chunk.index}
                className="bg-background rounded-md border p-2"
              >
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {chunk.chunk_type}
                  </Badge>
                  {chunk.speaker && (
                    <span className="text-muted-foreground text-xs font-medium">
                      {chunk.speaker}
                    </span>
                  )}
                </div>
                <ChunkDiff before={chunk.before} after={chunk.after} />
              </div>
            ))}
            {result.truncated && (
              <p className="text-muted-foreground text-center text-xs">
                Showing the first {result.changed_chunks.length} of{' '}
                {result.changed_chunk_count} changed chunks.
              </p>
            )}
          </div>
        )
      )}
    </div>
  );
};
