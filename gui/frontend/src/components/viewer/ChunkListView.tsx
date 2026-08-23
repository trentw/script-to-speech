import { useVirtualizer } from '@tanstack/react-virtual';
import { Loader2 } from 'lucide-react';
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
} from 'react';

import type { ChunkInventoryEntry } from '@/types/chunks';

import { ChunkRow } from './ChunkRow';
import type { ViewerLensHandle } from './lensHandle';
import { useLensScroll } from './useLensScroll';
import { estimateRowSize } from './viewerLogic';

interface ChunkListViewProps {
  entries: ChunkInventoryEntry[];
  projectName: string;
  /** Row currently played by sequential playback (list position), or null */
  activeIndex: number | null;
  /** Row open in the detail panel (list position), or null */
  selectedIndex: number | null;
  /** Whether to auto-scroll to the active row during sequential playback */
  followPlayback: boolean;
  onSelect: (position: number) => void;
  onPlayFromHere: (position: number) => void;
  /** Fired on genuine user scroll with the topmost visible position, so the
   * shell can drop follow and track the reading anchor */
  onUserScroll: (topPosition: number | null) => void;
  /** Position to land on when the lens mounts (the shell's reading anchor /
   * active chunk / selection), or null for the top */
  getRestorePosition: () => number | null;
  isLoading: boolean;
  hasInventory: boolean;
}

/**
 * The virtualized, screenplay-styled reading list. Extracted from the viewer
 * shell so the PDF lens can slot in beside it; the shell owns selection and
 * sequential playback, which this view reflects via props. Exposes an
 * imperative scrollToPosition for occurrence-chip jumps and the shell's
 * "jump to current" affordance.
 */
export const ChunkListView = forwardRef<ViewerLensHandle, ChunkListViewProps>(
  function ChunkListView(
    {
      entries,
      projectName,
      activeIndex,
      selectedIndex,
      followPlayback,
      onSelect,
      onPlayFromHere,
      onUserScroll,
      getRestorePosition,
      isLoading,
      hasInventory,
    },
    ref
  ) {
    const scrollRef = useRef<HTMLDivElement | null>(null);

    const virtualizer = useVirtualizer({
      count: entries.length,
      getScrollElement: () => scrollRef.current,
      estimateSize: (index) => {
        const entry = entries[index];
        return entry ? estimateRowSize(entry) : 52;
      },
      overscan: 12,
      // Key measurements (and React rows) by chunk identity, not list
      // position, so an inventory refresh that inserts/removes chunks doesn't
      // attribute stale heights to the wrong rows
      getItemKey: (index) => entries[index]?.idx ?? index,
    });

    // Re-measure when the inventory itself changes: the same idx can render
    // at a different height after a text-processor config change
    const measuredEntriesRef = useRef(entries);
    useEffect(() => {
      if (measuredEntriesRef.current !== entries) {
        measuredEntriesRef.current = entries;
        virtualizer.measure();
      }
    }, [entries, virtualizer]);

    // Topmost visible row = first virtual item whose bottom edge is below the
    // viewport top (virtual items include overscan rows above the viewport)
    const getTopPosition = useCallback(() => {
      const scrollTop = scrollRef.current?.scrollTop ?? 0;
      const items = virtualizer.getVirtualItems();
      for (const item of items) {
        if (item.start + item.size > scrollTop) return item.index;
      }
      return items.length > 0 ? items[items.length - 1]!.index : null;
    }, [virtualizer]);

    const { markProgrammaticScroll } = useLensScroll({
      scrollRef,
      getTopPosition,
      onUserScroll,
    });

    const scrollToPosition = useCallback(
      (position: number) => {
        markProgrammaticScroll();
        virtualizer.scrollToIndex(position, { align: 'center' });
      },
      [markProgrammaticScroll, virtualizer]
    );

    useImperativeHandle(ref, () => ({ scrollToPosition }), [scrollToPosition]);

    // Follow the active chunk while sequential playback runs. behavior stays
    // 'auto' - react-virtual doesn't support smooth scrolling with dynamic
    // row measurement.
    useEffect(() => {
      if (activeIndex !== null && followPlayback) {
        scrollToPosition(activeIndex);
      }
    }, [activeIndex, followPlayback, scrollToPosition]);

    // Land on the shell's restore target (e.g. after switching from the PDF
    // lens, or returning to the viewer tab) so the user keeps their place.
    // On a cold load entries arrive async - consuming the one-shot restore
    // while the list is still empty would strand the user at the top, so wait
    // for data like the PDF lens waits for its document.
    const didInitialScroll = useRef(false);
    useEffect(() => {
      if (didInitialScroll.current || entries.length === 0) return;
      didInitialScroll.current = true;
      const target = getRestorePosition();
      if (target !== null) {
        scrollToPosition(target);
      }
      // Runs once, when entries are first available; deliberately not
      // re-running on the other props.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [entries.length]);

    const virtualItems = virtualizer.getVirtualItems();

    return (
      <div
        ref={scrollRef}
        data-testid="viewer-scroll"
        className="min-w-0 flex-1 overflow-y-auto py-4 font-serif"
      >
        {isLoading && !hasInventory && (
          <div className="flex items-center justify-center py-8 font-sans">
            <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            <span className="text-muted-foreground ml-2">
              Loading chunk inventory...
            </span>
          </div>
        )}

        {!hasInventory && !isLoading && (
          <p className="text-muted-foreground py-8 text-center font-sans text-sm">
            No chunk inventory loaded. Click Refresh to load it.
          </p>
        )}

        {hasInventory && entries.length === 0 && (
          <p className="text-muted-foreground py-8 text-center font-sans text-sm">
            No chunks in this screenplay
          </p>
        )}

        {entries.length > 0 && (
          <div
            className="relative w-full"
            style={{ height: virtualizer.getTotalSize() }}
          >
            {virtualItems.map((virtualItem) => {
              const entry = entries[virtualItem.index];
              if (!entry) return null;
              return (
                <div
                  key={virtualItem.key}
                  data-index={virtualItem.index}
                  ref={virtualizer.measureElement}
                  className="absolute top-0 left-0 w-full"
                  style={{ transform: `translateY(${virtualItem.start}px)` }}
                >
                  <ChunkRow
                    entry={entry}
                    index={virtualItem.index}
                    projectName={projectName}
                    isActive={activeIndex === virtualItem.index}
                    isSelected={selectedIndex === virtualItem.index}
                    onSelect={onSelect}
                    onPlayFromHere={onPlayFromHere}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
);
