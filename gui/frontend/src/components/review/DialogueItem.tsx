import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Circle,
  Edit2,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

// Timeout for generation - spinner will stop after this even if variants haven't arrived
const GENERATION_TIMEOUT_MS = 45000;

import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useCreateTask } from '@/hooks/mutations/useTasks';
import { useTaskStatus } from '@/hooks/queries/useTaskStatus';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import type {
  EditInputInstance,
  ProblemClipInfo,
  VariantInfo,
} from '@/types/review';

import { EditInputItem } from './EditInputItem';
import { VariantList } from './VariantList';

interface DialogueItemProps {
  clip: ProblemClipInfo;
  projectName: string;
  cacheFolder: string;
  showDbfs?: boolean;
}

/**
 * Displays a single dialogue clip with controls for playback, editing, and regeneration.
 * Supports multiple edit inputs for generating variants with modified text.
 */
export function DialogueItem({
  clip,
  projectName,
  cacheFolder: _cacheFolder,
  showDbfs = false,
}: DialogueItemProps) {
  // Multiple edit inputs - each manages its own generation
  const [editInputs, setEditInputs] = useState<EditInputInstance[]>([]);

  // State for main "Regenerate" button (uses original text)
  const [variantCount, setVariantCount] = useState(1);
  const [variants, setVariants] = useState<VariantInfo[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isAwaitingVariants, setIsAwaitingVariants] = useState(false);
  const [generationStartTime, setGenerationStartTime] = useState<number | null>(
    null
  );
  const [processedUrls, setProcessedUrls] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const createTask = useCreateTask();
  const { data: taskStatus } = useTaskStatus(currentTaskId ?? undefined);

  // Check if generation has timed out
  const hasTimedOut = generationStartTime
    ? Date.now() - generationStartTime > GENERATION_TIMEOUT_MS
    : false;

  // Spinner shows until variants are received or timeout
  const isGenerating =
    createTask.isPending ||
    taskStatus?.status === 'pending' ||
    taskStatus?.status === 'running' ||
    (isAwaitingVariants && !hasTimedOut);

  // Get audio URL for existing cache file (silent clips)
  const existingAudioUrl = apiService.getCacheAudioUrl(
    projectName,
    clip.cacheFilename
  );

  // Play existing audio
  const handlePlayExisting = useCallback(() => {
    const audio = new Audio(existingAudioUrl);
    audio.play().catch(console.error);
  }, [existingAudioUrl]);

  // Add a new edit input instance
  const addEditInput = useCallback(() => {
    const newInput: EditInputInstance = {
      id: crypto.randomUUID(),
      text: clip.text,
      variantCount: 1,
      currentTaskId: null,
      isAwaitingVariants: false,
      generationStartTime: null,
      variants: [],
      processedUrls: new Set(),
      error: null,
    };
    setEditInputs((prev) => [...prev, newInput]);
  }, [clip.text]);

  // Update a specific edit input
  const updateEditInput = useCallback(
    (inputId: string, updates: Partial<EditInputInstance>) => {
      setEditInputs((prev) =>
        prev.map((input) =>
          input.id === inputId ? { ...input, ...updates } : input
        )
      );
    },
    []
  );

  // Remove an edit input
  const removeEditInput = useCallback((inputId: string) => {
    setEditInputs((prev) => prev.filter((input) => input.id !== inputId));
  }, []);

  // Generate variants with original text (main Regenerate button)
  const handleRegenerate = useCallback(async () => {
    try {
      // Clear any previous error when starting a new generation
      setError(null);
      setIsAwaitingVariants(true);
      setGenerationStartTime(Date.now());
      setProcessedUrls(new Set());

      const response = await createTask.mutateAsync({
        provider: clip.provider,
        config: clip.speakerConfig,
        text: clip.text,
        variants: variantCount,
      });

      setCurrentTaskId(response.task_id);
    } catch (err) {
      console.error('Failed to generate variants:', err);
      setError(
        err instanceof Error ? err.message : 'Failed to start generation'
      );
      setIsAwaitingVariants(false);
      setGenerationStartTime(null);
    }
  }, [createTask, clip.provider, clip.speakerConfig, clip.text, variantCount]);

  // Stream variants as they arrive - process only new URLs
  useEffect(() => {
    const urls = taskStatus?.audio_urls || [];
    const newUrls = urls.filter((url) => !processedUrls.has(url));

    if (newUrls.length > 0) {
      const newVariants: VariantInfo[] = newUrls.map((url, index) => ({
        id: `${clip.cacheFilename}-variant-${processedUrls.size + index}-${Date.now()}`,
        audioUrl: url,
        filePath: url.replace(/^.*\/static\//, ''),
        committed: false,
      }));

      setVariants((prev) => [...prev, ...newVariants]);
      setProcessedUrls((prev) => new Set([...prev, ...newUrls]));
    }
  }, [taskStatus?.audio_urls, clip.cacheFilename, processedUrls]);

  // Handle task completion - clear awaiting state
  useEffect(() => {
    if (taskStatus?.status === 'completed' && currentTaskId) {
      setIsAwaitingVariants(false);
      setGenerationStartTime(null);
      setCurrentTaskId(null);
    }
  }, [taskStatus?.status, currentTaskId]);

  // Timeout effect - clear awaiting state after timeout
  useEffect(() => {
    if (!generationStartTime) return;

    const timeRemaining =
      GENERATION_TIMEOUT_MS - (Date.now() - generationStartTime);
    if (timeRemaining <= 0) {
      setIsAwaitingVariants(false);
      setGenerationStartTime(null);
      setError('Generation timed out');
      return;
    }

    const timeoutId = setTimeout(() => {
      setIsAwaitingVariants(false);
      setGenerationStartTime(null);
      setError('Generation timed out');
    }, timeRemaining);

    return () => clearTimeout(timeoutId);
  }, [generationStartTime]);

  // Handle task failure - clear awaiting state and set error
  useEffect(() => {
    if (taskStatus?.status === 'failed') {
      setIsAwaitingVariants(false);
      setGenerationStartTime(null);
      setCurrentTaskId(null);
      setError(taskStatus.error || 'Generation failed');
    }
  }, [taskStatus?.status, taskStatus?.error]);

  // Handle variant removal (main variants)
  const handleRemoveVariant = useCallback((variantId: string) => {
    setVariants((prev) => prev.filter((v) => v.id !== variantId));
  }, []);

  // Handle variant commit (main variants)
  const handleCommitVariant = useCallback((variantId: string) => {
    setVariants((prev) =>
      prev.map((v) => (v.id === variantId ? { ...v, committed: true } : v))
    );
  }, []);

  // Truncate text for display
  const displayText =
    clip.text.length > 100 ? clip.text.slice(0, 100) + '...' : clip.text;

  const hasEditInputs = editInputs.length > 0;

  // Check if any variant has been committed (from main variants OR edit inputs)
  const hasCommittedVariant =
    variants.some((v) => v.committed) ||
    editInputs.some((input) => input.variants.some((v) => v.committed));

  return (
    <div
      className={cn(
        'rounded-md p-3',
        hasCommittedVariant
          ? 'border border-green-500/30 bg-green-500/5'
          : 'bg-muted/30'
      )}
    >
      {/* Main row: text + controls */}
      <div className="flex items-start gap-3">
        {/* Status indicator - leading */}
        <div className="flex shrink-0 items-center pt-0.5">
          {hasCommittedVariant ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Committed</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <Circle className="text-muted-foreground/40 h-4 w-4" />
          )}
        </div>

        {/* Text content */}
        <div className="min-w-0 flex-1">
          <p
            className={`text-sm leading-relaxed ${hasEditInputs ? 'text-muted-foreground' : ''}`}
            title={clip.text}
          >
            "{displayText}"
          </p>
          {showDbfs && clip.dbfsLevel !== null && (
            <Badge variant="outline" className="mt-1 text-xs">
              {clip.dbfsLevel.toFixed(1)} dBFS
            </Badge>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1">
          {/* Play cached audio (for silent clips or after variant is committed) */}
          {(showDbfs || hasCommittedVariant) && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={appButtonVariants({
                    variant: 'list-action',
                    size: 'icon-sm',
                  })}
                  onClick={handlePlayExisting}
                >
                  <Play className="h-3 w-3" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  {hasCommittedVariant
                    ? 'Play committed audio'
                    : 'Play existing audio'}
                </p>
              </TooltipContent>
            </Tooltip>
          )}

          {/* Edit/Add text input - toggles between Edit (no inputs) and Plus (has inputs) */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className={appButtonVariants({
                  variant: 'list-action',
                  size: 'icon-sm',
                })}
                onClick={addEditInput}
              >
                {hasEditInputs ? (
                  <Plus className="h-3 w-3" />
                ) : (
                  <Edit2 className="h-3 w-3" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{hasEditInputs ? 'Add another text variant' : 'Edit text'}</p>
            </TooltipContent>
          </Tooltip>

          {/* Variants dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
              >
                {variantCount}
                <ChevronDown className="ml-1 h-3 w-3" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {[1, 2, 3, 4, 5].map((count) => (
                <DropdownMenuItem
                  key={count}
                  onClick={() => setVariantCount(count)}
                >
                  {count} variant{count !== 1 ? 's' : ''}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Regenerate button - uses original text */}
          <button
            className={appButtonVariants({ variant: 'primary', size: 'sm' })}
            onClick={handleRegenerate}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-1 h-4 w-4" />
            )}
            Regenerate
          </button>
        </div>
      </div>

      {/* Error display for main regeneration */}
      {error && (
        <div className="border-destructive/30 bg-destructive/10 mt-2 flex items-center gap-2 rounded border px-3 py-2 text-sm">
          <AlertCircle className="text-destructive h-4 w-4 shrink-0" />
          {error.length > 60 ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-foreground flex-1 cursor-default">
                  {error.slice(0, 60)}...
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-md">
                <p className="whitespace-pre-wrap">{error}</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <span className="text-foreground flex-1">{error}</span>
          )}
          <button
            onClick={() => setError(null)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Dismiss error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Main variants list (from Regenerate button) - shown before edit inputs */}
      {variants.length > 0 && (
        <div className="mt-3">
          {hasEditInputs && (
            <div className="text-muted-foreground mb-1 text-xs">
              Original text:
            </div>
          )}
          <VariantList
            variants={variants}
            projectName={projectName}
            targetCacheFilename={clip.cacheFilename}
            onRemove={handleRemoveVariant}
            onCommit={handleCommitVariant}
          />
        </div>
      )}

      {/* Edit inputs - each is independent with its own generation */}
      {editInputs.map((input) => (
        <div key={input.id} className="border-muted mt-2 ml-4 border-l-2 pl-3">
          <EditInputItem
            input={input}
            clip={clip}
            projectName={projectName}
            onUpdate={(updates) => updateEditInput(input.id, updates)}
            onRemove={() => removeEditInput(input.id)}
          />
        </div>
      ))}
    </div>
  );
}
