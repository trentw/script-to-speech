import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { ChunkInventoryResponse } from '@/types/chunks';

import {
  ALL_FILTER,
  buildProblemClip,
  type ChunkStatusFilter,
  dedupeEntriesByCacheFilename,
  filterChunkEntries,
  getChunkTypeOptions,
  getSpeakerOptions,
  hasActiveSearch,
} from './chunkSearch';
import { DialogueItem } from './DialogueItem';

/** Cap on rendered results to avoid unbounded lists */
const MAX_DISPLAYED_RESULTS = 50;

const STATUS_FILTER_OPTIONS: { value: ChunkStatusFilter; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'cached', label: 'Cached' },
  { value: 'missing', label: 'Missing' },
  { value: 'user-modified', label: 'User-modified' },
];

const STATUS_LABELS: Record<string, string> = {
  cached: 'cached',
  missing: 'missing',
  expected_silence: 'expected silence',
};

interface ChunkSearchSectionProps {
  /** Full chunk inventory (undefined while loading or before first fetch) */
  inventory?: ChunkInventoryResponse;
  projectName: string;
  cacheFolder: string;
  /** Whether currently loading/refreshing */
  isLoading?: boolean;
  /** Callback to refresh the data (forces a server-side recompute) */
  onRefresh?: () => void;
  /** Whether the refresh button is disabled (e.g., voice casting incomplete) */
  disabled?: boolean;
  /** Reason why the refresh button is disabled, shown in tooltip */
  disabledReason?: string;
  /** Warning message to show above the results */
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
 * Search section for the Review Audio page: find any screenplay chunk by
 * text/speaker/type/status and re-record it with the existing clip-card UI.
 */
export function ChunkSearchSection({
  inventory,
  projectName,
  cacheFolder,
  isLoading = false,
  onRefresh,
  disabled = false,
  disabledReason,
  warningMessage,
}: ChunkSearchSectionProps) {
  const [query, setQuery] = useState('');
  const [speaker, setSpeaker] = useState<string>(ALL_FILTER);
  const [chunkType, setChunkType] = useState<string>(ALL_FILTER);
  const [status, setStatus] = useState<ChunkStatusFilter>('all');

  const entries = useMemo(() => inventory?.entries ?? [], [inventory]);

  const speakerOptions = useMemo(() => getSpeakerOptions(entries), [entries]);
  const chunkTypeOptions = useMemo(
    () => getChunkTypeOptions(entries),
    [entries]
  );

  // No results without an active query (search text or a non-default
  // filter) - an empty search box must not list the whole screenplay
  const isSearchActive = hasActiveSearch({ query, speaker, chunkType, status });

  // Filter, then collapse chunks sharing the same cache audio file so each
  // unique audio file renders exactly one card
  const uniqueEntries = useMemo(() => {
    if (!isSearchActive) return [];
    return dedupeEntriesByCacheFilename(
      filterChunkEntries(entries, { query, speaker, chunkType, status })
    );
  }, [entries, query, speaker, chunkType, status, isSearchActive]);

  const displayedEntries = uniqueEntries.slice(0, MAX_DISPLAYED_RESULTS);
  const hasInventory = !!inventory;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle>
              <span>Find Chunks</span>
            </CardTitle>
            <p className="text-muted-foreground mt-1 text-sm">
              Search all screenplay chunks and re-record any of them.
              {hasInventory &&
                ` ${inventory.totalChunks} chunks: ${inventory.cachedCount} cached, ${inventory.missingCount} missing, ${inventory.userModifiedCount} user-modified.`}
            </p>
          </div>
          {onRefresh && (
            <div className="flex w-fit flex-col items-end gap-1">
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
              {inventory?.generatedAt && (
                <span className="text-muted-foreground text-xs">
                  Last refreshed: {formatRelativeTime(inventory.generatedAt)}
                </span>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Warning banner (shown when voice casting incomplete) */}
        {warningMessage && (
          <div className="bg-muted text-muted-foreground mb-4 flex items-center gap-2 rounded-md p-3 text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{warningMessage}</span>
          </div>
        )}

        {/* Search + filter controls */}
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search dialogue text or speaker..."
            className="text-sm sm:flex-1"
            aria-label="Search chunks"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Select value={speaker} onValueChange={setSpeaker}>
              <SelectTrigger
                className="w-[150px]"
                aria-label="Filter by speaker"
              >
                <SelectValue placeholder="Speaker" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>All speakers</SelectItem>
                {speakerOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={chunkType} onValueChange={setChunkType}>
              <SelectTrigger className="w-[150px]" aria-label="Filter by type">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>All types</SelectItem>
                {chunkTypeOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={status}
              onValueChange={(value) => setStatus(value as ChunkStatusFilter)}
            >
              <SelectTrigger
                className="w-[150px]"
                aria-label="Filter by status"
              >
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_FILTER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Loading state (initial fetch) */}
        {isLoading && !hasInventory && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            <span className="text-muted-foreground ml-2">
              Loading chunk inventory...
            </span>
          </div>
        )}

        {/* Not loaded state (e.g., voice casting incomplete) */}
        {!hasInventory && !isLoading && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            No chunk inventory loaded. Click Refresh to load it.
          </p>
        )}

        {/* Inactive state (inventory loaded, no search text or filters yet) */}
        {hasInventory && !isSearchActive && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            Search by text, or filter by speaker, type, or status
          </p>
        )}

        {/* Empty state (active search but nothing matches) */}
        {hasInventory && isSearchActive && uniqueEntries.length === 0 && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            No chunks match your search
          </p>
        )}

        {/* Results - one card per unique cache audio file */}
        {hasInventory && isSearchActive && uniqueEntries.length > 0 && (
          <div className="space-y-3">
            <p className="text-muted-foreground text-xs">
              Showing {displayedEntries.length} of {uniqueEntries.length}{' '}
              matching audio file{uniqueEntries.length !== 1 ? 's' : ''}
              {uniqueEntries.length > displayedEntries.length
                ? ' - narrow your search to see the rest'
                : ''}
            </p>
            {displayedEntries.map((entry) => (
              <div
                key={entry.cacheFilename}
                className="border-border rounded-lg border"
              >
                <div className="flex items-center gap-2 px-3 pt-2 text-xs">
                  <span className="font-medium">{entry.speakerDisplay}</span>
                  <Badge variant="outline" className="text-xs">
                    {entry.chunkType}
                  </Badge>
                  <Badge
                    variant={
                      entry.status === 'missing' ? 'destructive' : 'secondary'
                    }
                    className="text-xs"
                  >
                    {STATUS_LABELS[entry.status] ?? entry.status}
                  </Badge>
                  {/* A collapsed card represents several chunks, so a single
                      chunk number would misleadingly imply one specific
                      occurrence could be re-recorded */}
                  {entry.occurrences.length === 1 && (
                    <span className="text-muted-foreground ml-auto">
                      chunk #{entry.idx}
                    </span>
                  )}
                </div>
                <div className="p-2">
                  <DialogueItem
                    clip={buildProblemClip(entry, inventory.speakerConfigs)}
                    projectName={projectName}
                    cacheFolder={cacheFolder}
                    showPlayExisting={entry.status === 'cached'}
                    occurrenceCount={entry.occurrences.length}
                    userModified={entry.userModified}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
