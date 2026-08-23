import { AlertTriangle, ArrowDownToLine } from 'lucide-react';
import { lazy, Suspense, useCallback, useMemo, useRef, useState } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { useSequentialPlayback } from '@/hooks/audio/useSequentialPlayback';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import type {
  ChunkInventoryEntry,
  ChunkInventoryResponse,
} from '@/types/chunks';

import { ChunkDetailPanel } from './ChunkDetailPanel';
import { ChunkListView } from './ChunkListView';
import type { ViewerLensHandle } from './lensHandle';
import { PdfLensLoading } from './pdf/PdfLensLoading';
import { buildPositionByIdx } from './viewerLogic';
import { type ViewerLens, ViewerToolbar } from './ViewerToolbar';

// The PDF lens pulls in react-pdf + pdf.js (large); load it only when opened.
const PdfLens = lazy(() => import('./pdf/PdfLens'));

const EMPTY_ENTRIES: ChunkInventoryEntry[] = [];

interface ScreenplayViewerProps {
  /** Full chunk inventory (undefined while loading or before first fetch) */
  inventory?: ChunkInventoryResponse | undefined;
  projectName: string;
  /** Whether the project has a source PDF (enables the PDF overlay lens) */
  hasPdf?: boolean | undefined;
  /** Whether currently loading/refreshing */
  isLoading?: boolean | undefined;
  /** Callback to refresh the data (forces a server-side recompute) */
  onRefresh?: (() => void | Promise<unknown>) | undefined;
  /** Whether the controls are disabled (e.g., voice casting incomplete) */
  disabled?: boolean | undefined;
  /** Reason why the controls are disabled, shown in tooltip */
  disabledReason?: string | undefined;
  /** Warning message to show above the list */
  warningMessage?: string | undefined;
}

/**
 * Screenplay viewer shell: hosts the List | PDF lens toggle, the chunk
 * selection + detail panel, and the sequential-playback controller, delegating
 * the actual rendering to ChunkListView (virtualized reading list) or the lazy
 * PdfLens (PDF overlay). Selection, playback, and the reading anchor (the
 * chunk at the top of the viewport) live here so they survive lens switches;
 * each lens reflects them via props, restores the reading position on mount,
 * and reports user scrolling back up.
 *
 * Selection and the reading anchor are stored as chunk idx (stable identity),
 * not list position: an inventory refresh that inserts or removes chunks must
 * not silently retarget the detail panel or the scroll restore.
 */
export function ScreenplayViewer({
  inventory,
  projectName,
  hasPdf = false,
  isLoading = false,
  onRefresh,
  disabled = false,
  disabledReason,
  warningMessage,
}: ScreenplayViewerProps) {
  const entries = inventory?.entries ?? EMPTY_ENTRIES;
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [selectedRegionIdxs, setSelectedRegionIdxs] = useState<number[] | null>(
    null
  );
  const [lens, setLens] = useState<ViewerLens>('list');
  const [isRefreshing, setIsRefreshing] = useState(false);
  // Auto-scroll to the active chunk during sequential playback; user
  // scrolling turns it off until "Jump to current" or a new playFrom
  const [followPlayback, setFollowPlayback] = useState(true);
  const lensRef = useRef<ViewerLensHandle | null>(null);

  const getAudioUrl = useCallback(
    (entry: ChunkInventoryEntry) =>
      apiService.getCacheAudioUrl(projectName, entry.cacheFilename),
    [projectName]
  );
  const sequential = useSequentialPlayback({ entries, getAudioUrl });
  const { playFrom } = sequential;

  // Occurrence chips and PDF anchors address chunks by task idx; resolve to
  // list position (identical for the full inventory, but not for future lenses)
  const positionByIdx = useMemo(() => buildPositionByIdx(entries), [entries]);

  // --- Reading anchor: the chunk idx at the top of the viewport ------------
  // Written on genuine user scrolls (either lens), read when a lens mounts so
  // toggling List <-> PDF keeps the reading position, and both lenses stay in
  // sync. Persisted per project for the tab session so navigating away from
  // the viewer and back also restores the place.
  const anchorStorageKey = `sts:viewer-reading-anchor:${projectName}`;
  const readingAnchorIdxRef = useRef<number | null>(null);
  const anchorInitializedRef = useRef(false);
  if (!anchorInitializedRef.current) {
    anchorInitializedRef.current = true;
    try {
      const stored = window.sessionStorage.getItem(anchorStorageKey);
      const parsed = stored === null ? Number.NaN : Number.parseInt(stored, 10);
      readingAnchorIdxRef.current = Number.isNaN(parsed) ? null : parsed;
    } catch {
      readingAnchorIdxRef.current = null;
    }
  }
  const setReadingAnchor = useCallback(
    (idx: number | null) => {
      readingAnchorIdxRef.current = idx;
      try {
        if (idx === null) {
          window.sessionStorage.removeItem(anchorStorageKey);
        } else {
          window.sessionStorage.setItem(anchorStorageKey, String(idx));
        }
      } catch {
        // Storage unavailable (private mode) - the in-memory anchor still works
      }
    },
    [anchorStorageKey]
  );

  // Live mirrors so getRestorePosition can stay identity-stable while lenses
  // call it at arbitrary times (the PDF lens restores only once its document
  // has rendered)
  const positionByIdxRef = useRef(positionByIdx);
  positionByIdxRef.current = positionByIdx;
  const followPlaybackRef = useRef(followPlayback);
  followPlaybackRef.current = followPlayback;
  const activeIndexRef = useRef(sequential.activeIndex);
  activeIndexRef.current = sequential.activeIndex;
  const selectedIdxRef = useRef(selectedIdx);
  selectedIdxRef.current = selectedIdx;

  /** Where a freshly mounted lens should land: the followed active chunk,
   * else the reading anchor, else the selection, else the top. */
  const getRestorePosition = useCallback((): number | null => {
    if (activeIndexRef.current !== null && followPlaybackRef.current) {
      return activeIndexRef.current;
    }
    const anchorIdx = readingAnchorIdxRef.current;
    if (anchorIdx !== null) {
      const position = positionByIdxRef.current.get(anchorIdx);
      if (position !== undefined) return position;
    }
    const selected = selectedIdxRef.current;
    if (selected !== null) {
      const position = positionByIdxRef.current.get(selected);
      if (position !== undefined) return position;
    }
    return null;
  }, []);

  const handlePlayFromHere = useCallback(
    (position: number) => {
      setFollowPlayback(true);
      playFrom(position);
    },
    [playFrom]
  );

  const handleSelect = useCallback(
    (position: number, regionPositions?: number[]) => {
      const entry = entries[position];
      if (!entry) return;
      setSelectedIdx(entry.idx);
      const regionIdxs = (regionPositions ?? [])
        .map((regionPosition) => entries[regionPosition]?.idx)
        .filter((idx): idx is number => idx !== undefined);
      setSelectedRegionIdxs(regionIdxs.length > 1 ? regionIdxs : null);
    },
    [entries]
  );

  const handleJumpToChunk = useCallback(
    (idx: number) => {
      const position = positionByIdx.get(idx);
      if (position === undefined) return;
      setSelectedIdx(idx);
      setSelectedRegionIdxs(null);
      setReadingAnchor(idx);
      lensRef.current?.scrollToPosition(position);
    },
    [positionByIdx, setReadingAnchor]
  );

  const jumpToCurrent = useCallback(() => {
    setFollowPlayback(true);
    if (sequential.activeIndex !== null) {
      lensRef.current?.scrollToPosition(sequential.activeIndex);
    }
  }, [sequential.activeIndex]);

  // Genuine user scrolling: remember the reading position and, while playback
  // is active, stop auto-following it
  const handleUserScroll = useCallback(
    (topPosition: number | null) => {
      if (topPosition !== null) {
        const idx = entries[topPosition]?.idx;
        if (idx !== undefined) setReadingAnchor(idx);
      }
      if (sequential.isActive) {
        setFollowPlayback(false);
      }
    },
    [entries, sequential.isActive, setReadingAnchor]
  );

  const handleLensChange = useCallback((next: ViewerLens) => {
    // Scroll position carries over via the reading anchor; follow state is
    // deliberately kept as-is so a user reading ahead of playback isn't
    // yanked to the active chunk by a lens switch
    setLens(next);
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const requests: Promise<unknown>[] = [];
      if (onRefresh) requests.push(Promise.resolve(onRefresh()));
      const lensRefresh = lensRef.current?.refresh;
      if (lensRefresh) requests.push(lensRefresh());
      await Promise.allSettled(requests);
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh]);

  const hasInventory = !!inventory;
  const speakerConfigs = useMemo(
    () => inventory?.speakerConfigs ?? {},
    [inventory]
  );
  // The user's lens preference survives transient data gaps, but what renders
  // (and what the toolbar shows) always falls back to the list when the PDF
  // lens can't be shown - state and UI can't disagree
  const lensAvailable = hasPdf && hasInventory && entries.length > 0;
  const effectiveLens: ViewerLens =
    lens === 'pdf' && lensAvailable ? 'pdf' : 'list';

  // Resolve idx-based selection to positions/entries for the current inventory
  const selectedPosition =
    selectedIdx !== null ? (positionByIdx.get(selectedIdx) ?? null) : null;
  const selectedEntry =
    selectedPosition !== null ? entries[selectedPosition] : undefined;
  const selectedRegionPositions = useMemo(
    () =>
      (selectedRegionIdxs ?? [])
        .map((idx) => positionByIdx.get(idx))
        .filter((position): position is number => position !== undefined),
    [selectedRegionIdxs, positionByIdx]
  );
  const selectedRegionEntries = useMemo(
    () =>
      selectedRegionPositions
        .map((position) => entries[position])
        .filter((entry): entry is ChunkInventoryEntry => entry !== undefined),
    [entries, selectedRegionPositions]
  );

  // Selection is user-driven only: sequential playback moving through a
  // selected composite region must NOT retarget the panel to the active
  // constituent - the panel is keyed by chunk idx, so retargeting would
  // remount it and discard in-progress editor state. The page overlay already
  // highlights the active region during playback.

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <ViewerToolbar
        inventory={inventory}
        isLoading={isLoading || isRefreshing}
        onRefresh={onRefresh ? () => void handleRefresh() : undefined}
        disabled={disabled}
        disabledReason={disabledReason}
        isSequentialActive={sequential.isActive}
        onPlayAll={() => handlePlayFromHere(0)}
        onStop={sequential.stop}
        lens={effectiveLens}
        onLensChange={handleLensChange}
        showLensToggle={lensAvailable}
      />

      {warningMessage && (
        <div className="bg-muted text-muted-foreground flex items-center gap-2 rounded-md p-3 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{warningMessage}</span>
        </div>
      )}

      <div className="border-border relative flex min-h-0 flex-1 overflow-hidden rounded-lg border">
        {effectiveLens === 'pdf' ? (
          <Suspense fallback={<PdfLensLoading />}>
            <PdfLens
              ref={lensRef}
              entries={entries}
              projectName={projectName}
              activeIndex={sequential.activeIndex}
              selectedIndex={selectedPosition}
              followPlayback={followPlayback}
              positionByIdx={positionByIdx}
              chunkLayoutRevision={inventory?.chunkLayoutRevision ?? ''}
              onSelect={handleSelect}
              onUserScroll={handleUserScroll}
              getRestorePosition={getRestorePosition}
            />
          </Suspense>
        ) : (
          <ChunkListView
            ref={lensRef}
            entries={entries}
            projectName={projectName}
            activeIndex={sequential.activeIndex}
            selectedIndex={selectedPosition}
            followPlayback={followPlayback}
            onSelect={handleSelect}
            onPlayFromHere={handlePlayFromHere}
            onUserScroll={handleUserScroll}
            getRestorePosition={getRestorePosition}
            isLoading={isLoading}
            hasInventory={hasInventory}
          />
        )}

        {/* Persistent split detail panel */}
        {selectedEntry && (
          <div className="border-border w-[420px] shrink-0 border-l xl:w-[480px]">
            <ChunkDetailPanel
              key={selectedEntry.idx}
              entry={selectedEntry}
              speakerConfigs={speakerConfigs}
              projectName={projectName}
              cacheFolder={inventory?.cacheFolder ?? ''}
              onJumpToChunk={handleJumpToChunk}
              onPlayFromHere={(idx) => {
                const position = positionByIdx.get(idx);
                if (position !== undefined) handlePlayFromHere(position);
              }}
              regionEntries={selectedRegionEntries}
              onSelectRegionEntry={(idx) => setSelectedIdx(idx)}
              onClose={() => {
                setSelectedIdx(null);
                setSelectedRegionIdxs(null);
              }}
            />
          </div>
        )}

        {/* Re-enable auto-follow after the user scrolled away mid-playback */}
        {sequential.isActive && !followPlayback && (
          <button
            className={cn(
              appButtonVariants({ variant: 'primary', size: 'sm' }),
              'absolute bottom-4 left-1/2 -translate-x-1/2 shadow-lg'
            )}
            onClick={jumpToCurrent}
          >
            <ArrowDownToLine className="mr-2 h-4 w-4" />
            Jump to current
          </button>
        )}
      </div>
    </div>
  );
}
