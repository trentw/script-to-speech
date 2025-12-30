import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { useMemo } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ProblemClipInfo, SpeakerGroup } from '@/types/review';

import { SpeakerGroupComponent } from './SpeakerGroup';

interface ProblemClipsSectionProps {
  title: string;
  description: string;
  clips: ProblemClipInfo[];
  projectName: string;
  cacheFolder: string;
  showDbfs?: boolean;
  /** Empty state message when no clips but section should still show */
  emptyMessage?: string;
  /** Pre-scan state message (before first scan) */
  notScannedMessage?: string;
  /** Whether data has been scanned at least once */
  hasScanned?: boolean;
  /** ISO timestamp of when the scan was performed */
  scannedAt?: string;
  /** Whether currently loading/refreshing */
  isLoading?: boolean;
  /** Callback to refresh the data */
  onRefresh?: () => void;
  /** Whether the refresh button is disabled (e.g., voice casting incomplete) */
  disabled?: boolean;
  /** Reason why the refresh button is disabled, shown in tooltip */
  disabledReason?: string;
  /** Warning message to show above clips (e.g., when voice casting incomplete but cached data exists) */
  warningMessage?: string;
}

/**
 * Format relative time (e.g., "2 minutes ago")
 */
function formatRelativeTime(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);

  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Groups clips by speaker and displays them in a section.
 * Now includes refresh button and timestamp.
 */
export function ProblemClipsSection({
  title,
  description,
  clips,
  projectName,
  cacheFolder,
  showDbfs = false,
  emptyMessage = 'No issues detected',
  notScannedMessage,
  hasScanned = true,
  scannedAt,
  isLoading = false,
  onRefresh,
  disabled = false,
  disabledReason,
  warningMessage,
}: ProblemClipsSectionProps) {
  // Group clips by speaker
  const speakerGroups = useMemo(() => {
    const groups = new Map<string, SpeakerGroup>();

    for (const clip of clips) {
      const key = `${clip.speaker}:${clip.voiceId}:${clip.provider}`;

      if (!groups.has(key)) {
        groups.set(key, {
          speaker: clip.speaker,
          voiceId: clip.voiceId,
          provider: clip.provider,
          clips: [],
        });
      }

      groups.get(key)!.clips.push(clip);
    }

    // Sort by speaker name, then by clip count (descending)
    return Array.from(groups.values()).sort((a, b) => {
      if (a.speaker === b.speaker) {
        return b.clips.length - a.clips.length;
      }
      return a.speaker.localeCompare(b.speaker);
    });
  }, [clips]);

  const hasClips = clips.length > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <span>{title}</span>
              {hasClips && (
                <span className="text-muted-foreground text-sm font-normal">
                  ({clips.length} clip{clips.length !== 1 ? 's' : ''})
                </span>
              )}
            </CardTitle>
            <p className="text-muted-foreground mt-1 text-sm">{description}</p>
          </div>
          {onRefresh && (
            <div className="flex flex-col items-end gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  {/* Wrap button in span so tooltip works when button is disabled */}
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
                        <RefreshCw className={cn('mr-2 h-4 w-4')} />
                      )}
                      Refresh
                    </button>
                  </span>
                </TooltipTrigger>
                {disabled && disabledReason && (
                  <TooltipContent>{disabledReason}</TooltipContent>
                )}
              </Tooltip>
              {scannedAt && (
                <span className="text-muted-foreground text-xs">
                  Last refreshed: {formatRelativeTime(scannedAt)}
                </span>
              )}
              {!hasScanned && !scannedAt && (
                <span className="text-muted-foreground text-xs">
                  Not yet scanned
                </span>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Warning banner (shown when voice casting incomplete but cached data exists) */}
        {warningMessage && (
          <div className="bg-muted text-muted-foreground mb-4 flex items-center gap-2 rounded-md p-3 text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{warningMessage}</span>
          </div>
        )}

        {/* Loading state */}
        {isLoading && !hasClips && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            <span className="text-muted-foreground ml-2">Scanning...</span>
          </div>
        )}

        {/* Not scanned state */}
        {!hasScanned && !isLoading && notScannedMessage && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            {notScannedMessage}
          </p>
        )}

        {/* Empty state (after scanning) */}
        {hasScanned && !isLoading && !hasClips && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            {emptyMessage}
          </p>
        )}

        {/* Clips list */}
        {hasClips && (
          <div className="space-y-6">
            {speakerGroups.map((group) => (
              <SpeakerGroupComponent
                key={`${group.speaker}:${group.voiceId}:${group.provider}`}
                group={group}
                projectName={projectName}
                cacheFolder={cacheFolder}
                showDbfs={showDbfs}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
