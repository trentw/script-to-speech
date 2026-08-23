import { describe, expect, it } from 'vitest';

import type { ChunkInventoryEntry } from '@/types/chunks';
import type { ChunkAnchor } from '@/types/pdfAnchors';

import {
  buildAnchorOffsets,
  computeFollowOffset,
  computePageStarts,
  findTopPosition,
  groupAnchorsByPage,
  remapScrollTop,
  scaleRect,
  statusOverlayClasses,
  summarizeRegion,
} from '../pdfOverlayLogic';

function rect(page: number, x0 = 100, top = 72, x1 = 200, bottom = 84) {
  return { page, x0, top, x1, bottom };
}

function anchor(idx: number, rects: ReturnType<typeof rect>[]): ChunkAnchor {
  return { idx, rects, matchRatio: 1 };
}

function entry(
  overrides: Partial<ChunkInventoryEntry> = {}
): ChunkInventoryEntry {
  return {
    idx: 0,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: 'Hi.',
    processedText: 'HI.',
    cacheFilename: 'a.mp3',
    status: 'cached',
    userModified: null,
    occurrences: [0],
    ...overrides,
  };
}

describe('groupAnchorsByPage', () => {
  it('groups anchors by page and attaches list position', () => {
    const positionByIdx = new Map([
      [10, 0],
      [20, 1],
    ]);
    const anchors = [anchor(10, [rect(0)]), anchor(20, [rect(1)])];
    const byPage = groupAnchorsByPage(anchors, positionByIdx);
    expect(byPage.get(0)?.[0]?.members[0]?.idx).toBe(10);
    expect(byPage.get(0)?.[0]?.members[0]?.position).toBe(0);
    expect(byPage.get(1)?.[0]?.members[0]?.idx).toBe(20);
    expect(byPage.get(1)?.[0]?.members[0]?.position).toBe(1);
  });

  it('combines chunks with identical geometry into one source region', () => {
    const positionByIdx = new Map([
      [5, 3],
      [6, 4],
    ]);
    const sharedRect = rect(0);
    const byPage = groupAnchorsByPage(
      [anchor(5, [sharedRect]), anchor(6, [{ ...sharedRect }])],
      positionByIdx
    );
    expect(byPage.get(0)).toHaveLength(1);
    expect(byPage.get(0)?.[0]?.members).toEqual([
      { idx: 5, position: 3, matchRatio: 1 },
      { idx: 6, position: 4, matchRatio: 1 },
    ]);
  });

  it('splits a page-spanning chunk into one region per page', () => {
    const positionByIdx = new Map([[5, 3]]);
    const anchors = [anchor(5, [rect(0), rect(1)])];
    const byPage = groupAnchorsByPage(anchors, positionByIdx);
    expect(byPage.get(0)?.[0]?.rects).toHaveLength(1);
    expect(byPage.get(1)?.[0]?.rects).toHaveLength(1);
    expect(byPage.get(0)?.[0]?.members[0]?.position).toBe(3);
  });

  it('skips anchors whose idx has no list position (skew)', () => {
    const positionByIdx = new Map<number, number>();
    const byPage = groupAnchorsByPage([anchor(99, [rect(0)])], positionByIdx);
    expect(byPage.size).toBe(0);
  });
});

describe('scaleRect', () => {
  it('scales PDF points to pixels', () => {
    const scaled = scaleRect(rect(0, 100, 72, 200, 84), 2);
    expect(scaled).toEqual({ left: 200, top: 144, width: 200, height: 24 });
  });
});

describe('statusOverlayClasses', () => {
  it('active wins over selected and status', () => {
    const cls = statusOverlayClasses('missing', {
      isActive: true,
      isSelected: true,
    });
    expect(cls).toContain('bg-primary/25');
  });

  it('selected wins over status', () => {
    const cls = statusOverlayClasses('missing', {
      isActive: false,
      isSelected: true,
    });
    expect(cls).toContain('bg-accent/40');
  });

  it('reflects missing and expected_silence status', () => {
    expect(
      statusOverlayClasses('missing', {
        isActive: false,
        isSelected: false,
      })
    ).toContain('bg-destructive/15');
    expect(
      statusOverlayClasses('expected_silence', {
        isActive: false,
        isSelected: false,
      })
    ).toContain('bg-muted/20');
  });
});

describe('summarizeRegion', () => {
  it('keeps availability and user provenance as separate signals', () => {
    expect(
      summarizeRegion([
        entry({ status: 'cached', userModified: 'retake' }),
        entry({ idx: 1, status: 'missing', userModified: 'edit' }),
      ])
    ).toEqual({
      status: 'missing',
      modifiedKinds: ['edit', 'retake'],
    });
  });
});

describe('computePageStarts', () => {
  it('accumulates heights plus the gap', () => {
    expect(computePageStarts([100, 200, 150], 10)).toEqual([0, 110, 320]);
  });
});

describe('computeFollowOffset', () => {
  it('centers the rect top in the viewport', () => {
    // pageStart 320, rectTop 100 * scale 2 = 200 -> 520, minus half of 400
    expect(computeFollowOffset(320, 100, 2, 400)).toBe(320);
  });

  it('clamps to zero near the top', () => {
    expect(computeFollowOffset(0, 10, 1, 400)).toBe(0);
  });
});

describe('buildAnchorOffsets / findTopPosition', () => {
  const pages = [
    { page: 0, width: 612, height: 792 },
    { page: 1, width: 612, height: 792 },
  ];
  // renderWidth 612 -> scale 1; heights [792, 792] with an 8px gap
  const pageStarts = computePageStarts([792, 792], 8);
  const positionByIdx = new Map([
    [10, 0],
    [20, 1],
    [30, 2],
  ]);
  const offsets = buildAnchorOffsets(
    [
      anchor(20, [rect(1, 100, 100)]),
      anchor(10, [rect(0, 100, 72)]),
      anchor(30, [rect(1, 100, 500)]),
      anchor(99, [rect(0, 100, 10)]), // no list position -> dropped
    ],
    positionByIdx,
    pageStarts,
    pages,
    612,
    16
  );

  it('produces ascending offsets with list positions', () => {
    expect(offsets).toEqual([
      { offset: 88, position: 0 }, // 16 + 0 + 72
      { offset: 916, position: 1 }, // 16 + 800 + 100
      { offset: 1316, position: 2 }, // 16 + 800 + 500
    ]);
  });

  it('resolves the topmost chunk for a scrollTop', () => {
    expect(findTopPosition(offsets, 0)).toBe(0); // above all -> first
    expect(findTopPosition(offsets, 88)).toBe(0);
    expect(findTopPosition(offsets, 900)).toBe(0); // still reading chunk 0
    expect(findTopPosition(offsets, 916)).toBe(1);
    expect(findTopPosition(offsets, 5000)).toBe(2);
    expect(findTopPosition([], 100)).toBeNull();
  });
});

describe('remapScrollTop', () => {
  const pages = [
    { page: 0, width: 600, height: 800 },
    { page: 1, width: 600, height: 800 },
  ];

  it('keeps the same page fraction under the viewport top', () => {
    // prev: heights 800, starts [0, 810]; scrollTop = 20 pad + 810 + 400
    // next: heights 400, starts [0, 410]; expected = 20 + 410 + 200
    expect(
      remapScrollTop({
        scrollTop: 1230,
        prevWidth: 600,
        nextWidth: 300,
        pages,
        gap: 10,
        paddingTop: 20,
      })
    ).toBe(630);
  });

  it('returns the input when geometry is unknown', () => {
    expect(
      remapScrollTop({
        scrollTop: 50,
        prevWidth: 0,
        nextWidth: 300,
        pages,
        gap: 10,
        paddingTop: 20,
      })
    ).toBe(50);
    expect(
      remapScrollTop({
        scrollTop: 50,
        prevWidth: 600,
        nextWidth: 300,
        pages: [],
        gap: 10,
        paddingTop: 20,
      })
    ).toBe(50);
  });
});
