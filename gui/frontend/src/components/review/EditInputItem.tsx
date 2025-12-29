import { ChevronDown, Loader2, RefreshCw, X } from 'lucide-react';
import { useCallback, useEffect } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { useCreateTask } from '@/hooks/mutations/useTasks';
import { useTaskStatus } from '@/hooks/queries/useTaskStatus';
import type {
  EditInputInstance,
  ProblemClipInfo,
  VariantInfo,
} from '@/types/review';

import { VariantList } from './VariantList';

// Timeout for generation - spinner will stop after this even if variants haven't arrived
const GENERATION_TIMEOUT_MS = 45000;

interface EditInputItemProps {
  /** The edit input instance state */
  input: EditInputInstance;
  /** Original clip info for regeneration config */
  clip: ProblemClipInfo;
  /** Project name for commit operations */
  projectName: string;
  /** Update this input instance */
  onUpdate: (updates: Partial<EditInputInstance>) => void;
  /** Remove this input instance */
  onRemove: () => void;
}

/**
 * A self-contained edit input with its own task polling and variant streaming.
 * Each instance manages generation independently.
 */
export function EditInputItem({
  input,
  clip,
  projectName,
  onUpdate,
  onRemove,
}: EditInputItemProps) {
  const createTask = useCreateTask();
  const { data: taskStatus } = useTaskStatus(input.currentTaskId ?? undefined);

  // Check if generation has timed out
  const hasTimedOut = input.generationStartTime
    ? Date.now() - input.generationStartTime > GENERATION_TIMEOUT_MS
    : false;

  // Spinner shows until variants are received or timeout
  const isGenerating =
    createTask.isPending ||
    taskStatus?.status === 'pending' ||
    taskStatus?.status === 'running' ||
    (input.isAwaitingVariants && !hasTimedOut);

  // Generate variants
  const handleGenerate = useCallback(async () => {
    try {
      // Set awaiting state before starting generation
      onUpdate({
        isAwaitingVariants: true,
        generationStartTime: Date.now(),
        processedUrls: new Set(),
      });

      const response = await createTask.mutateAsync({
        provider: clip.provider,
        config: clip.speakerConfig,
        text: input.text,
        variants: input.variantCount,
      });

      onUpdate({ currentTaskId: response.task_id });
    } catch (error) {
      console.error('Failed to generate variants:', error);
      onUpdate({
        isAwaitingVariants: false,
        generationStartTime: null,
      });
    }
  }, [
    createTask,
    clip.provider,
    clip.speakerConfig,
    input.text,
    input.variantCount,
    onUpdate,
  ]);

  // Stream variants as they arrive - process only new URLs
  useEffect(() => {
    const urls = taskStatus?.audio_urls || [];
    const newUrls = urls.filter((url) => !input.processedUrls.has(url));

    if (newUrls.length > 0) {
      const newVariants: VariantInfo[] = newUrls.map((url, index) => ({
        id: `${input.id}-variant-${input.processedUrls.size + index}-${Date.now()}`,
        audioUrl: url,
        filePath: url.replace(/^.*\/static\//, ''),
        committed: false,
      }));

      const updatedProcessedUrls = new Set([
        ...input.processedUrls,
        ...newUrls,
      ]);
      onUpdate({
        variants: [...input.variants, ...newVariants],
        processedUrls: updatedProcessedUrls,
      });
    }
  }, [
    taskStatus?.audio_urls,
    input.id,
    input.processedUrls,
    input.variants,
    onUpdate,
  ]);

  // Handle task completion - clear awaiting state
  useEffect(() => {
    if (taskStatus?.status === 'completed' && input.currentTaskId) {
      onUpdate({
        isAwaitingVariants: false,
        generationStartTime: null,
        currentTaskId: null,
      });
    }
  }, [taskStatus?.status, input.currentTaskId, onUpdate]);

  // Timeout effect - clear awaiting state after timeout
  useEffect(() => {
    if (!input.generationStartTime) return;

    const timeRemaining =
      GENERATION_TIMEOUT_MS - (Date.now() - input.generationStartTime);
    if (timeRemaining <= 0) {
      onUpdate({
        isAwaitingVariants: false,
        generationStartTime: null,
      });
      return;
    }

    const timeoutId = setTimeout(() => {
      onUpdate({
        isAwaitingVariants: false,
        generationStartTime: null,
      });
    }, timeRemaining);

    return () => clearTimeout(timeoutId);
  }, [input.generationStartTime, onUpdate]);

  // Handle task failure - clear awaiting state
  useEffect(() => {
    if (taskStatus?.status === 'failed') {
      onUpdate({
        isAwaitingVariants: false,
        generationStartTime: null,
        currentTaskId: null,
      });
    }
  }, [taskStatus?.status, onUpdate]);

  // Handle variant removal
  const handleRemoveVariant = useCallback(
    (variantId: string) => {
      onUpdate({
        variants: input.variants.filter((v) => v.id !== variantId),
      });
    },
    [input.variants, onUpdate]
  );

  // Handle variant commit
  const handleCommitVariant = useCallback(
    (variantId: string) => {
      onUpdate({
        variants: input.variants.map((v) =>
          v.id === variantId ? { ...v, committed: true } : v
        ),
      });
    },
    [input.variants, onUpdate]
  );

  const hasChanges = input.text !== clip.text;

  return (
    <div className="space-y-2">
      <Input
        value={input.text}
        onChange={(e) => onUpdate({ text: e.target.value })}
        placeholder="Edit text for pronunciation adjustments..."
        className="text-sm"
        disabled={isGenerating}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Reset to original */}
          {hasChanges && (
            <button
              className={`${appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })} text-muted-foreground text-xs`}
              onClick={() => onUpdate({ text: clip.text })}
              disabled={isGenerating}
            >
              Reset
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Remove this input */}
          <button
            className={appButtonVariants({ variant: 'secondary', size: 'sm' })}
            onClick={onRemove}
            disabled={isGenerating}
          >
            <X className="mr-1 h-4 w-4" />
            Remove
          </button>

          {/* Variants dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
                disabled={isGenerating}
              >
                {input.variantCount} variant
                {input.variantCount !== 1 ? 's' : ''}
                <ChevronDown className="ml-1 h-3 w-3" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {[1, 2, 3, 4, 5].map((count) => (
                <DropdownMenuItem
                  key={count}
                  onClick={() => onUpdate({ variantCount: count })}
                >
                  {count} variant{count !== 1 ? 's' : ''}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Generate button */}
          <button
            className={appButtonVariants({ variant: 'primary', size: 'sm' })}
            onClick={handleGenerate}
            disabled={isGenerating || !input.text.trim()}
          >
            {isGenerating ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-1 h-4 w-4" />
            )}
            Generate
          </button>
        </div>
      </div>

      {/* Variants for this input */}
      {input.variants.length > 0 && (
        <VariantList
          variants={input.variants}
          projectName={projectName}
          targetCacheFilename={clip.cacheFilename}
          onRemove={handleRemoveVariant}
          onCommit={handleCommitVariant}
        />
      )}
    </div>
  );
}
