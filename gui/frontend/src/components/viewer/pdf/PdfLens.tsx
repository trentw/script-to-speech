// Configure the pdf.js worker (local bundled asset). Importing here (in the
// lazily-loaded PDF lens) keeps pdf.js out of the main bundle until needed.
import './pdfSetup';

import { useVirtualizer } from '@tanstack/react-virtual';
import { AlertTriangle, Loader2 } from 'lucide-react';
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Document } from 'react-pdf';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { usePdfAnchors } from '@/hooks/queries/usePdfAnchors';
import { apiService } from '@/services/api';
import type { ChunkInventoryEntry } from '@/types/chunks';
import type { ChunkAnchor } from '@/types/pdfAnchors';

import type { ViewerLensHandle } from '../lensHandle';
import { useLensScroll } from '../useLensScroll';
import {
  buildAnchorOffsets,
  computeFollowOffset,
  computePageStarts,
  findTopPosition,
  groupAnchorsByPage,
  remapScrollTop,
} from './pdfOverlayLogic';
import { PdfPageView } from './PdfPageView';

/** Vertical gap between rendered pages, px. */
const PAGE_GAP = 16;
/** Max rendered page width, px (keeps text readable on wide screens). */
const MAX_PAGE_WIDTH = 900;
/** Horizontal breathing room subtracted from the container width, px. */
const HORIZONTAL_PADDING = 32;
/** Top padding of the pages wrapper (py-4), included in scroll offsets. */
const PAGE_VERTICAL_PADDING = 16;

interface PdfLensProps {
  entries: ChunkInventoryEntry[];
  projectName: string;
  /** List position of the sequential-playback active chunk, or null */
  activeIndex: number | null;
  /** List position of the chunk open in the detail panel, or null */
  selectedIndex: number | null;
  followPlayback: boolean;
  /** idx -> list position (shared with the list lens) */
  positionByIdx: Map<number, number>;
  /** Ordered preprocessed-chunk revision from the inventory response. */
  chunkLayoutRevision: string;
  onSelect: (position: number, regionPositions: number[]) => void;
  /** Fired on genuine user scroll with the topmost visible position, so the
   * shell can drop follow and track the reading anchor */
  onUserScroll: (topPosition: number | null) => void;
  /** Position to land on once the document renders (the shell's reading
   * anchor / active chunk / selection), or null for the top */
  getRestorePosition: () => number | null;
}

/**
 * The PDF overlay lens: the source screenplay PDF rendered with each chunk's
 * audio-status highlight anchored onto it. Each source region is one clean
 * selection target; when preprocessors derive multiple audio chunks from that
 * source, the persistent detail panel presents them in screenplay order.
 *
 * Anchors are fetched from the backend (idx-aligned with the inventory).
 * Chunks that can't be confidently anchored are omitted with an "N not shown"
 * indicator; the list lens remains the complete fallback. Pages are
 * virtualized with useVirtualizer so long screenplays stay responsive.
 */
export const PdfLens = forwardRef<ViewerLensHandle, PdfLensProps>(
  function PdfLens(
    {
      entries,
      projectName,
      activeIndex,
      selectedIndex,
      followPlayback,
      positionByIdx,
      chunkLayoutRevision,
      onSelect,
      onUserScroll,
      getRestorePosition,
    },
    ref
  ) {
    const scrollRef = useRef<HTMLDivElement | null>(null);
    const [containerWidth, setContainerWidth] = useState(0);
    // The scroll container only has a tall child once react-pdf resolves the
    // document; scrolling before that clamps to 0
    const [documentReady, setDocumentReady] = useState(false);

    const {
      data: anchors,
      isLoading,
      isRefetching,
      error,
      refresh,
    } = usePdfAnchors(projectName);

    const pdfUrl = useMemo(
      () => apiService.getSourcePdfUrl(projectName),
      [projectName]
    );

    // Measure the container to size pages (and re-measure on resize)
    useLayoutEffect(() => {
      const element = scrollRef.current;
      if (!element) return;
      const measure = () => setContainerWidth(element.clientWidth);
      measure();
      const observer = new ResizeObserver(measure);
      observer.observe(element);
      return () => observer.disconnect();
    }, []);

    const renderWidth = Math.max(
      0,
      Math.min(MAX_PAGE_WIDTH, containerWidth - HORIZONTAL_PADDING)
    );

    // Anchors and inventory are fetched independently. Count equality is not
    // enough: a reparse can reorder or replace chunks without changing the
    // length, making an old anchor idx select the wrong current entry. The
    // cheap ordered-layout revision detects that skew. If mismatches become
    // persistent rather than transient, the backend caches should additionally
    // reject in-flight computations from an older invalidation generation.
    const anchorsInSync =
      !anchors ||
      (anchors.totalChunks === entries.length &&
        anchors.chunkLayoutRevision === chunkLayoutRevision);
    const overlayGeometrySupported =
      !anchors || anchors.unsupportedGeometryPages.length === 0;
    // One refresh attempt per distinct revision-pair skew. The signature must
    // not include anything that changes on every recompute (generatedAt would
    // turn a persistent mismatch into an endless refresh loop of multi-second
    // PDF extractions).
    const attemptedSyncRefreshRef = useRef<string | null>(null);
    const [syncRefreshExhausted, setSyncRefreshExhausted] = useState(false);
    useEffect(() => {
      if (!anchors || anchorsInSync) {
        setSyncRefreshExhausted(false);
        return;
      }
      if (isRefetching) return;
      const signature = `${anchors.chunkLayoutRevision}:${chunkLayoutRevision}`;
      if (attemptedSyncRefreshRef.current === signature) {
        // The refresh for this skew already ran and didn't clear it
        setSyncRefreshExhausted(true);
        return;
      }
      attemptedSyncRefreshRef.current = signature;
      setSyncRefreshExhausted(false);
      void refresh();
    }, [anchors, anchorsInSync, chunkLayoutRevision, isRefetching, refresh]);

    // Page geometry comes from the backend, so layout is stable before pdf.js
    // parses the file.
    const pages = useMemo(() => anchors?.pages ?? [], [anchors]);
    const pageHeights = useMemo(
      () =>
        pages.map((page) =>
          page.width > 0
            ? (renderWidth * page.height) / page.width
            : renderWidth
        ),
      [pages, renderWidth]
    );
    const pageStarts = useMemo(
      () => computePageStarts(pageHeights, PAGE_GAP),
      [pageHeights]
    );

    const syncedAnchors = useMemo<ChunkAnchor[]>(
      () =>
        anchorsInSync && overlayGeometrySupported
          ? (anchors?.anchors ?? [])
          : [],
      [anchors, anchorsInSync, overlayGeometrySupported]
    );
    const anchorsByPage = useMemo(
      () => groupAnchorsByPage(syncedAnchors, positionByIdx),
      [syncedAnchors, positionByIdx]
    );
    const anchorByIdx = useMemo(() => {
      const map = new Map<number, ChunkAnchor>();
      for (const anchor of syncedAnchors) {
        map.set(anchor.idx, anchor);
      }
      return map;
    }, [syncedAnchors]);
    const anchorOffsets = useMemo(
      () =>
        buildAnchorOffsets(
          syncedAnchors,
          positionByIdx,
          pageStarts,
          pages,
          renderWidth,
          PAGE_VERTICAL_PADDING
        ),
      [syncedAnchors, positionByIdx, pageStarts, pages, renderWidth]
    );

    const virtualizer = useVirtualizer({
      count: pages.length,
      getScrollElement: () => scrollRef.current,
      estimateSize: (index) => (pageHeights[index] ?? 0) + PAGE_GAP,
      overscan: 2,
    });

    // Reflow the virtualizer when page heights change (width/resize)
    useEffect(() => {
      virtualizer.measure();
    }, [pageHeights, virtualizer]);

    const getTopPosition = useCallback(
      () => findTopPosition(anchorOffsets, scrollRef.current?.scrollTop ?? 0),
      [anchorOffsets]
    );

    const { markProgrammaticScroll } = useLensScroll({
      scrollRef,
      getTopPosition,
      onUserScroll,
    });

    // Keep the same content under the viewport top when the rendered page
    // width changes (detail panel opening/closing, window resize): page
    // heights rescale but the raw scrollTop would stay in stale pixels.
    // The ref records which width's pixel space scrollTop currently lives in;
    // it only advances when a remap write actually lands, so a remap whose
    // frame gets cancelled by a newer width change (resize drags) is folded
    // into the next remap instead of leaving scrollTop half-converted.
    const scrollTopWidthRef = useRef(0);
    useEffect(() => {
      if (renderWidth <= 0 || pages.length === 0) return;
      const element = scrollRef.current;
      if (!element) return;
      const prevWidth = scrollTopWidthRef.current;
      if (prevWidth <= 0 || prevWidth === renderWidth) {
        scrollTopWidthRef.current = renderWidth;
        return;
      }
      const nextTop = remapScrollTop({
        scrollTop: element.scrollTop,
        prevWidth,
        nextWidth: renderWidth,
        pages,
        gap: PAGE_GAP,
        paddingTop: PAGE_VERTICAL_PADDING,
      });
      markProgrammaticScroll();
      // Defer one frame so the re-measured total height is in the DOM;
      // setting scrollTop against the stale height would clamp it
      const frame = requestAnimationFrame(() => {
        markProgrammaticScroll();
        element.scrollTop = nextTop;
        scrollTopWidthRef.current = renderWidth;
      });
      return () => cancelAnimationFrame(frame);
    }, [renderWidth, pages, markProgrammaticScroll]);

    // Scroll a chunk into view by list position, resolving its anchor's first
    // rect. Unanchored chunks have no place on the page, so land on the
    // nearest anchored neighbor instead of silently doing nothing.
    const scrollToPosition = useCallback(
      (position: number) => {
        const hasAnchor = (candidate: number) => {
          const candidateEntry = entries[candidate];
          return candidateEntry ? anchorByIdx.has(candidateEntry.idx) : false;
        };
        let target: number | null = hasAnchor(position) ? position : null;
        for (let d = 1; target === null && d < entries.length; d++) {
          if (position - d >= 0 && hasAnchor(position - d)) {
            target = position - d;
          } else if (position + d < entries.length && hasAnchor(position + d)) {
            target = position + d;
          }
        }
        if (target === null) return;
        const entry = entries[target];
        if (!entry) return;
        const anchor = anchorByIdx.get(entry.idx);
        const rect = anchor?.rects[0];
        if (!rect) return;
        const pageWidth = pages[rect.page]?.width ?? 0;
        const viewportHeight = scrollRef.current?.clientHeight ?? 0;
        const offset = computeFollowOffset(
          PAGE_VERTICAL_PADDING + (pageStarts[rect.page] ?? 0),
          rect.top,
          renderWidth > 0 && pageWidth > 0 ? renderWidth / pageWidth : 1,
          viewportHeight
        );
        markProgrammaticScroll();
        scrollRef.current?.scrollTo({ top: offset });
      },
      [
        entries,
        anchorByIdx,
        pageStarts,
        pages,
        renderWidth,
        markProgrammaticScroll,
      ]
    );

    useImperativeHandle(ref, () => ({ scrollToPosition, refresh }), [
      refresh,
      scrollToPosition,
    ]);

    // Follow the active chunk during sequential playback (only once the
    // document exists - scrolling an empty container clamps to 0)
    useEffect(() => {
      if (activeIndex === null || !followPlayback || !documentReady) return;
      scrollToPosition(activeIndex);
    }, [activeIndex, followPlayback, documentReady, scrollToPosition]);

    // Land on the shell's restore target when the lens mounts - but only
    // after the rendered document exists; earlier scrolls clamp to 0 because
    // the scroll container has no tall child yet.
    const didInitialScroll = useRef(false);
    const getRestorePositionRef = useRef(getRestorePosition);
    getRestorePositionRef.current = getRestorePosition;
    useEffect(() => {
      if (didInitialScroll.current) return;
      if (!documentReady || renderWidth === 0 || pages.length === 0) return;
      didInitialScroll.current = true;
      const target = getRestorePositionRef.current();
      if (target !== null) {
        scrollToPosition(target);
      }
      // Runs once, when geometry and the document are first available.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [documentReady, renderWidth, pages.length]);

    const unanchoredCount = anchors?.unanchoredIdxs.length ?? 0;
    const virtualItems = virtualizer.getVirtualItems();

    return (
      <div className="flex min-w-0 flex-1 flex-col">
        {!anchorsInSync && (
          <div className="text-muted-foreground bg-muted/50 flex items-center gap-1.5 px-4 py-1.5 font-sans text-xs">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span>
              {syncRefreshExhausted
                ? 'Overlay positions are out of sync with the current chunks, so highlights are hidden. The PDF remains readable; use List view to select and edit chunks, or press Refresh to try again.'
                : 'Chunk data changed — refreshing overlay positions...'}
            </span>
          </div>
        )}
        {anchorsInSync && !overlayGeometrySupported && (
          <div className="text-muted-foreground bg-muted/50 flex items-center gap-1.5 px-4 py-2 font-sans text-xs">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span>
              Audio highlights are disabled because this PDF uses non-standard
              page geometry that is not yet supported. The PDF remains readable;
              use List view to select and edit chunks.
            </span>
          </div>
        )}
        {anchorsInSync && overlayGeometrySupported && unanchoredCount > 0 && (
          <div className="text-muted-foreground bg-muted/50 flex items-center gap-1.5 px-4 py-1.5 font-sans text-xs">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-help">
                  {unanchoredCount} chunk{unanchoredCount === 1 ? '' : 's'} not
                  shown on the PDF
                </span>
              </TooltipTrigger>
              <TooltipContent>
                These chunks couldn&apos;t be located on the page. The List view
                shows every chunk.
              </TooltipContent>
            </Tooltip>
          </div>
        )}

        <div
          ref={scrollRef}
          data-testid="pdf-scroll"
          className="bg-muted/30 min-w-0 flex-1 overflow-y-auto"
        >
          {(isLoading || isRefetching) && !anchors && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
              <span className="text-muted-foreground ml-2 text-sm">
                Anchoring chunks to the PDF...
              </span>
            </div>
          )}

          {error && !isLoading && !isRefetching && (
            <p className="text-muted-foreground py-16 text-center text-sm">
              Couldn&apos;t load the PDF overlay: {error.message}
            </p>
          )}

          {anchors && renderWidth > 0 && (
            <Document
              file={pdfUrl}
              onLoadSuccess={() => setDocumentReady(true)}
              loading={
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
                  <span className="text-muted-foreground ml-2 text-sm">
                    Loading PDF...
                  </span>
                </div>
              }
              error={
                <p className="text-muted-foreground py-16 text-center text-sm">
                  Failed to render the PDF.
                </p>
              }
            >
              <div
                className="relative mx-auto w-full py-4"
                style={{ height: virtualizer.getTotalSize() }}
              >
                {virtualItems.map((virtualItem) => {
                  const page = pages[virtualItem.index];
                  return (
                    <div
                      key={virtualItem.key}
                      className="absolute top-0 left-0 w-full"
                      style={{
                        transform: `translateY(${virtualItem.start}px)`,
                      }}
                    >
                      <PdfPageView
                        pageNumber={virtualItem.index}
                        renderWidth={renderWidth}
                        scale={
                          page && page.width > 0 ? renderWidth / page.width : 1
                        }
                        pageRegions={anchorsByPage.get(virtualItem.index) ?? []}
                        entries={entries}
                        activePosition={activeIndex}
                        selectedPosition={selectedIndex}
                        onSelect={onSelect}
                      />
                    </div>
                  );
                })}
              </div>
            </Document>
          )}
        </div>
      </div>
    );
  }
);

export default PdfLens;
