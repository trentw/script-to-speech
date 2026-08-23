/**
 * Pure logic for the PDF overlay lens: grouping anchors onto pages, scaling
 * PDF-point rects to rendered pixels, status-driven overlay styles, and
 * follow-scroll math. No React in this module.
 */

import type { ChunkInventoryEntry, GenerationKind } from '@/types/chunks';
import type { AnchorRect, ChunkAnchor, PdfPageInfo } from '@/types/pdfAnchors';

export interface SourceRegionMember {
  idx: number;
  position: number;
  matchRatio: number;
}

/** One source-text region on a page and every audio chunk derived from it. */
export interface PageRegion {
  /** Stable page + geometry key. */
  key: string;
  page: number;
  /** Members in screenplay/list order. Usually one; splits may have several. */
  members: SourceRegionMember[];
  /** Rects belonging to this page only */
  rects: AnchorRect[];
}

function geometryKey(page: number, rects: AnchorRect[]): string {
  const canonical = [...rects]
    .sort((a, b) => a.top - b.top || a.x0 - b.x0)
    .map((rect) =>
      [rect.x0, rect.top, rect.x1, rect.bottom]
        .map((value) => value.toFixed(3))
        .join(',')
    )
    .join('|');
  return `${page}:${canonical}`;
}

/**
 * Group anchors by page and exact source geometry. Preprocessors can derive
 * several audio chunks from one raw-text block (parenthetical splits and dual
 * dialogue); those chunks intentionally share one interactive source region
 * rather than producing inaccessible overlapping controls.
 */
export function groupAnchorsByPage(
  anchors: ChunkAnchor[],
  positionByIdx: Map<number, number>
): Map<number, PageRegion[]> {
  const regionMaps = new Map<number, Map<string, PageRegion>>();
  for (const anchor of anchors) {
    const position = positionByIdx.get(anchor.idx);
    if (position === undefined) continue;

    const rectsByPage = new Map<number, AnchorRect[]>();
    for (const rect of anchor.rects) {
      const existing = rectsByPage.get(rect.page);
      if (existing) {
        existing.push(rect);
      } else {
        rectsByPage.set(rect.page, [rect]);
      }
    }

    for (const [page, rects] of rectsByPage) {
      const key = geometryKey(page, rects);
      let pageRegions = regionMaps.get(page);
      if (!pageRegions) {
        pageRegions = new Map();
        regionMaps.set(page, pageRegions);
      }
      const existing = pageRegions.get(key);
      if (existing) {
        existing.members.push({
          idx: anchor.idx,
          position,
          matchRatio: anchor.matchRatio,
        });
      } else {
        pageRegions.set(key, {
          key,
          page,
          members: [
            { idx: anchor.idx, position, matchRatio: anchor.matchRatio },
          ],
          rects,
        });
      }
    }
  }

  const byPage = new Map<number, PageRegion[]>();
  for (const [page, regionMap] of regionMaps) {
    const regions = [...regionMap.values()];
    for (const region of regions) {
      region.members.sort((a, b) => a.position - b.position);
    }
    regions.sort(
      (a, b) =>
        (a.rects[0]?.top ?? 0) - (b.rects[0]?.top ?? 0) ||
        (a.rects[0]?.x0 ?? 0) - (b.rects[0]?.x0 ?? 0)
    );
    byPage.set(page, regions);
  }
  return byPage;
}

export interface RegionSummary {
  status: ChunkInventoryEntry['status'];
  modifiedKinds: GenerationKind[];
}

/** Summarize orthogonal availability and provenance for a source region. */
export function summarizeRegion(entries: ChunkInventoryEntry[]): RegionSummary {
  const status = entries.some((entry) => entry.status === 'missing')
    ? 'missing'
    : entries.some((entry) => entry.status === 'cached')
      ? 'cached'
      : 'expected_silence';
  const kinds = new Set(
    entries
      .map((entry) => entry.userModified)
      .filter((kind): kind is GenerationKind => kind !== null)
  );
  return {
    status,
    modifiedKinds: (['edit', 'retake'] as const).filter((kind) =>
      kinds.has(kind)
    ),
  };
}

export interface ScaledRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Scale a PDF-point rect to rendered pixels (renderedWidth / pageWidth). */
export function scaleRect(rect: AnchorRect, scale: number): ScaledRect {
  return {
    left: rect.x0 * scale,
    top: rect.top * scale,
    width: (rect.x1 - rect.x0) * scale,
    height: (rect.bottom - rect.top) * scale,
  };
}

/**
 * Tailwind classes for a chunk's overlay box, mirroring the list-row status
 * semantics (active > selected > status). Boxes are translucent so the PDF
 * text shows through; rings give an outline over any background.
 */
export function statusOverlayClasses(
  status: ChunkInventoryEntry['status'],
  opts: { isActive: boolean; isSelected: boolean }
): string {
  const base = 'rounded-sm cursor-pointer transition-colors ring-1 ring-inset';
  if (opts.isActive) {
    return `${base} bg-primary/25 ring-primary/70`;
  }
  if (opts.isSelected) {
    return `${base} bg-accent/40 ring-accent-foreground/40`;
  }
  switch (status) {
    case 'missing':
      return `${base} bg-destructive/15 ring-destructive/40 hover:bg-destructive/25`;
    case 'expected_silence':
      return `${base} bg-muted/20 ring-muted-foreground/20 hover:bg-muted/40`;
    case 'cached':
    default:
      return `${base} bg-primary/5 ring-primary/20 hover:bg-primary/15`;
  }
}

/**
 * Cumulative top offset (px) of each page in the scroll container, given each
 * page's rendered height and the vertical gap between pages.
 */
export function computePageStarts(
  pageHeights: number[],
  gap: number
): number[] {
  const starts: number[] = [];
  let acc = 0;
  for (const height of pageHeights) {
    starts.push(acc);
    acc += height + gap;
  }
  return starts;
}

/**
 * Scroll offset that centers a rect's top within the viewport (clamped at 0).
 */
export function computeFollowOffset(
  pageStart: number,
  rectTop: number,
  scale: number,
  viewportHeight: number
): number {
  return Math.max(0, pageStart + rectTop * scale - viewportHeight / 2);
}

/** A chunk's vertical scroll offset in the PDF container, sorted ascending. */
export interface AnchorOffset {
  offset: number;
  position: number;
}

/**
 * Flat scroll-offset index of every anchored chunk (by its first rect),
 * sorted ascending — the reverse of "scroll to chunk": given a scrollTop,
 * find which chunk is at the top of the viewport.
 */
export function buildAnchorOffsets(
  anchors: ChunkAnchor[],
  positionByIdx: Map<number, number>,
  pageStarts: number[],
  pages: PdfPageInfo[],
  renderWidth: number,
  paddingTop: number
): AnchorOffset[] {
  const offsets: AnchorOffset[] = [];
  for (const anchor of anchors) {
    const position = positionByIdx.get(anchor.idx);
    const rect = anchor.rects[0];
    if (position === undefined || !rect) continue;
    const pageWidth = pages[rect.page]?.width ?? 0;
    const scale =
      pageWidth > 0 && renderWidth > 0 ? renderWidth / pageWidth : 1;
    offsets.push({
      offset: paddingTop + (pageStarts[rect.page] ?? 0) + rect.top * scale,
      position,
    });
  }
  offsets.sort((a, b) => a.offset - b.offset);
  return offsets;
}

/**
 * The list position of the topmost visible chunk for a given scrollTop: the
 * last anchor at or above the viewport top (i.e. the chunk being read), or
 * the first anchor when scrolled above them all. Null when nothing is
 * anchored. Binary search over the sorted offsets.
 */
export function findTopPosition(
  offsets: AnchorOffset[],
  scrollTop: number
): number | null {
  if (offsets.length === 0) return null;
  let low = 0;
  let high = offsets.length - 1;
  let result = 0;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (offsets[mid]!.offset <= scrollTop) {
      result = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return offsets[result]!.position;
}

/**
 * Remap a scrollTop across a page-width change so the same content stays at
 * the viewport top. Page heights scale linearly with width but inter-page
 * gaps and container padding do not, so the mapping goes through "page +
 * fraction within page" rather than scaling the raw offset.
 */
export function remapScrollTop(options: {
  scrollTop: number;
  prevWidth: number;
  nextWidth: number;
  pages: PdfPageInfo[];
  gap: number;
  paddingTop: number;
}): number {
  const { scrollTop, prevWidth, nextWidth, pages, gap, paddingTop } = options;
  if (pages.length === 0 || prevWidth <= 0 || nextWidth <= 0) return scrollTop;

  const heightAt = (page: PdfPageInfo, width: number) =>
    page.width > 0 ? (width * page.height) / page.width : width;
  const prevHeights = pages.map((page) => heightAt(page, prevWidth));
  const nextHeights = pages.map((page) => heightAt(page, nextWidth));
  const prevStarts = computePageStarts(prevHeights, gap);
  const nextStarts = computePageStarts(nextHeights, gap);

  const contentTop = Math.max(0, scrollTop - paddingTop);
  let pageIndex = pages.length - 1;
  for (let i = 0; i < pages.length; i++) {
    if (contentTop < prevStarts[i]! + prevHeights[i]! + gap) {
      pageIndex = i;
      break;
    }
  }
  const prevHeight = prevHeights[pageIndex]!;
  const fraction =
    prevHeight > 0 ? (contentTop - prevStarts[pageIndex]!) / prevHeight : 0;
  return (
    paddingTop + nextStarts[pageIndex]! + fraction * nextHeights[pageIndex]!
  );
}
