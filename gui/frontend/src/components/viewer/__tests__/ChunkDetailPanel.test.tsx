import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { render, screen } from '@/test/utils/render';
import type { ChunkInventoryEntry, ChunkSpeakerConfig } from '@/types/chunks';

import { ChunkDetailPanel } from '../ChunkDetailPanel';

// Stub the dialogue card (renders audio players / task polling) so we can
// focus on the panel's detail sections.
vi.mock('@/components/review/DialogueItem', () => ({
  DialogueItem: ({
    clip,
    occurrenceCount,
    userModified,
  }: {
    clip: { text: string; provider: string };
    occurrenceCount?: number;
    userModified?: string | null;
  }) => (
    <div
      data-testid="dialogue-item"
      data-occurrence-count={occurrenceCount}
      data-user-modified={userModified ?? ''}
      data-provider={clip.provider}
    >
      {clip.text}
    </div>
  ),
}));

const SPEAKER_CONFIGS: Record<string, ChunkSpeakerConfig> = {
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
};

function makeEntry(
  overrides: Partial<ChunkInventoryEntry> = {}
): ChunkInventoryEntry {
  return {
    idx: 3,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: 'Is anyone sitting here?',
    processedText: 'IS ANYONE SITTING HERE?',
    cacheFilename: 'abc~~def~~openai~~nova_tts-1.mp3',
    status: 'cached',
    userModified: null,
    occurrences: [3],
    ...overrides,
  };
}

function renderPanel(
  entry: ChunkInventoryEntry,
  overrides: Partial<Parameters<typeof ChunkDetailPanel>[0]> = {}
) {
  const onJumpToChunk = vi.fn();
  const onClose = vi.fn();
  render(
    <ChunkDetailPanel
      entry={entry}
      speakerConfigs={SPEAKER_CONFIGS}
      projectName="demo"
      cacheFolder="/tmp/cache"
      onJumpToChunk={onJumpToChunk}
      onClose={onClose}
      {...overrides}
    />
  );
  return { onJumpToChunk, onClose };
}

describe('ChunkDetailPanel', () => {
  it('renders the original and processed text, and the cache filename', () => {
    renderPanel(makeEntry());

    expect(screen.getByText('Original')).toBeInTheDocument();
    expect(screen.getByText('Is anyone sitting here?')).toBeInTheDocument();
    expect(screen.getByText('Spoken (processed)')).toBeInTheDocument();
    expect(
      screen.getByText('abc~~def~~openai~~nova_tts-1.mp3')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /copy cache filename/i })
    ).toBeInTheDocument();
  });

  it('shows the chunk header with type and status badges', () => {
    renderPanel(makeEntry({ status: 'missing', userModified: 'edit' }));

    expect(screen.getByText('chunk #3')).toBeInTheDocument();
    expect(screen.getByText('dialogue')).toBeInTheDocument();
    expect(screen.getByText('missing')).toBeInTheDocument();
    expect(screen.getByText('edited text')).toBeInTheDocument();
  });

  it('passes the built clip and props to the dialogue card', () => {
    renderPanel(makeEntry({ occurrences: [3, 7], userModified: 'retake' }));

    const item = screen.getByTestId('dialogue-item');
    // buildProblemClip uses processedText and the speaker's config
    expect(item).toHaveTextContent('IS ANYONE SITTING HERE?');
    expect(item).toHaveAttribute('data-provider', 'openai');
    expect(item).toHaveAttribute('data-occurrence-count', '2');
    expect(item).toHaveAttribute('data-user-modified', 'retake');
  });

  it('hides the shared-audio section for a unique chunk', () => {
    renderPanel(makeEntry({ occurrences: [3] }));
    expect(screen.queryByText(/Shared audio/i)).not.toBeInTheDocument();
  });

  it('fires onJumpToChunk from the shared-audio chips', async () => {
    const user = userEvent.setup();
    const { onJumpToChunk } = renderPanel(
      makeEntry({ occurrences: [3, 8, 21] })
    );

    expect(screen.getByText(/shared by 3 chunks/i)).toBeInTheDocument();
    // Chips list the other occurrences, not the chunk itself
    expect(screen.queryByRole('button', { name: 'chunk #3' })).toBeNull();

    await user.click(screen.getByRole('button', { name: 'chunk #21' }));
    expect(onJumpToChunk).toHaveBeenCalledWith(21);
  });

  it('caps the shared-audio chips and shows the remainder count', () => {
    const occurrences = Array.from({ length: 20 }, (_, i) => i);
    renderPanel(makeEntry({ idx: 0, occurrences }));

    // 19 other occurrences: 12 chips + "+7 more"
    const chips = screen
      .getAllByRole('button')
      .filter((b) => /^chunk #\d+$/.test(b.textContent ?? ''));
    expect(chips).toHaveLength(12);
    expect(screen.getByText('+7 more')).toBeInTheDocument();
  });

  it('navigates the audio chunks derived from one PDF source region', async () => {
    const user = userEvent.setup();
    const current = makeEntry({ idx: 3 });
    const sibling = makeEntry({
      idx: 4,
      speakerDisplay: 'MARY',
      originalText: 'It is free.',
      status: 'missing',
      userModified: 'retake',
    });
    const onSelectRegionEntry = vi.fn();

    renderPanel(current, {
      regionEntries: [current, sibling],
      onSelectRegionEntry,
    });

    expect(screen.getByText(/source region · 2 audio chunks/i)).toBeVisible();
    expect(
      screen.getByRole('button', {
        name: /select chunk #3 from source region/i,
      })
    ).toHaveAttribute('aria-current', 'true');
    expect(screen.getByText('custom take')).toBeVisible();

    await user.click(
      screen.getByRole('button', {
        name: /select chunk #4 from source region/i,
      })
    );
    expect(onSelectRegionEntry).toHaveBeenCalledWith(4);
  });

  it('fires onClose from the close button', async () => {
    const user = userEvent.setup();
    const { onClose } = renderPanel(makeEntry());

    await user.click(screen.getByRole('button', { name: /close details/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('starts sequential playback from the header play-from-here control', async () => {
    const user = userEvent.setup();
    const onPlayFromHere = vi.fn();
    renderPanel(makeEntry(), { onPlayFromHere });

    await user.click(screen.getByRole('button', { name: /play from here/i }));
    expect(onPlayFromHere).toHaveBeenCalledWith(3);
  });

  it('omits playback controls when no play-from-here handler is provided', () => {
    renderPanel(makeEntry());
    expect(
      screen.queryByRole('button', { name: /play from here/i })
    ).not.toBeInTheDocument();
  });
});
