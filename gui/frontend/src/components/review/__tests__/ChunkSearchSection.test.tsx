import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { render, screen } from '@/test/utils/render';
import type {
  ChunkInventoryEntry,
  ChunkInventoryResponse,
} from '@/types/chunks';

import { ChunkSearchSection } from '../ChunkSearchSection';

// Stub the dialogue card (renders audio players / task polling) so we can
// focus on the section's search/filter/limit UI.
vi.mock('../DialogueItem', () => ({
  DialogueItem: ({
    clip,
    occurrenceCount,
  }: {
    clip: { text: string };
    occurrenceCount?: number;
  }) => (
    <div data-testid="dialogue-item" data-occurrence-count={occurrenceCount}>
      {clip.text}
    </div>
  ),
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
    generatedAt: '2026-07-05T00:00:00+00:00',
  };
}

function baseProps() {
  return {
    projectName: 'demo',
    cacheFolder: '/tmp/cache',
    onRefresh: vi.fn(),
  };
}

describe('ChunkSearchSection', () => {
  it('shows a loading state while the inventory is loading', () => {
    render(<ChunkSearchSection {...baseProps()} isLoading />);
    expect(screen.getByText(/Loading chunk inventory/i)).toBeInTheDocument();
  });

  it('shows a not-loaded message when there is no inventory', () => {
    render(<ChunkSearchSection {...baseProps()} />);
    expect(screen.getByText(/No chunk inventory loaded/i)).toBeInTheDocument();
  });

  it('shows a hint instead of results when there is no active query', () => {
    const inventory = makeInventory([makeEntry(0), makeEntry(1)]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    expect(screen.queryByTestId('dialogue-item')).not.toBeInTheDocument();
    expect(
      screen.getByText(/Search by text, or filter by speaker, type, or status/i)
    ).toBeVisible();
  });

  it('does not treat a whitespace-only query as active', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([makeEntry(0)]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), '   ');

    expect(screen.queryByTestId('dialogue-item')).not.toBeInTheDocument();
    expect(
      screen.getByText(/Search by text, or filter by speaker, type, or status/i)
    ).toBeVisible();
  });

  it('renders matching results with a "showing X of Y" note once a query is active', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([
      makeEntry(0),
      makeEntry(1, {
        speaker: null,
        speakerDisplay: '(default)',
        chunkType: 'action',
        status: 'missing',
      }),
    ]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), 'line');

    expect(screen.getAllByTestId('dialogue-item')).toHaveLength(2);
    expect(
      screen.getByText(/Showing 2 of 2 matching audio files/i)
    ).toBeVisible();
  });

  it('filters results as the user types in the search box', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([
      makeEntry(0, { originalText: 'Hello world.' }),
      makeEntry(1, { originalText: 'Goodbye now.' }),
    ]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), 'goodbye');

    expect(screen.getAllByTestId('dialogue-item')).toHaveLength(1);
    expect(
      screen.getByText(/Showing 1 of 1 matching audio file/i)
    ).toBeVisible();
  });

  it('shows an empty state when nothing matches', async () => {
    const user = userEvent.setup();
    const inventory = makeInventory([makeEntry(0)]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), 'zzz-no-match');

    expect(screen.queryByTestId('dialogue-item')).not.toBeInTheDocument();
    expect(screen.getByText(/No chunks match your search/i)).toBeVisible();
  });

  it('collapses chunks sharing the same cache audio into one card', async () => {
    const user = userEvent.setup();
    const shared = 'shared~~openai~~nova_tts-1.mp3';
    const inventory = makeInventory([
      makeEntry(0, {
        originalText: 'Repeated line.',
        processedText: 'REPEATED LINE.',
        cacheFilename: shared,
        occurrences: [0, 1, 2],
      }),
      makeEntry(1, {
        originalText: 'Repeated line.',
        processedText: 'REPEATED LINE.',
        cacheFilename: shared,
        occurrences: [0, 1, 2],
      }),
      makeEntry(2, {
        originalText: 'Repeated line.',
        processedText: 'REPEATED LINE.',
        cacheFilename: shared,
        occurrences: [0, 1, 2],
      }),
      makeEntry(3, { originalText: 'Repeated once more.' }),
    ]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), 'repeated');

    // 4 matching chunks, but only 2 unique audio files
    const items = screen.getAllByTestId('dialogue-item');
    expect(items).toHaveLength(2);
    expect(
      screen.getByText(/Showing 2 of 2 matching audio files/i)
    ).toBeVisible();

    // Collapsed card receives the occurrence count for its shared-audio badge
    expect(items[0]).toHaveAttribute('data-occurrence-count', '3');
    expect(items[1]).toHaveAttribute('data-occurrence-count', '1');
  });

  it('hides the chunk number on collapsed cards but keeps it on unique ones', async () => {
    const user = userEvent.setup();
    const shared = 'shared~~openai~~nova_tts-1.mp3';
    const inventory = makeInventory([
      makeEntry(0, {
        originalText: 'Repeated line.',
        cacheFilename: shared,
        occurrences: [0, 1],
      }),
      makeEntry(1, {
        originalText: 'Repeated line.',
        cacheFilename: shared,
        occurrences: [0, 1],
      }),
      makeEntry(2, { originalText: 'Repeated once more.' }),
    ]);
    render(<ChunkSearchSection {...baseProps()} inventory={inventory} />);

    await user.type(screen.getByLabelText(/Search chunks/i), 'repeated');

    // The collapsed card (chunks 0+1) must not show any chunk number; the
    // unique card (chunk 2) keeps its chunk number.
    expect(screen.queryByText('chunk #0')).not.toBeInTheDocument();
    expect(screen.queryByText('chunk #1')).not.toBeInTheDocument();
    expect(screen.getByText('chunk #2')).toBeVisible();
  });

  it('caps the rendered list at 50 unique audio files', async () => {
    const user = userEvent.setup();
    const entries = Array.from({ length: 75 }, (_, idx) => makeEntry(idx));
    render(
      <ChunkSearchSection {...baseProps()} inventory={makeInventory(entries)} />
    );

    await user.type(screen.getByLabelText(/Search chunks/i), 'line');

    expect(screen.getAllByTestId('dialogue-item')).toHaveLength(50);
    expect(
      screen.getByText(/Showing 50 of 75 matching audio files/i)
    ).toBeVisible();
  });

  it('counts unique audio files (not raw chunks) in the cap note', async () => {
    const user = userEvent.setup();
    const shared = 'shared~~openai~~nova_tts-1.mp3';
    // 60 chunks sharing one audio file + 2 unique chunks = 3 unique files
    const sharedOccurrences = Array.from({ length: 60 }, (_, idx) => idx);
    const entries = [
      ...sharedOccurrences.map((idx) =>
        makeEntry(idx, {
          cacheFilename: shared,
          originalText: 'Same line.',
          processedText: 'SAME LINE.',
          occurrences: sharedOccurrences,
        })
      ),
      makeEntry(60, { originalText: 'Same but unique.' }),
      makeEntry(61, { originalText: 'Same but also unique.' }),
    ];
    render(
      <ChunkSearchSection {...baseProps()} inventory={makeInventory(entries)} />
    );

    await user.type(screen.getByLabelText(/Search chunks/i), 'same');

    expect(screen.getAllByTestId('dialogue-item')).toHaveLength(3);
    expect(
      screen.getByText(/Showing 3 of 3 matching audio files/i)
    ).toBeVisible();
  });

  it('calls onRefresh when the refresh button is clicked', async () => {
    const user = userEvent.setup();
    const props = baseProps();
    render(
      <ChunkSearchSection
        {...props}
        inventory={makeInventory([makeEntry(0)])}
      />
    );

    await user.click(screen.getByRole('button', { name: /Refresh/i }));

    expect(props.onRefresh).toHaveBeenCalledTimes(1);
  });
});
