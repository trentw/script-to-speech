import userEvent from '@testing-library/user-event';
import { createRef, useEffect } from 'react';
import {
  afterAll,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';

import type { ViewerLensHandle } from '@/components/viewer/lensHandle';
import { render, screen } from '@/test/utils/render';
import type { ChunkInventoryEntry } from '@/types/chunks';
import type { ChunkAnchorsResponse } from '@/types/pdfAnchors';

import PdfLens from '../PdfLens';

// react-pdf needs a canvas + worker (absent in jsdom): Document passes children
// through (reporting load success like the real component), Page renders a
// marker div.
vi.mock('react-pdf', () => ({
  Document: ({
    children,
    onLoadSuccess,
  }: {
    children: React.ReactNode;
    onLoadSuccess?: () => void;
  }) => {
    useEffect(() => {
      onLoadSuccess?.();
      // Fire once, like a real document load.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return <div data-testid="pdf-document">{children}</div>;
  },
  Page: ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid={`pdf-page-${pageNumber}`} />
  ),
  pdfjs: { GlobalWorkerOptions: {} },
}));

// Keep the worker `?url` asset import out of jsdom.
vi.mock('../pdfSetup', () => ({}));

// Render every page (no layout in jsdom).
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        key: index,
        index,
        start: index * 800,
        size: 800,
      })),
    getTotalSize: () => count * 800,
    measure: vi.fn(),
    scrollToIndex: vi.fn(),
  }),
}));

// Controllable anchors query.
const anchorsMock = vi.hoisted(() => ({
  data: undefined as ChunkAnchorsResponse | undefined,
  isLoading: false,
  isRefetching: false,
  error: null as Error | null,
  refresh: vi.fn(() => Promise.resolve()),
}));
vi.mock('@/hooks/queries/usePdfAnchors', () => ({
  usePdfAnchors: () => ({
    data: anchorsMock.data,
    isLoading: anchorsMock.isLoading,
    isRefetching: anchorsMock.isRefetching,
    error: anchorsMock.error,
    refresh: anchorsMock.refresh,
    refetch: vi.fn(),
  }),
}));

function entry(
  idx: number,
  overrides: Partial<ChunkInventoryEntry> = {}
): ChunkInventoryEntry {
  return {
    idx,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: `Line ${idx}.`,
    processedText: `LINE ${idx}.`,
    cacheFilename: `c-${idx}.mp3`,
    status: 'cached',
    userModified: null,
    occurrences: [idx],
    ...overrides,
  };
}

function anchorsResponse(): ChunkAnchorsResponse {
  return {
    projectName: 'demo',
    pages: [
      { page: 0, width: 612, height: 792 },
      { page: 1, width: 612, height: 792 },
    ],
    anchors: [
      {
        idx: 0,
        rects: [{ page: 0, x0: 100, top: 72, x1: 300, bottom: 84 }],
        matchRatio: 1,
      },
      {
        idx: 1,
        rects: [{ page: 1, x0: 100, top: 100, x1: 300, bottom: 112 }],
        matchRatio: 1,
      },
      {
        idx: 2,
        rects: [{ page: 0, x0: 100, top: 72, x1: 300, bottom: 84 }],
        matchRatio: 1,
      },
    ],
    unanchoredIdxs: [3],
    totalChunks: 4,
    anchoredCount: 3,
    chunkLayoutRevision: 'layout-rev-1',
    unsupportedGeometryPages: [],
    generatedAt: '2026-07-06T00:00:00+00:00',
  };
}

const entries = [
  entry(0),
  entry(1),
  entry(2, { userModified: 'edit' }),
  entry(3),
];
const positionByIdx = new Map([
  [0, 0],
  [1, 1],
  [2, 2],
  [3, 3],
]);

function baseProps(overrides = {}) {
  return {
    entries,
    projectName: 'demo',
    activeIndex: null,
    selectedIndex: null,
    followPlayback: true,
    positionByIdx,
    chunkLayoutRevision: 'layout-rev-1',
    onSelect: vi.fn(),
    onUserScroll: vi.fn(),
    getRestorePosition: () => null,
    ...overrides,
  };
}

// Force a non-zero container width so the Document renders, and stub scrollTo
// (absent in jsdom).
let widthSpy: PropertyDescriptor | undefined;
beforeAll(() => {
  widthSpy = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'clientWidth'
  );
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => 800,
  });
  HTMLElement.prototype.scrollTo = vi.fn();
});
afterAll(() => {
  if (widthSpy) {
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', widthSpy);
  }
});

beforeEach(() => {
  anchorsMock.data = anchorsResponse();
  anchorsMock.isLoading = false;
  anchorsMock.isRefetching = false;
  anchorsMock.error = null;
  anchorsMock.refresh.mockClear();
});

describe('PdfLens', () => {
  it('renders one overlay per source region with scaled geometry', () => {
    render(<PdfLens {...baseProps()} />);
    // scale = 768 / 612; left = 100 * scale ~= 125.5px
    const overlay = screen.getByRole('button', {
      name: /Source region with 2 audio chunks: #0, #2/i,
    });
    expect(overlay).toBeInTheDocument();
    expect(overlay.style.width).not.toBe('');
    expect(overlay).toHaveTextContent('2');
    expect(overlay).toHaveAccessibleName(/cached; edited text/i);
    expect(screen.getByTitle(/edited text/i)).toBeInTheDocument();
  });

  it('shows the unanchored-count indicator', () => {
    render(<PdfLens {...baseProps()} />);
    expect(
      screen.getByText(/1 chunk not shown on the PDF/i)
    ).toBeInTheDocument();
  });

  it('selects by list position when an overlay is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PdfLens {...baseProps({ onSelect })} />);
    await user.click(
      screen.getByRole('button', {
        name: /Source region for chunk 1: dialogue/i,
      })
    );
    expect(onSelect).toHaveBeenCalledWith(1, [1]);
  });

  it('selects a composite source region as an ordered chunk set', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PdfLens {...baseProps({ onSelect })} />);
    await user.click(
      screen.getByRole('button', {
        name: /Source region with 2 audio chunks: #0, #2/i,
      })
    );
    expect(onSelect).toHaveBeenCalledWith(0, [0, 2]);
  });

  it('marks the active chunk overlay', () => {
    render(<PdfLens {...baseProps({ activeIndex: 0 })} />);
    const overlay = screen.getByRole('button', {
      name: /Source region with 2 audio chunks: #0, #2/i,
    });
    expect(overlay.querySelector('span')?.className).toContain('bg-primary/25');
  });

  it('shows a loading state while anchors compute', () => {
    anchorsMock.data = undefined;
    anchorsMock.isLoading = true;
    render(<PdfLens {...baseProps()} />);
    expect(
      screen.getByText(/Anchoring chunks to the PDF/i)
    ).toBeInTheDocument();
  });

  it('scrolls to the nearest anchored neighbor for unanchored chunks', () => {
    const scrollTo = vi.fn();
    HTMLElement.prototype.scrollTo = scrollTo;
    const ref = createRef<ViewerLensHandle>();
    render(<PdfLens ref={ref} {...baseProps()} />);
    scrollTo.mockClear();
    // idx 3 is unanchored -> lands on the nearest anchored neighbor (idx 2)
    ref.current?.scrollToPosition(3);
    expect(scrollTo).toHaveBeenCalledTimes(1);
  });

  it('exposes a force-refresh operation through the lens handle', async () => {
    const ref = createRef<ViewerLensHandle>();
    render(<PdfLens ref={ref} {...baseProps()} />);
    await ref.current?.refresh?.();
    expect(anchorsMock.refresh).toHaveBeenCalledTimes(1);
  });

  it('restores the reading position once the document reports load success', () => {
    const scrollTo = vi.fn();
    HTMLElement.prototype.scrollTo = scrollTo;
    render(<PdfLens {...baseProps({ getRestorePosition: () => 1 })} />);
    // The mount restore waits for onLoadSuccess (scrolling an empty container
    // would clamp to 0); the Document mock fires it on mount
    expect(scrollTo).toHaveBeenCalledTimes(1);
  });

  it('hides overlays and refreshes when anchors disagree with the inventory', () => {
    anchorsMock.data = { ...anchorsResponse(), totalChunks: 99 };
    render(<PdfLens {...baseProps()} />);
    expect(screen.getByText(/Chunk data changed/i)).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Source region/i })
    ).not.toBeInTheDocument();
    expect(anchorsMock.refresh).toHaveBeenCalledTimes(1);
  });

  it('hides overlays when same-length anchors have a different layout revision', () => {
    anchorsMock.data = {
      ...anchorsResponse(),
      chunkLayoutRevision: 'stale-layout-rev',
    };
    render(<PdfLens {...baseProps()} />);

    expect(screen.getByText(/Chunk data changed/i)).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Source region/i })
    ).not.toBeInTheDocument();
    expect(anchorsMock.refresh).toHaveBeenCalledTimes(1);
  });

  it('attempts one refresh per distinct skew, then reports the mismatch', () => {
    // A recompute stamps a fresh generatedAt; if the skew persists (same
    // revision pair), that must NOT count as a new skew - retrying per
    // response would loop multi-second PDF extractions forever
    anchorsMock.data = {
      ...anchorsResponse(),
      chunkLayoutRevision: 'stale-layout-rev',
    };
    const { rerender } = render(<PdfLens {...baseProps()} />);
    expect(anchorsMock.refresh).toHaveBeenCalledTimes(1);

    anchorsMock.data = {
      ...anchorsResponse(),
      chunkLayoutRevision: 'stale-layout-rev',
      generatedAt: '2026-07-06T00:05:00+00:00',
    };
    rerender(<PdfLens {...baseProps()} />);

    expect(anchorsMock.refresh).toHaveBeenCalledTimes(1);
    expect(
      screen.getByText(/out of sync with the current chunks/i)
    ).toBeInTheDocument();
  });

  it('keeps the PDF readable but disables overlays for cropped page geometry', () => {
    anchorsMock.data = {
      ...anchorsResponse(),
      unsupportedGeometryPages: [0],
    };
    render(<PdfLens {...baseProps()} />);

    expect(screen.getByTestId('pdf-document')).toBeInTheDocument();
    expect(screen.getByText(/Audio highlights are disabled/i)).toBeVisible();
    expect(
      screen.queryByRole('button', { name: /Source region/i })
    ).not.toBeInTheDocument();
    expect(anchorsMock.refresh).not.toHaveBeenCalled();
  });
});
