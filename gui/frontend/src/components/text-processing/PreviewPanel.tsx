import { ChevronDown, FlaskConical, Play } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { buttonUtils } from '@/components/ui/button-variants';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

import {
  usePreviewTextProcessorDiff,
  usePreviewTextProcessors,
} from '../../hooks/mutations/useTextProcessorConfigMutations';
import type { EntryPayload } from '../../services/textProcessorApi';
import type {
  PreviewChangedChunk,
  TextProcessorPreview,
  TextProcessorPreviewDiff,
} from '../../types/text-processing';
import { ChunkDiff } from './ChunkDiff';
import { DirtyDiffResults } from './DirtyDiffResults';

const MAX_RENDERED_CHUNKS = 100;

interface PreviewPanelProps {
  inputPath: string;
  /** Current buffer entries (including unsaved edits) */
  getEntries: () => EntryPayload[];
  /** The editor's snapshot of what's on disk */
  getBaselineEntries: () => EntryPayload[];
  dirty: boolean;
}

/**
 * Preview tab. The primary flow diffs the unsaved edits against the saved
 * config ("what do my changes add"); the full-pipeline preview (everything
 * the config does to the script) remains available below it.
 */
export const PreviewPanel: React.FC<PreviewPanelProps> = ({
  inputPath,
  getEntries,
  getBaselineEntries,
  dirty,
}) => {
  const previewDiff = usePreviewTextProcessorDiff();
  const [diffResult, setDiffResult] = useState<TextProcessorPreviewDiff | null>(
    null
  );

  // The result describes unsaved changes; once they're saved or discarded
  // there's nothing left for it to describe.
  useEffect(() => {
    if (!dirty) setDiffResult(null);
  }, [dirty]);

  const runDiff = async () => {
    try {
      const data = await previewDiff.mutateAsync({
        inputPath,
        draftEntries: getEntries(),
        baselineEntries: getBaselineEntries(),
        maxChangedChunks: MAX_RENDERED_CHUNKS,
      });
      setDiffResult(data);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Preview failed');
    }
  };

  const diffDisabled = !dirty || previewDiff.isPending;

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Unsaved changes</h2>
            <p className="text-muted-foreground text-sm">
              Shows only what your unsaved edits add on top of the saved
              configuration.
            </p>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                aria-disabled={diffDisabled}
                className={cn(diffDisabled && buttonUtils.ariaDisabled)}
                onClick={() => {
                  if (!diffDisabled) void runDiff();
                }}
              >
                <FlaskConical className="mr-1 h-4 w-4" />
                {previewDiff.isPending ? 'Running…' : 'Preview unsaved changes'}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                {dirty
                  ? 'Diff all unsaved changes against the saved config'
                  : 'No unsaved changes to preview'}
              </p>
            </TooltipContent>
          </Tooltip>
        </div>

        {diffResult && (
          <DirtyDiffResults
            result={diffResult}
            subject="your unsaved changes"
            onDismiss={() => setDiffResult(null)}
          />
        )}
      </div>

      <Separator />

      <FullPreview
        inputPath={inputPath}
        getEntries={getEntries}
        dirty={dirty}
      />
    </div>
  );
};

interface FullPreviewProps {
  inputPath: string;
  getEntries: () => EntryPayload[];
  dirty: boolean;
}

/**
 * The full-pipeline preview: runs the entire (possibly edited) pipeline over
 * the project's screenplay and shows before/after diffs of every changed
 * chunk, with badges attributing each change to the processor(s) responsible.
 */
const FullPreview: React.FC<FullPreviewProps> = ({
  inputPath,
  getEntries,
  dirty,
}) => {
  const preview = usePreviewTextProcessors();
  const [result, setResult] = useState<TextProcessorPreview | null>(null);

  const run = async () => {
    try {
      const data = await preview.mutateAsync({
        inputPath,
        entries: getEntries(),
        maxChangedChunks: MAX_RENDERED_CHUNKS,
      });
      setResult(data);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Preview failed');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Full pipeline</h2>
          <p className="text-muted-foreground text-sm">
            Runs the {dirty ? 'edited (unsaved)' : 'current'} pipeline on this
            screenplay and shows everything it changes.
          </p>
        </div>
        <Button variant="outline" onClick={run} disabled={preview.isPending}>
          <Play className="mr-1 h-4 w-4" />
          {preview.isPending ? 'Running…' : 'Run full preview'}
        </Button>
      </div>

      {result && (
        <>
          <div className="text-muted-foreground flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <span>
              <strong className="text-foreground">
                {result.input_chunk_count}
              </strong>{' '}
              chunks in
            </span>
            <span>
              <strong className="text-foreground">
                {result.final_chunk_count}
              </strong>{' '}
              chunks out
            </span>
            <span>
              <strong className="text-foreground">
                {result.changed_chunk_count}
              </strong>{' '}
              chunks with text changes
            </span>
          </div>

          {result.preprocessor_stages.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.preprocessor_stages.map((stage, index) => (
                <Badge
                  key={`${stage.name}-${index}`}
                  variant={stage.modified ? 'default' : 'outline'}
                  className="font-mono text-[10px]"
                >
                  {stage.name}
                  {stage.before_count !== stage.after_count &&
                    ` (${stage.before_count} → ${stage.after_count})`}
                </Badge>
              ))}
            </div>
          )}

          {result.changed_chunk_count === 0 ? (
            <p className="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm">
              No chunk text changes. Structural changes (merges, removals) are
              summarized above.
            </p>
          ) : (
            <div className="space-y-3">
              {result.changed_chunks.map((chunk) => (
                <ChangedChunkCard key={chunk.index} chunk={chunk} />
              ))}
              {result.truncated && (
                <p className="text-muted-foreground text-center text-xs">
                  Showing the first {result.changed_chunks.length} of{' '}
                  {result.changed_chunk_count} changed chunks.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

const ChangedChunkCard: React.FC<{ chunk: PreviewChangedChunk }> = ({
  chunk,
}) => {
  const [stepsOpen, setStepsOpen] = useState(false);

  return (
    <Card className="py-3">
      <CardContent className="space-y-2 px-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="text-[10px]">
            {chunk.chunk_type}
          </Badge>
          {chunk.speaker && (
            <span className="text-muted-foreground text-xs font-medium">
              {chunk.speaker}
            </span>
          )}
          <span className="text-muted-foreground ml-auto flex items-center gap-1 text-xs">
            changed by:
            {chunk.steps.map((step, index) => (
              <Badge
                key={`${step.name}-${index}`}
                variant="secondary"
                className="font-mono text-[10px]"
              >
                {step.name}
              </Badge>
            ))}
          </span>
        </div>

        <ChunkDiff before={chunk.before} after={chunk.after} />

        {chunk.steps.length > 1 && (
          <div>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
              onClick={() => setStepsOpen((open) => !open)}
            >
              <ChevronDown
                className={`h-3 w-3 transition-transform ${stepsOpen ? 'rotate-180' : ''}`}
              />
              Step-by-step changes
            </button>
            {stepsOpen && (
              <div className="mt-2 space-y-2 border-l-2 pl-3">
                {chunk.steps.map((step, index) => (
                  <div key={`${step.name}-${index}`}>
                    <Badge
                      variant="secondary"
                      className="mb-1 font-mono text-[10px]"
                    >
                      {step.name}
                    </Badge>
                    <ChunkDiff before={step.before} after={step.after} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
