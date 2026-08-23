import {
  BookOpen,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Square,
} from 'lucide-react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { formatRelativeTime } from '@/lib/formatRelativeTime';
import type { ChunkInventoryResponse } from '@/types/chunks';

export type ViewerLens = 'list' | 'pdf';

interface ViewerToolbarProps {
  inventory?: ChunkInventoryResponse | undefined;
  isLoading?: boolean | undefined;
  onRefresh?: (() => void) | undefined;
  /** Whether the controls are disabled (e.g., voice casting incomplete) */
  disabled?: boolean | undefined;
  /** Reason why the controls are disabled, shown in tooltip */
  disabledReason?: string | undefined;
  isSequentialActive: boolean;
  onPlayAll: () => void;
  onStop: () => void;
  /** Active lens (list vs. PDF overlay) */
  lens: ViewerLens;
  onLensChange: (lens: ViewerLens) => void;
  /** Whether to show the List | PDF toggle (hidden for text-only projects) */
  showLensToggle: boolean;
}

/**
 * Toolbar for the screenplay viewer: play-all/stop sequential playback,
 * inventory status counts, and the refresh control.
 */
export function ViewerToolbar({
  inventory,
  isLoading = false,
  onRefresh,
  disabled = false,
  disabledReason,
  isSequentialActive,
  onPlayAll,
  onStop,
  lens,
  onLensChange,
  showLensToggle,
}: ViewerToolbarProps) {
  const playAllDisabled = disabled || !inventory || inventory.cachedCount === 0;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {showLensToggle && (
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          value={lens}
          onValueChange={(value) => {
            if (value === 'list' || value === 'pdf') onLensChange(value);
          }}
        >
          <ToggleGroupItem value="list" aria-label="List view">
            <FileText className="mr-1.5 h-4 w-4" />
            List
          </ToggleGroupItem>
          <ToggleGroupItem value="pdf" aria-label="PDF view">
            <BookOpen className="mr-1.5 h-4 w-4" />
            PDF
          </ToggleGroupItem>
        </ToggleGroup>
      )}

      {isSequentialActive ? (
        <button
          className={appButtonVariants({ variant: 'secondary', size: 'sm' })}
          onClick={onStop}
        >
          <Square className="mr-2 h-4 w-4" />
          Stop
        </button>
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className={playAllDisabled ? 'cursor-not-allowed' : ''}>
              <button
                className={appButtonVariants({
                  variant: 'primary',
                  size: 'sm',
                })}
                onClick={onPlayAll}
                disabled={playAllDisabled}
                style={playAllDisabled ? { pointerEvents: 'none' } : undefined}
              >
                <Play className="mr-2 h-4 w-4" />
                Play all
              </button>
            </span>
          </TooltipTrigger>
          {playAllDisabled && (
            <TooltipContent>
              {disabled && disabledReason
                ? disabledReason
                : 'No cached audio to play'}
            </TooltipContent>
          )}
        </Tooltip>
      )}

      {inventory && (
        <span className="text-muted-foreground text-sm">
          {inventory.totalChunks} chunks · {inventory.cachedCount} cached ·{' '}
          {inventory.missingCount} missing · {inventory.userModifiedCount}{' '}
          user-modified
        </span>
      )}

      <div className="ml-auto flex items-center gap-2">
        {inventory?.generatedAt && (
          <span className="text-muted-foreground text-xs">
            Last refreshed: {formatRelativeTime(inventory.generatedAt)}
          </span>
        )}
        {onRefresh && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className={disabled ? 'cursor-not-allowed' : ''}>
                <button
                  className={appButtonVariants({
                    variant: 'secondary',
                    size: 'sm',
                  })}
                  onClick={onRefresh}
                  disabled={isLoading || disabled}
                  style={disabled ? { pointerEvents: 'none' } : undefined}
                >
                  {isLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Refresh
                </button>
              </span>
            </TooltipTrigger>
            {disabled && disabledReason && (
              <TooltipContent>{disabledReason}</TooltipContent>
            )}
          </Tooltip>
        )}
      </div>
    </div>
  );
}
