import { fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { forwardRef, useImperativeHandle } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ViewerLensHandle } from '@/components/viewer/lensHandle';
import type { SequentialPlayback } from '@/hooks/audio/useSequentialPlayback';
import { render, screen } from '@/test/utils/render';
import type {
  ChunkInventoryEntry,
  ChunkInventoryResponse,
} from '@/types/chunks';

import { ScreenplayViewer } from '../ScreenplayViewer';

const pdfLensMocks = vi.hoisted(() => ({
  refresh: vi.fn(() => Promise.resolve()),
}));

// The PDF lens pulls in react-pdf + pdf.js (no canvas/worker in jsdom), so stub
// it. It exercises its own suite; here we only verify the shell mounts it and
// preserves shared state across the toggle.
vi.mock('../pdf/PdfLens', () => ({
  default: forwardRef<
    ViewerLensHandle,
    {
      entries: unknown[];
      onSelect: (position: number, regionPositions?: number[]) => void;
      getRestorePosition?: () => number | null;
    }
  >(function PdfLensStub(props, ref) {
    useImperativeHandle(ref, () => ({
      scrollToPosition: vi.fn(),
      refresh: pdfLensMocks.refresh,
    }));
    return (
      <div
        data-testid="pdf-lens"
        data-restore={String(props.getRestorePosition?.() ?? '')}
      >
        PDF lens ({props.entries.length})
        <button onClick={() => props.onSelect(0, [0, 1])}>
          Select composite source region
        </button>
      </div>
    );
  }),
}));

// jsdom has no layout, so virtualization is mocked to render every row at a
// fixed offset. The real logic under test lives in the pure helpers and the
// sequential-playback hook, which have their own suites.
const virtualMocks = vi.hoisted(() => ({
  scrollToIndex: vi.fn(),
}));

vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        key: index,
        index,
        start: index * 50,
        size: 50,
      })),
    getTotalSize: () => count * 50,
    scrollToIndex: virtualMocks.scrollToIndex,
    measureElement: () => {},
    measure: () => {},
  }),
}));

// Stub the dialogue card (renders audio players / task polling)
vi.mock('@/components/review/DialogueItem', () => ({
  DialogueItem: ({ clip }: { clip: { text: string } }) => (
    <div data-testid="dialogue-item">{clip.text}</div>
  ),
}));

// Controllable sequential-playback hook (its state machine has its own suite)
const sequentialMock = vi.hoisted(() => {
  const value = {
    activeIndex: null as number | null,
    status: 'inactive',
    isActive: false,
    playFrom: vi.fn(),
    stop: vi.fn(),
  };
  return {
    value,
    reset: () => {
      value.activeIndex = null;
      value.status = 'inactive';
      value.isActive = false;
      value.playFrom.mockClear();
      value.stop.mockClear();
    },
    activateAt: (index: number) => {
      value.activeIndex = index;
      value.status = 'playing';
      value.isActive = true;
    },
  };
});

vi.mock('@/hooks/audio/useSequentialPlayback', () => ({
  useSequentialPlayback: (): SequentialPlayback =>
    sequentialMock.value as SequentialPlayback,
}));

function makeEntry(
  idx: number,
  overrides: Partial<ChunkInventoryEntry> = {}
): ChunkInventoryEntry {
  return {
    idx,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: `Line number ${idx}.`,
    processedText: `LINE NUMBER ${idx}.`,
    cacheFilename: `hash-${idx}~~openai~~nova_tts-1.mp3`,
    status: 'cached',
    userModified: null,
    occurrences: [idx],
    ...overrides,
  };
}

function makeInventory(entries: ChunkInventoryEntry[]): ChunkInventoryResponse {
  return {
    projectName: 'demo',
    entries,
    speakerConfigs: {
      JOHN: {
        provider: 'openai',
        voiceId: 'nova_tts-1',
        speakerConfig: { provider: 'openai', voice: 'nova' },
        stsId: 'sarah',
      },
      default: {
        provider: 'openai',
        voiceId: 'onyx_tts-1',
        speakerConfig: {},
        stsId: null,
      },
    },
    totalChunks: entries.length,
    cachedCount: entries.filter((e) => e.status === 'cached').length,
    missingCount: entries.filter((e) => e.status === 'missing').length,
    userModifiedCount: entries.filter((e) => e.userModified !== null).length,
    cacheFolder: '/tmp/cache',
    chunkLayoutRevision: 'layout-rev-1',
    generatedAt: '2026-07-05T00:00:00+00:00',
  };
}

function baseProps() {
  return {
    projectName: 'demo',
    onRefresh: vi.fn(),
  };
}

function getRow(idx: number, chunkType = 'dialogue') {
  // The row button's accessible name is a hidden "Chunk N, type:" prefix
  // followed by the chunk text itself (a reading view must expose its text
  // to assistive tech), so match on the prefix
  return screen.getByRole('button', {
    name: new RegExp(`^Chunk ${idx}, ${chunkType.replace(/_/g, ' ')}:`),
  });
}

/**
 * Fire a scroll event that reads as genuine user scrolling. Programmatic
 * scrolls open a quiet window (useLensScroll), so pretend time has passed.
 */
function fireUserScroll(element: Element, scrollTop = 0) {
  Object.defineProperty(element, 'scrollTop', {
    value: scrollTop,
    configurable: true,
  });
  const nowSpy = vi
    .spyOn(Date, 'now')
    .mockImplementation(() => new Date().getTime() + 60_000);
  fireEvent.scroll(element);
  nowSpy.mockRestore();
}

describe('ScreenplayViewer', () => {
  beforeEach(() => {
    sequentialMock.reset();
    virtualMocks.scrollToIndex.mockClear();
    pdfLensMocks.refresh.mockClear();
    // The reading anchor persists per project for the tab session
    window.sessionStorage.clear();
  });

  it('shows a loading state while the inventory is loading', () => {
    render(<ScreenplayViewer {...baseProps()} isLoading />);
    expect(screen.getByText(/Loading chunk inventory/i)).toBeInTheDocument();
  });

  it('shows a not-loaded message when there is no inventory', () => {
    render(<ScreenplayViewer {...baseProps()} />);
    expect(screen.getByText(/No chunk inventory loaded/i)).toBeInTheDocument();
  });

  it('shows the warning banner when disabled', () => {
    render(
      <ScreenplayViewer
        {...baseProps()}
        disabled
        warningMessage="Complete voice casting before viewing the screenplay."
      />
    );
    expect(
      screen.getByText(/Complete voice casting before viewing/i)
    ).toBeInTheDocument();
  });

  it('renders every chunk with per-type reading styles', () => {
    const inventory = makeInventory([
      makeEntry(0, {
        chunkType: 'scene_heading',
        originalText: 'INT. LAB - DAY',
      }),
      makeEntry(1, { chunkType: 'action', originalText: 'John walks in.' }),
      makeEntry(2, { originalText: 'Hello there.' }),
    ]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    const heading = screen.getByText('INT. LAB - DAY');
    expect(heading.className).toContain('uppercase');
    const dialogue = screen.getByText('Hello there.');
    expect(dialogue.className).toContain('max-w-xl');
    expect(screen.getByText('John walks in.')).toBeInTheDocument();
    // Counts line in the toolbar
    expect(screen.getByText(/3 chunks · 3 cached/)).toBeInTheDocument();
  });

  it('opens, swaps, and closes the detail panel on row clicks', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    expect(screen.queryByTestId('dialogue-item')).not.toBeInTheDocument();

    await user.click(getRow(0));
    expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
      'LINE NUMBER 0.'
    );

    await user.click(getRow(1));
    expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
      'LINE NUMBER 1.'
    );

    await user.click(screen.getByRole('button', { name: /close details/i }));
    expect(screen.queryByTestId('dialogue-item')).not.toBeInTheDocument();
  });

  it('keeps row selection and playback as separate keyboard controls', () => {
    const inventory = makeInventory([makeEntry(0)]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    const selection = getRow(0);
    const playback = within(screen.getByTestId('chunk-row-0')).getByRole(
      'button',
      { name: /play chunk/i }
    );
    expect(selection.contains(playback)).toBe(false);
  });

  it('starts sequential playback from a row and from the toolbar', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    const playFromHere = within(screen.getByTestId('chunk-row-1')).getByRole(
      'button',
      {
        name: /play from here/i,
      }
    );
    await user.click(playFromHere);
    expect(sequentialMock.value.playFrom).toHaveBeenCalledWith(1);

    await user.click(screen.getByRole('button', { name: /play all/i }));
    expect(sequentialMock.value.playFrom).toHaveBeenCalledWith(0);
  });

  it('disables play-all when nothing is cached', () => {
    const inventory = makeInventory([
      makeEntry(0, { status: 'missing' }),
      makeEntry(1, { status: 'missing' }),
    ]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    expect(screen.getByRole('button', { name: /play all/i })).toBeDisabled();
  });

  it('highlights the active row and offers Stop while playback runs', async () => {
    const user = userEvent.setup();
    sequentialMock.activateAt(1);
    const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    expect(screen.getByTestId('chunk-row-1').className).toContain(
      'bg-primary/10'
    );
    expect(screen.getByTestId('chunk-row-0').className).not.toContain(
      'bg-primary/10'
    );

    await user.click(screen.getByRole('button', { name: /stop/i }));
    expect(sequentialMock.value.stop).toHaveBeenCalled();
  });

  it('restores the reading anchor once the inventory arrives on a cold load', () => {
    // The anchor was written in an earlier visit; on a fresh mount the
    // inventory is still loading, so the one-shot restore must wait for
    // entries instead of consuming itself against an empty list
    window.sessionStorage.setItem('sts:viewer-reading-anchor:demo', '2');
    const { rerender } = render(
      <ScreenplayViewer {...baseProps()} isLoading />
    );
    expect(virtualMocks.scrollToIndex).not.toHaveBeenCalled();

    const inventory = makeInventory([makeEntry(0), makeEntry(1), makeEntry(2)]);
    rerender(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    expect(virtualMocks.scrollToIndex).toHaveBeenCalledWith(2, {
      align: 'center',
    });
  });

  it('pauses auto-follow on user scroll and restores it via Jump to current', async () => {
    const user = userEvent.setup();
    sequentialMock.activateAt(0);
    const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    // Following by default - no pill
    expect(
      screen.queryByRole('button', { name: /jump to current/i })
    ).toBeNull();

    fireUserScroll(screen.getByTestId('viewer-scroll'));
    const pill = screen.getByRole('button', { name: /jump to current/i });

    virtualMocks.scrollToIndex.mockClear();
    await user.click(pill);
    expect(virtualMocks.scrollToIndex).toHaveBeenCalledWith(0, {
      align: 'center',
    });
    expect(
      screen.queryByRole('button', { name: /jump to current/i })
    ).toBeNull();
  });

  it('jumps the list when the detail panel requests another chunk', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([
      makeEntry(0, { occurrences: [0, 1] }),
      makeEntry(1, { occurrences: [0, 1] }),
    ]);
    render(<ScreenplayViewer {...baseProps()} inventory={inventory} />);

    await user.click(getRow(0));
    await user.click(screen.getByRole('button', { name: 'chunk #1' }));

    expect(virtualMocks.scrollToIndex).toHaveBeenCalledWith(1, {
      align: 'center',
    });
    // Selection follows the jump
    expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
      'LINE NUMBER 1.'
    );
  });

  describe('lens toggle', () => {
    it('hides the List | PDF toggle when the project has no PDF', () => {
      const inventory = makeInventory([makeEntry(0)]);
      render(
        <ScreenplayViewer
          {...baseProps()}
          inventory={inventory}
          hasPdf={false}
        />
      );
      expect(
        screen.queryByRole('radio', { name: /pdf view/i })
      ).not.toBeInTheDocument();
    });

    it('shows the toggle and switches to the PDF lens', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
      render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      expect(screen.getByTestId('viewer-scroll')).toBeInTheDocument();

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));

      expect(await screen.findByTestId('pdf-lens')).toBeInTheDocument();
      expect(screen.queryByTestId('viewer-scroll')).not.toBeInTheDocument();
    });

    it('preserves the selected chunk across a lens round-trip', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
      render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      // Select a chunk in the list, then toggle to PDF and back
      await user.click(getRow(1));
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 1.'
      );

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      await screen.findByTestId('pdf-lens');
      // Detail panel (and its selection) persists in the shell
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 1.'
      );

      await user.click(screen.getByRole('radio', { name: /list view/i }));
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 1.'
      );
    });

    it('opens one persistent navigator for chunks from a composite PDF region', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
      render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      await user.click(
        screen.getByRole('button', { name: /select composite source region/i })
      );

      expect(screen.getByText(/source region · 2 audio chunks/i)).toBeVisible();
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 0.'
      );

      await user.click(
        screen.getByRole('button', {
          name: /select chunk #1 from source region/i,
        })
      );
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 1.'
      );
    });

    it('keeps the selected panel chunk while playback moves through a composite region', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
      const { rerender } = render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      await user.click(
        screen.getByRole('button', { name: /select composite source region/i })
      );
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 0.'
      );

      // Sequential playback advances onto the region's other constituent;
      // the panel is keyed by chunk idx, so retargeting it would remount the
      // editor card and discard in-progress edits - selection stays put
      sequentialMock.activateAt(1);
      rerender(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );
      expect(screen.getByTestId('dialogue-item')).toHaveTextContent(
        'LINE NUMBER 0.'
      );
    });

    it('starts sequential playback from the detail panel in the PDF lens', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
      render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      await user.click(
        screen.getByRole('button', { name: /select composite source region/i })
      );

      // The panel header hosts play-from-here - the PDF lens's only
      // sequential entry point besides Play all
      await user.click(screen.getByRole('button', { name: /play from here/i }));
      expect(sequentialMock.value.playFrom).toHaveBeenCalledWith(0);
    });

    it('restores the reading position across a lens round-trip', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([
        makeEntry(0),
        makeEntry(1),
        makeEntry(2),
      ]);
      render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      // User scrolls the list so row 2 tops the viewport (50px mocked rows)
      fireUserScroll(screen.getByTestId('viewer-scroll'), 100);

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      // The PDF lens is handed the remembered reading position to restore
      const pdfLens = await screen.findByTestId('pdf-lens');
      expect(pdfLens).toHaveAttribute('data-restore', '2');

      virtualMocks.scrollToIndex.mockClear();
      await user.click(screen.getByRole('radio', { name: /list view/i }));
      // The freshly mounted list lands back on the reading anchor
      expect(virtualMocks.scrollToIndex).toHaveBeenCalledWith(2, {
        align: 'center',
      });
    });

    it('remembers the reading anchor by chunk identity across refreshes', async () => {
      const user = userEvent.setup();
      const inventory = makeInventory([
        makeEntry(0),
        makeEntry(1),
        makeEntry(2),
      ]);
      const { rerender } = render(
        <ScreenplayViewer {...baseProps()} inventory={inventory} hasPdf />
      );

      // Anchor on chunk idx 2 (third row)
      fireUserScroll(screen.getByTestId('viewer-scroll'), 100);

      // A refresh inserts a chunk before it: idx 2 is now at position 3
      const grown = makeInventory([
        makeEntry(0),
        makeEntry(1),
        makeEntry(5),
        makeEntry(2),
      ]);
      rerender(<ScreenplayViewer {...baseProps()} inventory={grown} hasPdf />);

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      const pdfLens = await screen.findByTestId('pdf-lens');
      // Restores to idx 2's NEW position, not the stale position 2
      expect(pdfLens).toHaveAttribute('data-restore', '3');
    });

    it('refreshes both the inventory and PDF anchors from one action', async () => {
      const user = userEvent.setup();
      const onRefresh = vi.fn(() => Promise.resolve());
      const inventory = makeInventory([makeEntry(0)]);
      render(
        <ScreenplayViewer
          {...baseProps()}
          inventory={inventory}
          hasPdf
          onRefresh={onRefresh}
        />
      );

      await user.click(screen.getByRole('radio', { name: /pdf view/i }));
      await user.click(screen.getByRole('button', { name: /refresh/i }));

      expect(onRefresh).toHaveBeenCalledTimes(1);
      expect(pdfLensMocks.refresh).toHaveBeenCalledTimes(1);
    });
  });
});
